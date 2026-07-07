from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Coroutine

class IEvent(ABC):
    """Immutable structural Event contract."""

    @property
    @abstractmethod
    def event_id(self) -> str:
        """Unique UUID for this event."""
        pass

    @property
    @abstractmethod
    def topic(self) -> str:
        """The channel/routing topic for this event."""
        pass

    @property
    @abstractmethod
    def source(self) -> str:
        """The module identifier that produced the event."""
        pass

    @property
    @abstractmethod
    def timestamp(self) -> str:
        """ISO 8601 UTC timestamp of event creation."""
        pass

    @property
    @abstractmethod
    def payload(self) -> Dict[str, Any]:
        """Immutable payload data dictionary."""
        pass


class IEventBus(ABC):
    """Core Event Bus subscription and routing contract."""

    @abstractmethod
    def publish(self, event: IEvent) -> None:
        """Dispatches an event asynchronously to all subscribed listeners."""
        pass

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[IEvent], Coroutine[Any, Any, None]]) -> None:
        """Subscribes an async callback handler to a specific topic."""
        pass

    @abstractmethod
    def unsubscribe(self, topic: str, callback: Callable[[IEvent], Coroutine[Any, Any, None]]) -> None:
        """Removes an active async callback handler from a topic."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the event bus and cancels any active background dispatch loops."""
        pass
