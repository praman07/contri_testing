import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any
from override.runtime.interfaces.event import IEvent

@dataclass(frozen=True)
class Event(IEvent):
    """
    Immutable implementation of the IEvent contract.
    Guarantees event data cannot be modified in-flight by subscribers.
    """
    _topic: str
    _source: str
    _payload: Dict[str, Any] = field(default_factory=dict)
    _event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def source(self) -> str:
        return self._source

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @property
    def payload(self) -> Dict[str, Any]:
        # Return a copy of the dictionary to enforce payload immutability
        return dict(self._payload)
