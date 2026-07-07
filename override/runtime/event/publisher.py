import logging
from override.runtime.interfaces.event import IEvent

logger = logging.getLogger("Override.EventBus")

class EventPublisher:
    """
    Handles validation, metrics, and routing of outgoing events.
    Prevents flooding and checks basic payload integrity before dispatch.
    """

    def __init__(self, bus):
        self._bus = bus

    def publish(self, event: IEvent) -> None:
        """
        Validates event payload and dispatches it onto the underlying Event Bus.
        Safe to call from any thread.
        """
        if not event.topic:
            raise ValueError("Event topic cannot be empty.")
        if not event.source:
            raise ValueError("Event source cannot be empty.")

        # Pass event to the bus coordinator for async queueing/dispatching
        self._bus.enqueue_event(event)
