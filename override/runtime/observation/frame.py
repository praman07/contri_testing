from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass(frozen=True)
class ObservationFrame:
    """
    Immutable representation of an environment signal observation.
    Carries source metadata, timestamps, and unstructured sensor/signal payloads.
    """
    timestamp: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
