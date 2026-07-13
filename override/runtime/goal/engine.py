import logging
from datetime import datetime
import threading
import uuid
from typing import List, Dict, Any, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.goal import IGoalEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.goal.models import GoalNode
from override.runtime.goal.tree import GoalTree

logger = logging.getLogger("Override.GoalEngine")

class GoalEngine(OverrideModule, IGoalEngine):
    """
    Layer 10 — Goal Engine.
    Represents and organizes user objectives, processes execution results to
    rollup progress, and triggers warnings for context deviations or priority conflicts.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        config: ConfigurationManager
    ):
        super().__init__("goal_engine")
        self._event_bus = event_bus
        self._config = config
        self._lock = threading.RLock()

        # In-memory Goal Hierarchy
        self._tree = GoalTree()

        # Context/Planning Mappings
        self._plan_to_goal_map: Dict[str, str] = {}
        self._deviation_timers: Dict[str, datetime] = {}
        self._deviation_threshold_seconds = 900.0  # 15 minutes default

    @property
    def deviation_threshold_seconds(self) -> float:
        return self._deviation_threshold_seconds

    @deviation_threshold_seconds.setter
    def deviation_threshold_seconds(self, val: float) -> None:
        self._deviation_threshold_seconds = val

    # ------------------------------------------------------------------
    # ICognitiveEngine Lifecycle Hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        """Register subscriptions for all goal inputs."""
        logger.info("Initializing Goal Engine...")

        # Subscriptions
        self._event_bus.subscribe("context.updated", self._on_context_updated)
        self._event_bus.subscribe("verification.passed", self._on_verification_passed)
        self._event_bus.subscribe("verification.failed", self._on_verification_failed)
        self._event_bus.subscribe("planning.plan_started", self._on_plan_started)
        self._event_bus.subscribe("planning.plan_completed", self._on_plan_finished)
        self._event_bus.subscribe("planning.plan_aborted", self._on_plan_finished)
        self._event_bus.subscribe("system.shutdown", self._on_system_shutdown)

        logger.info("Goal Engine initialized.")

    def on_start(self) -> None:
        logger.info("Goal Engine started.")

    def on_stop(self) -> None:
        logger.info("Stopping Goal Engine...")
        with self._lock:
            self._tree.clear()
            self._plan_to_goal_map.clear()
            self._deviation_timers.clear()
        logger.info("Goal Engine stopped.")

    # ------------------------------------------------------------------
    # IGoalEngine Interface Methods
    # ------------------------------------------------------------------

    async def create_goal(
        self,
        title: str,
        description: str,
        parent_goal_id: Optional[str] = None,
        priority: int = 3,
        target_date: Optional[str] = None,
        criteria: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Creates a new goal node in the hierarchy (defaults to DRAFT state)."""
        with self._lock:
            # Parse target date
            t_date = None
            if target_date:
                try:
                    cleaned_date = target_date.replace("Z", "+00:00")
                    t_date = datetime.fromisoformat(cleaned_date)
                except Exception as e:
                    logger.warning(f"Failed to parse target date {target_date}: {e}")

            goal_id = str(uuid.uuid4())
            node = GoalNode(
                goal_id=goal_id,
                title=title,
                description=description,
                parent_goal_id=parent_goal_id,
                priority=max(1, min(5, priority)),
                state="DRAFT",
                progress_percent=0.0,
                target_date=t_date,
                blockers=[],
                criteria=criteria or [],
                tags=tags or []
            )

            self._tree.add_node(node)

            # Publish goal created
            self._event_bus.publish(Event(
                _topic="goal.node_created",
                _source="goal_engine",
                _payload=node.to_dict()
            ))

            return node.to_dict()

    async def update_goal_state(
        self,
        goal_id: str,
        state: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transitions the lifecycle state of a goal."""
        with self._lock:
            node, state_changes = self._tree.update_node_state(goal_id, state)
            
            # Publish all state changes (including cascading completions)
            for cid, old, new in state_changes:
                self._event_bus.publish(Event(
                    _topic="goal.state_changed",
                    _source="goal_engine",
                    _payload={
                        "goal_id": cid,
                        "old_state": old,
                        "new_state": new,
                        "reason": reason or f"Manual state transition to {new}"
                    }
                ))

                # Check and resolve conflicts immediately if transitioned to ACTIVE
                if new == "ACTIVE":
                    self._resolve_conflicts(cid)

            return node.to_dict()

    async def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a goal's detail map by ID."""
        with self._lock:
            node = self._tree.get_node(goal_id)
            return node.to_dict() if node else None

    async def get_goal_hierarchy(self) -> List[Dict[str, Any]]:
        """Returns the tree representation of all goals."""
        with self._lock:
            return self._tree.serialize_hierarchy()

    async def get_active_goals(self) -> List[Dict[str, Any]]:
        """Retrieves all goals currently in the ACTIVE state."""
        with self._lock:
            active_nodes = [n for n in self._tree.get_all_nodes() if n.state == "ACTIVE"]
            return [n.to_dict() for n in active_nodes]

    async def record_progress(
        self,
        goal_id: str,
        progress_percent: float,
        update_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records progress percentage update for a specific goal."""
        with self._lock:
            node, delta, state_changes = self._tree.update_node_progress(goal_id, progress_percent)

            if delta != 0.0:
                self._event_bus.publish(Event(
                    _topic="goal.progress_updated",
                    _source="goal_engine",
                    _payload={
                        "goal_id": goal_id,
                        "progress_percent": node.progress_percent,
                        "delta": delta
                    }
                ))

            # Publish any cascading state change events
            for cid, old, new in state_changes:
                self._event_bus.publish(Event(
                    _topic="goal.state_changed",
                    _source="goal_engine",
                    _payload={
                        "goal_id": cid,
                        "old_state": old,
                        "new_state": new,
                        "reason": update_description or f"Progress rollup to {progress_percent}%"
                    }
                ))

            return node.to_dict()

    # ------------------------------------------------------------------
    # Conflict Resolution logic
    # ------------------------------------------------------------------

    def _resolve_conflicts(self, goal_id: str) -> None:
        """Checks for and resolves tag-based conflicts for active goals."""
        target_node = self._tree.get_node(goal_id)
        if not target_node or target_node.state != "ACTIVE":
            return

        active_nodes = [n for n in self._tree.get_all_nodes() if n.state == "ACTIVE" and n.goal_id != goal_id]
        
        for active_node in active_nodes:
            overlap = set(target_node.tags) & set(active_node.tags)
            if overlap:
                conflict_tag = list(overlap)[0]

                # Publish conflict detected event
                self._event_bus.publish(Event(
                    _topic="goal.conflict_detected",
                    _source="goal_engine",
                    _payload={
                        "goal_id_1": target_node.goal_id,
                        "goal_id_2": active_node.goal_id,
                        "conflict_tag": conflict_tag
                    }
                ))

                # Resolve based on priority
                if target_node.priority > active_node.priority:
                    # Target node is higher priority: pause the existing active node
                    self._tree.update_node_state(active_node.goal_id, "PAUSED")
                    self._event_bus.publish(Event(
                        _topic="goal.state_changed",
                        _source="goal_engine",
                        _payload={
                            "goal_id": active_node.goal_id,
                            "old_state": "ACTIVE",
                            "new_state": "PAUSED",
                            "reason": f"Conflict with higher-priority goal {target_node.goal_id} on tag {conflict_tag}"
                        }
                    ))
                else:
                    # Existing active node has higher or equal priority: pause the target node
                    self._tree.update_node_state(target_node.goal_id, "PAUSED")
                    self._event_bus.publish(Event(
                        _topic="goal.state_changed",
                        _source="goal_engine",
                        _payload={
                            "goal_id": target_node.goal_id,
                            "old_state": "ACTIVE",
                            "new_state": "PAUSED",
                            "reason": f"Conflict with higher-priority active goal {active_node.goal_id} on tag {conflict_tag}"
                        }
                    ))
                    # Break because target_node is no longer active, so it cannot conflict with other active nodes
                    break

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_context_updated(self, event: IEvent) -> None:
        """Processes window changes and clipboard context to check deviation constraints."""
        payload = event.payload or {}
        active_window = payload.get("active_window", {})
        proc_name = active_window.get("process_name")
        
        # Check active goals
        with self._lock:
            active_goals = [n for n in self._tree.get_all_nodes() if n.state == "ACTIVE"]
            for goal in active_goals:
                is_mismatch = False
                dev_type = None
                details = None

                # Mismatch logic:
                # Rule 1: watched process (YouTube, Netflix, etc.) during focuses tasks
                if proc_name == "YouTube" and ("Write Code" in goal.title or "requires_focus" in goal.tags):
                    is_mismatch = True
                    dev_type = "distracting_media_usage"
                    details = "User is focused on YouTube instead of goal."
                elif proc_name == "Netflix" and ("requires_focus" in goal.tags):
                    is_mismatch = True
                    dev_type = "distracting_media_usage"
                    details = "User is focused on Netflix instead of goal."
                elif proc_name in ["Facebook", "Twitter", "distracting_app"] and ("requires_focus" in goal.tags):
                    is_mismatch = True
                    dev_type = "social_media_distraction"
                    details = f"User is focused on {proc_name} instead of goal."

                if is_mismatch:
                    if goal.goal_id not in self._deviation_timers:
                        self._deviation_timers[goal.goal_id] = datetime.utcnow()
                    
                    elapsed = (datetime.utcnow() - self._deviation_timers[goal.goal_id]).total_seconds()
                    if elapsed >= self._deviation_threshold_seconds:
                        self._event_bus.publish(Event(
                            _topic="goal.deviation_detected",
                            _source="goal_engine",
                            _payload={
                                "goal_id": goal.goal_id,
                                "deviation_type": dev_type,
                                "details": details,
                                "severity": "warning"
                            }
                        ))
                else:
                    self._deviation_timers.pop(goal.goal_id, None)

    async def _on_verification_passed(self, event: IEvent) -> None:
        """Sets matching goal to COMPLETED if plan verification passes."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        if not plan_id:
            return

        with self._lock:
            goal_id = self._plan_to_goal_map.get(plan_id)
            if goal_id:
                node = self._tree.get_node(goal_id)
                if node and node.state == "ACTIVE":
                    await self.update_goal_state(
                        goal_id,
                        "COMPLETED",
                        f"Verification passed for plan {plan_id}"
                    )

    async def _on_verification_failed(self, event: IEvent) -> None:
        """Sets matching goal to BLOCKED if plan verification fails."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        if not plan_id:
            return

        with self._lock:
            goal_id = self._plan_to_goal_map.get(plan_id)
            if goal_id:
                node = self._tree.get_node(goal_id)
                if node and node.state == "ACTIVE":
                    node.blockers.append(f"Verification failed for plan {plan_id}")
                    await self.update_goal_state(
                        goal_id,
                        "BLOCKED",
                        f"Verification failed for plan {plan_id}"
                    )

    async def _on_plan_started(self, event: IEvent) -> None:
        """Links plan ID to Goal ID."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        goal_id = payload.get("goal_id")
        if plan_id and goal_id:
            with self._lock:
                self._plan_to_goal_map[plan_id] = goal_id

    async def _on_plan_finished(self, event: IEvent) -> None:
        """Cleans up plan mapping."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        if plan_id:
            with self._lock:
                self._plan_to_goal_map.pop(plan_id, None)

    async def _on_system_shutdown(self, event: IEvent) -> None:
        self.stop()
