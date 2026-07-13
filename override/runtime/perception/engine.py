"""
Layer 03 — Perception Engine

Transforms raw observation signals into structured PerceptionFrames.
Operates purely event-driven: subscribes to Observation and Environment
events, processes them in a background thread pool, and publishes
perception facts back to the Event Bus.

Architectural constraints:
  - Never calls the PAL directly.
  - Never calls higher-layer subsystems directly.
  - Never performs planning, reasoning, or memory writes.
  - All OS facts arrive via Event Bus payloads from Layer 01 and Layer 02.
"""
import logging
import datetime
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Dict, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.perception.frame import PerceptionFrame
from override.runtime.perception.classifiers import classify_app
from override.runtime.perception.clipboard_classifier import classify_clipboard
from override.runtime.perception.ocr_provider import extract_text_from_bytes

logger = logging.getLogger("Override.Perception.Engine")

# Maximum workers for background perception tasks (OCR etc.)
_MAX_WORKERS = 2


class PerceptionEngine(OverrideModule):
    """
    Layer 03 — Perception Engine.

    Converts raw observation and environment events into structured
    PerceptionFrame records and publishes them via the Event Bus.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        config: ConfigurationManager
    ):
        super().__init__("perception_engine")
        self._event_bus = event_bus
        self._config = config

        # Latest environment state — updated by event subscriptions
        self._lock = threading.RLock()
        self._active_window: Dict[str, Any] = {}
        self._clipboard_state: Dict[str, Any] = {}
        self._current_speech_transcript: str = ""

        # Thread pool for expensive perception tasks (e.g. OCR)
        self._executor: Optional[ThreadPoolExecutor] = None

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        logger.info("Initializing Perception Engine...")

        # Subscribe to Observation events
        self._event_bus.subscribe("observation.screen_captured", self._on_screen_captured)
        self._event_bus.subscribe("observation.audio_captured", self._on_audio_captured)
        self._event_bus.subscribe("observation.window_changed", self._on_window_changed)

        # Subscribe to Environment events to stay current
        self._event_bus.subscribe("environment.window_focused", self._on_env_window_focused)
        self._event_bus.subscribe("environment.updated", self._on_environment_updated)

        logger.info("Perception Engine initialized.")

    def on_start(self) -> None:
        logger.info("Starting Perception Engine...")

        # Start thread pool for non-blocking perception work
        self._executor = ThreadPoolExecutor(
            max_workers=_MAX_WORKERS,
            thread_name_prefix="Override.Perception.Worker"
        )

        self._event_bus.publish(Event(
            _topic="perception.engine.started",
            _source="perception_engine",
            _payload={}
        ))
        logger.info("Perception Engine started successfully.")

    def on_stop(self) -> None:
        logger.info("Stopping Perception Engine...")

        # Shutdown thread pool gracefully
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("Perception Engine thread pool shut down.")

        # Unsubscribe all event handlers
        self._event_bus.unsubscribe("observation.screen_captured", self._on_screen_captured)
        self._event_bus.unsubscribe("observation.audio_captured", self._on_audio_captured)
        self._event_bus.unsubscribe("observation.window_changed", self._on_window_changed)
        self._event_bus.unsubscribe("environment.window_focused", self._on_env_window_focused)
        self._event_bus.unsubscribe("environment.updated", self._on_environment_updated)

        self._event_bus.publish(Event(
            _topic="perception.engine.stopped",
            _source="perception_engine",
            _payload={}
        ))
        logger.info("Perception Engine stopped.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_current_frame(self) -> PerceptionFrame:
        """
        Assembles and returns the current PerceptionFrame from the latest
        known state. Does not publish an event — for direct synchronous query.
        """
        with self._lock:
            return self._build_frame(source_event_id="direct_query", ocr_text="")

    # ------------------------------------------------------------------
    # Event handlers — run on the EventBus dispatch loop (async)
    # ------------------------------------------------------------------

    async def _on_screen_captured(self, event: IEvent) -> None:
        """
        Handles observation.screen_captured events.
        Dispatches OCR work to thread pool to avoid blocking the Event Bus.
        """
        payload = event.payload or {}
        image_bytes: bytes = payload.get("image_bytes", b"")
        event_id: str = getattr(event, "event_id", str(uuid.uuid4()))

        if self._executor and image_bytes:
            self._executor.submit(self._run_ocr_and_publish, image_bytes, event_id)

    async def _on_audio_captured(self, event: IEvent) -> None:
        """
        Handles observation.audio_captured events.
        Normalizes speech transcript if present in payload.
        """
        payload = event.payload or {}
        transcript: str = payload.get("transcript", "").strip()

        if not transcript:
            return

        normalized = self._normalize_transcript(transcript)
        with self._lock:
            self._current_speech_transcript = normalized

        self._event_bus.publish(Event(
            _topic="perception.speech_recognized",
            _source="perception_engine",
            _payload={"transcript": normalized}
        ))

        self._publish_frame(
            source_event_id=getattr(event, "event_id", "audio"),
            ocr_text=""
        )

    async def _on_window_changed(self, event: IEvent) -> None:
        """
        Handles observation.window_changed events — window focus change signal
        from the Observation Engine. Immediately reclassifies the active app.
        """
        payload = event.payload or {}
        with self._lock:
            self._active_window = payload

        self._publish_window_context(payload)
        self._publish_frame(
            source_event_id=getattr(event, "event_id", "window"),
            ocr_text=""
        )

    async def _on_env_window_focused(self, event: IEvent) -> None:
        """
        Handles environment.window_focused events from Layer 02.
        Updates internal active window state and reclassifies.
        """
        payload = event.payload or {}
        with self._lock:
            self._active_window = payload

        self._publish_window_context(payload)

    async def _on_environment_updated(self, event: IEvent) -> None:
        """
        Handles environment.updated events from Layer 02.
        Refreshes clipboard state and active window from full snapshot payload.
        """
        payload = event.payload or {}
        with self._lock:
            if "active_window" in payload:
                self._active_window = payload["active_window"]
            if "clipboard_state" in payload:
                self._clipboard_state = payload["clipboard_state"]
                self._classify_and_publish_clipboard()

    # ------------------------------------------------------------------
    # Internal workers
    # ------------------------------------------------------------------

    def _run_ocr_and_publish(self, image_bytes: bytes, event_id: str) -> None:
        """Runs in thread pool. Performs OCR and publishes result."""
        try:
            ocr_text = extract_text_from_bytes(image_bytes)
            if ocr_text:
                self._event_bus.publish(Event(
                    _topic="perception.screen_text_extracted",
                    _source="perception_engine",
                    _payload={"ocr_text": ocr_text}
                ))
                self._publish_frame(source_event_id=event_id, ocr_text=ocr_text)
        except Exception as e:
            logger.error(f"OCR worker failed: {e}", exc_info=True)

    def _publish_window_context(self, window_payload: Dict[str, Any]) -> None:
        """Classifies window context and publishes a perception event."""
        title = window_payload.get("title", "")
        class_name = window_payload.get("class_name", "")
        exe_name = window_payload.get("exe_name", "")
        category = classify_app(title, class_name, exe_name)

        self._event_bus.publish(Event(
            _topic="perception.window_context_classified",
            _source="perception_engine",
            _payload={
                "title": title,
                "class_name": class_name,
                "category": category,
                "pid": window_payload.get("pid", 0)
            }
        ))

    def _classify_and_publish_clipboard(self) -> None:
        """Classifies clipboard content and publishes a perception event."""
        with self._lock:
            clip = dict(self._clipboard_state)

        clip_type = classify_clipboard(clip)
        self._event_bus.publish(Event(
            _topic="perception.clipboard_classified",
            _source="perception_engine",
            _payload={"clipboard_text_type": clip_type}
        ))

    def _publish_frame(self, source_event_id: str, ocr_text: str) -> None:
        """Assembles and publishes a complete PerceptionFrame."""
        with self._lock:
            frame = self._build_frame(source_event_id=source_event_id, ocr_text=ocr_text)

        self._event_bus.publish(Event(
            _topic="perception.frame_ready",
            _source="perception_engine",
            _payload=frame.to_dict()
        ))

    def _build_frame(self, source_event_id: str, ocr_text: str) -> PerceptionFrame:
        """
        Builds a PerceptionFrame from current internal state.
        Must be called within self._lock context (or with a local copy of state).
        """
        window = self._active_window
        title = window.get("title", "")
        class_name = window.get("class_name", "")
        exe_name = window.get("exe_name", "")

        category = classify_app(title, class_name, exe_name)
        clip_type = classify_clipboard(self._clipboard_state)

        return PerceptionFrame(
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            source_event_id=source_event_id,
            active_window_title=title,
            active_window_class=class_name,
            active_app_category=category,
            ocr_text=ocr_text,
            speech_transcript=self._current_speech_transcript,
            clipboard_text_type=clip_type,
            detected_entities=[]
        )

    @staticmethod
    def _normalize_transcript(raw: str) -> str:
        """
        Performs minimal normalization on a speech transcript:
        strips leading/trailing whitespace, collapses internal whitespace.
        Does not perform NLP or AI inference.
        """
        import re
        return re.sub(r"\s+", " ", raw).strip()
