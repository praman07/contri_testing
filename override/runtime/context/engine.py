import logging
import datetime
import threading
import uuid
import re
from typing import List, Dict, Any, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.context import IContextEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.context.models import (
    ActiveWindowContext,
    HostEnvironmentSummary,
    TaskStateContext,
    EntityNode,
    EntityEdge,
    WorldState
)
from override.runtime.context.graph import EntityGraph

logger = logging.getLogger("Override.ContextEngine")

class ContextEngine(OverrideModule, IContextEngine):
    """
    Layer 09 — Context / World Model Engine.
    Aggregates environmental, perception, memory, and task state signals into
    a real-time in-memory WorldState with entity relationships and temporal tracking.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        config: ConfigurationManager
    ):
        super().__init__("context_engine")
        self._event_bus = event_bus
        self._config = config
        self._lock = threading.RLock()

        # Context components
        self._graph = EntityGraph()
        self._history: List[WorldState] = []
        self._max_history_len = 10

        # Current working values
        self._active_window = ActiveWindowContext()
        self._running_applications: List[Dict[str, Any]] = []
        self._clipboard_summary: Optional[str] = None
        self._host_environment = HostEnvironmentSummary()
        self._task_state = TaskStateContext()
        self._last_user_input_time = datetime.datetime.utcnow()
        self._idle_threshold_seconds = 300.0  # 5 minutes
        self._last_emitted_anomalies: List[str] = []

    # ------------------------------------------------------------------
    # ICognitiveEngine Lifecycle Hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        """Register subscriptions for all context inputs."""
        logger.info("Initializing Context Engine...")

        # Subscriptions to low-level observations and environments
        self._event_bus.subscribe("observation.window_changed", self._on_window_changed)
        self._event_bus.subscribe("perception.frame_ready", self._on_frame_ready)
        self._event_bus.subscribe("environment.changed", self._on_environment_changed)
        
        # Subscriptions for user activity timers
        self._event_bus.subscribe("observation.keyboard_input", self._on_user_input)
        self._event_bus.subscribe("observation.mouse_moved", self._on_user_input)
        self._event_bus.subscribe("observation.mouse_button", self._on_user_input)

        # Subscriptions for task tracking
        self._event_bus.subscribe("planning.plan_started", self._on_plan_started)
        self._event_bus.subscribe("planning.plan_completed", self._on_plan_finished)
        self._event_bus.subscribe("planning.plan_aborted", self._on_plan_finished)
        self._event_bus.subscribe("execution.step_started", self._on_step_started)
        self._event_bus.subscribe("execution.step_completed", self._on_step_finished)
        self._event_bus.subscribe("execution.step_failed", self._on_step_failed)

        # Lifecycle events
        self._event_bus.subscribe("system.shutdown", self._on_system_shutdown)

        # Seed initial default graph nodes
        with self._lock:
            self._graph.add_node(EntityNode("user", "actor", {"name": "User"}))
            self._graph.add_node(EntityNode("host_os", "system", {"name": "Host Operating System"}))

        logger.info("Context Engine initialized.")

    def on_start(self) -> None:
        logger.info("Context Engine started.")

    def on_stop(self) -> None:
        logger.info("Stopping Context Engine...")
        with self._lock:
            self._history.clear()
            self._graph.clear()
            self._running_applications.clear()
            self._clipboard_summary = None
            self._last_emitted_anomalies.clear()
        logger.info("Context Engine stopped.")

    # ------------------------------------------------------------------
    # IContextEngine Interface Methods
    # ------------------------------------------------------------------

    async def get_current_state(self) -> Dict[str, Any]:
        with self._lock:
            if not self._history:
                # Compile a state immediately if history is empty
                self._compile_and_publish_state()
            return self._serialize_world_state(self._history[-1])

    async def get_active_window(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "title": self._redact_pii(self._active_window.title),
                "process_name": self._active_window.process_name,
                "bounds": self._active_window.bounds,
                "is_minimized": self._active_window.is_minimized
            }

    async def get_running_applications(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._running_applications)

    async def get_clipboard_context(self) -> Optional[str]:
        with self._lock:
            return self._redact_pii(self._clipboard_summary)

    async def get_host_environment_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "cpu_usage_percent": self._host_environment.cpu_usage_percent,
                "available_memory_mb": self._host_environment.available_memory_mb,
                "network_status": self._host_environment.network_status,
                "power_source": self._host_environment.power_source,
                "battery_percent": self._host_environment.battery_percent
            }

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_window_changed(self, event: IEvent) -> None:
        payload = event.payload or {}
        with self._lock:
            self._active_window = ActiveWindowContext(
                title=payload.get("title", ""),
                process_name=payload.get("process_name", ""),
                bounds=payload.get("bounds", {}),
                is_minimized=payload.get("is_minimized", False)
            )
            # Updatefocused window in graph
            app_id = f"app:{self._active_window.process_name}"
            self._graph.add_node(EntityNode(
                entity_id=app_id,
                entity_type="application",
                properties={"name": self._active_window.process_name, "title": self._active_window.title}
            ))
            self._graph.add_edge(EntityEdge(
                source_id="user",
                target_id=app_id,
                relationship_type="focuses",
                properties={"timestamp": datetime.datetime.utcnow().isoformat() + "Z"}
            ))
            self._compile_and_publish_state()

    async def _on_frame_ready(self, event: IEvent) -> None:
        payload = event.payload or {}
        ocr_text = payload.get("ocr_text", "")
        clipboard = payload.get("clipboard", "")

        with self._lock:
            if clipboard:
                self._clipboard_summary = clipboard
            
            # Simple OCR parsing for web URLs or files to enrich entity graph
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', ocr_text)
            for url in urls[:3]:  # Cap at top 3 perceived links to avoid graph bloat
                url_id = f"url:{url}"
                self._graph.add_node(EntityNode(
                    entity_id=url_id,
                    entity_type="web_page",
                    properties={"url": url}
                ))
                # Link focused application to page
                app_id = f"app:{self._active_window.process_name}"
                self._graph.add_edge(EntityEdge(
                    source_id=app_id,
                    target_id=url_id,
                    relationship_type="contains",
                    properties={"source": "ocr_extraction"}
                ))

            self._compile_and_publish_state()

    async def _on_environment_changed(self, event: IEvent) -> None:
        payload = event.payload or {}
        running_apps = payload.get("running_applications", [])
        metrics = payload.get("metrics", {})

        with self._lock:
            self._running_applications = running_apps
            self._host_environment = HostEnvironmentSummary(
                cpu_usage_percent=float(metrics.get("cpu_percent", 0.0)),
                available_memory_mb=float(metrics.get("available_memory_mb", 0.0)),
                network_status=payload.get("network_status", "connected"),
                power_source=payload.get("power_source", "AC"),
                battery_percent=float(metrics.get("battery_percent", 100.0))
            )
            
            # Update applications in graph
            for app in self._running_applications:
                proc = app.get("process_name")
                if proc:
                    app_id = f"app:{proc}"
                    self._graph.add_node(EntityNode(
                        entity_id=app_id,
                        entity_type="application",
                        properties={"name": proc}
                    ))
                    self._graph.add_edge(EntityEdge(
                        source_id="host_os",
                        target_id=app_id,
                        relationship_type="runs"
                    ))

            self._compile_and_publish_state()

    async def _on_user_input(self, event: IEvent) -> None:
        with self._lock:
            # Check what the last compiled activity actually was
            was_idle = False
            if self._history:
                was_idle = (self._history[-1].perceived_user_activity == "idle")

            # Update input time
            self._last_user_input_time = datetime.datetime.utcnow()

            # Transition from idle to active triggers immediate compilation
            if was_idle:
                self._compile_and_publish_state()

    async def _on_plan_started(self, event: IEvent) -> None:
        payload = event.payload or {}
        with self._lock:
            self._task_state = TaskStateContext(
                active_plan_id=payload.get("plan_id"),
                executor_status="planning"
            )
            self._compile_and_publish_state()

    async def _on_plan_finished(self, event: IEvent) -> None:
        with self._lock:
            self._task_state = TaskStateContext(
                active_plan_id=None,
                active_step_id=None,
                executor_status="idle"
            )
            self._compile_and_publish_state()

    async def _on_step_started(self, event: IEvent) -> None:
        payload = event.payload or {}
        with self._lock:
            self._task_state = TaskStateContext(
                active_plan_id=self._task_state.active_plan_id,
                active_step_id=payload.get("step_id"),
                executor_status="executing"
            )
            self._compile_and_publish_state()

    async def _on_step_finished(self, event: IEvent) -> None:
        with self._lock:
            self._task_state = TaskStateContext(
                active_plan_id=self._task_state.active_plan_id,
                active_step_id=None,
                executor_status="verifying"
            )
            self._compile_and_publish_state()

    async def _on_step_failed(self, event: IEvent) -> None:
        payload = event.payload or {}
        step_id = payload.get("step_id")
        with self._lock:
            self._task_state = TaskStateContext(
                active_plan_id=self._task_state.active_plan_id,
                active_step_id=step_id,
                executor_status="verifying"
            )
            self._compile_and_publish_state()

    async def _on_system_shutdown(self, event: IEvent) -> None:
        logger.info("System shutdown received in Context Engine.")
        self.stop()

    # ------------------------------------------------------------------
    # State Synthesis & Helper Logic
    # ------------------------------------------------------------------

    def _compile_and_publish_state(self) -> None:
        """Synthesize working attributes into a unified WorldState frame."""
        with self._lock:
            # 1. Determine User Activity Status
            if self._task_state.executor_status in ("executing", "verifying"):
                perceived_activity = "system_executing"
            elif (datetime.datetime.utcnow() - self._last_user_input_time).total_seconds() > self._idle_threshold_seconds:
                perceived_activity = "idle"
            else:
                perceived_activity = "active"

            # 2. Safety / Performance Anomaly Detection
            anomalies = []
            if self._host_environment.cpu_usage_percent > 95.0:
                anomalies.append("high_cpu_usage")
            if self._host_environment.battery_percent < 15.0 and self._host_environment.power_source == "battery":
                anomalies.append("low_battery")
            if self._host_environment.network_status == "disconnected":
                anomalies.append("network_disconnected")
            if self._task_state.executor_status == "verifying" and self._last_emitted_anomalies and "execution_step_failed" in self._last_emitted_anomalies:
                # Retain step failed anomaly if we haven't transition to next step
                anomalies.append("execution_step_failed")

            # 3. PII Scrubbing
            scrubbed_window = ActiveWindowContext(
                title=self._redact_pii(self._active_window.title),
                process_name=self._active_window.process_name,
                bounds=self._active_window.bounds,
                is_minimized=self._active_window.is_minimized
            )
            scrubbed_clipboard = self._redact_pii(self._clipboard_summary)

            # 4. Construct WorldState Dataclass
            state = WorldState(
                active_window=scrubbed_window,
                running_applications=list(self._running_applications),
                clipboard_summary=scrubbed_clipboard,
                host_environment=self._host_environment,
                task_state=self._task_state,
                perceived_user_activity=perceived_activity,
                detected_anomalies=anomalies,
                entities=self._graph.get_all_nodes(),
                relationships=self._graph.get_all_edges()
            )

            # 5. Maintain sliding history window (capped at 10)
            self._history.append(state)
            if len(self._history) > self._max_history_len:
                self._history.pop(0)

            # 6. Publish Context Update Event
            serialized = self._serialize_world_state(state)
            self._event_bus.publish(Event(
                _topic="context.updated",
                _source="context_engine",
                _payload=serialized
            ))

            # 7. Check for new anomalies and publish alert
            for anomaly in anomalies:
                if anomaly not in self._last_emitted_anomalies:
                    self._event_bus.publish(Event(
                        _topic="context.anomaly_detected",
                        _source="context_engine",
                        _payload={"anomaly": anomaly, "timestamp": state.timestamp}
                    ))
            self._last_emitted_anomalies = anomalies

    def _redact_pii(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        # Regexes for credentials, SSN, Credit Cards, API Keys
        # API Keys & Passwords pattern
        text = re.sub(
            r'(?:api[_-]?key|passwd|password|secret|auth[_-]?token)(?:\s*[:=]\s*|\s+)[a-zA-Z0-9_\-\.]{12,}',
            r'[CREDENTIALS_REDACTED]',
            text,
            flags=re.IGNORECASE
        )
        # SSN Pattern
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        # Credit Card Pattern
        text = re.sub(r'\b(?:\d[ -]*?){13,19}\b', '[CREDIT_CARD_REDACTED]', text)
        return text

    def _serialize_world_state(self, state: WorldState) -> Dict[str, Any]:
        return {
            "state_id": state.state_id,
            "timestamp": state.timestamp,
            "active_window": {
                "title": state.active_window.title,
                "process_name": state.active_window.process_name,
                "bounds": state.active_window.bounds,
                "is_minimized": state.active_window.is_minimized
            },
            "running_applications": state.running_applications,
            "clipboard_summary": state.clipboard_summary,
            "host_environment": {
                "cpu_usage_percent": state.host_environment.cpu_usage_percent,
                "available_memory_mb": state.host_environment.available_memory_mb,
                "network_status": state.host_environment.network_status,
                "power_source": state.host_environment.power_source,
                "battery_percent": state.host_environment.battery_percent
            },
            "task_state": {
                "active_plan_id": state.task_state.active_plan_id,
                "active_step_id": state.task_state.active_step_id,
                "executor_status": state.task_state.executor_status
            },
            "perceived_user_activity": state.perceived_user_activity,
            "detected_anomalies": state.detected_anomalies,
            "entities": [
                {"entity_id": n.entity_id, "entity_type": n.entity_type, "properties": n.properties}
                for n in state.entities
            ],
            "relationships": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relationship_type": e.relationship_type,
                    "properties": e.properties
                }
                for e in state.relationships
            ]
        }
