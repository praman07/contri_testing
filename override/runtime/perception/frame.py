import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass(frozen=True)
class PerceptionFrame:
    """
    Immutable structured knowledge record produced by the Perception Engine.
    Represents the engine's understanding of the environment at a specific point in time.
    Consumed by the Context Engine (Layer 04).
    """
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    source_event_id: str = ""

    # Active window context
    active_window_title: str = ""
    active_window_class: str = ""
    active_app_category: str = "unknown"  # browser | ide | terminal | media | comms | office | unknown

    # Extracted content
    ocr_text: str = ""
    speech_transcript: str = ""
    clipboard_text_type: str = "empty"  # code | url | plain_text | empty

    # Named entities extracted from screen or speech
    detected_entities: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary for Event Bus payload transport."""
        return asdict(self)
