import fnmatch
from typing import Callable, Any, Coroutine
from override.runtime.interfaces.event import IEvent

class EventSubscriber:
    """
    Wraps subscriber callbacks.
    Supports routing wildcard patterns (e.g., 'engine.*', 'system.error').
    """

    def __init__(
        self,
        topic_pattern: str,
        callback: Callable[[IEvent], Coroutine[Any, Any, None]]
    ):
        self.topic_pattern = topic_pattern
        self.callback = callback

    def matches(self, topic: str) -> bool:
        """Determines if this subscriber matches the published event topic."""
        # Use shell-style wildcards for topic matching
        return fnmatch.fnmatchcase(topic, self.topic_pattern)
