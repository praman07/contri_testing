import asyncio
import logging
import threading
from typing import Dict, List, Set, Callable, Coroutine, Any, Optional
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.subscriber import EventSubscriber
from override.runtime.event.publisher import EventPublisher

logger = logging.getLogger("Override.EventBus")

class EventBus(IEventBus):
    """
    Asynchronous Event Bus using an asyncio.Queue.
    Supports thread-safe event publishing and concurrent dispatcher execution.
    """

    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: List[EventSubscriber] = []
        self._lock = threading.RLock()
        
        # Async-specific coordination
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._max_queue_size = max_queue_size
        self._publisher = EventPublisher(self)
        
        # Buffer for events published prior to event loop bootstrap
        self._bootstrap_buffer: List[IEvent] = []

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Configures the asyncio event loop and initializes queues/worker."""
        with self._lock:
            self._loop = loop
            # Initialize queue in context of the target loop
            self._queue = asyncio.Queue(maxsize=self._max_queue_size)
            self._worker_task = loop.create_task(self._dispatch_loop())
            
            # Flush early bootstrap buffered events
            while self._bootstrap_buffer:
                event = self._bootstrap_buffer.pop(0)
                try:
                    self._queue.put_nowait(event)
                    logger.debug(f"Flushed bootstrap event to queue: {event.topic}")
                except asyncio.QueueFull:
                    logger.error(f"Event queue full during bootstrap flush. Dropped: {event.topic}")

    def publish(self, event: IEvent) -> None:
        """Direct implementation of IEventBus interface."""
        self._publisher.publish(event)

    def enqueue_event(self, event: IEvent) -> None:
        """
        Thread-safe method to enqueue an event for routing.
        Buffers events if loop is uninitialized, otherwise puts them into the queue.
        """
        with self._lock:
            if self._loop is None or self._queue is None:
                self._bootstrap_buffer.append(event)
                logger.info(f"Buffered boot event: {event.topic}")
                return

        def _enqueue():
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.error(f"Event queue full. Dropped event: {event.topic} (ID: {event.event_id})")

        if self._loop.is_running():
            self._loop.call_soon_threadsafe(_enqueue)
        else:
            logger.warning(f"Event loop not running. Dropping event: {event.topic}")

    def stop(self) -> None:
        """Stops the event bus dispatch loops and clears buffers."""
        with self._lock:
            if self._loop and self._worker_task and not self._worker_task.done():
                self._loop.call_soon_threadsafe(self._worker_task.cancel)
                logger.info("Cancelled Event Bus dispatch worker task.")
            self._bootstrap_buffer.clear()

    def subscribe(self, topic: str, callback: Callable[[IEvent], Coroutine[Any, Any, None]]) -> None:
        with self._lock:
            self._subscribers.append(EventSubscriber(topic, callback))
            logger.debug(f"Subscribed callback to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable[[IEvent], Coroutine[Any, Any, None]]) -> None:
        with self._lock:
            initial_count = len(self._subscribers)
            self._subscribers = [
                sub for sub in self._subscribers 
                if not (sub.topic_pattern == topic and sub.callback == callback)
            ]
            if len(self._subscribers) < initial_count:
                logger.debug(f"Unsubscribed callback from topic: {topic}")

    async def _dispatch_loop(self) -> None:
        """Continuously pulls events from the queue and routes to matching subscribers."""
        logger.info("Event Bus dispatch loop active.")
        while True:
            try:
                event = await self._queue.get()
                
                with self._lock:
                    # Capture current subscribers under lock
                    targets = [sub for sub in self._subscribers if sub.matches(event.topic)]

                # Dispatch concurrently
                for sub in targets:
                    asyncio.create_task(self._safe_invoke(sub.callback, event))
                
                self._queue.task_done()
            except asyncio.CancelledError:
                logger.info("Event Bus dispatch loop cancelling.")
                break
            except Exception as e:
                logger.error(f"Error in Event Bus dispatch worker: {e}", exc_info=True)

    async def _safe_invoke(self, callback: Callable[[IEvent], Coroutine[Any, Any, None]], event: IEvent) -> None:
        """Executes a subscriber callback inside a try/catch bubble to prevent propagation failures."""
        try:
            await callback(event)
        except Exception as e:
            logger.error(f"Error executing callback on topic '{event.topic}': {e}", exc_info=True)
