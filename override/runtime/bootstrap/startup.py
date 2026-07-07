import asyncio
import logging
from override.runtime.container.container import ServiceContainer
from override.runtime.logging.logger import LoggingService
from override.runtime.event.bus import EventBus
from override.runtime.interfaces.event import IEventBus
from override.runtime.runtime.runtime import Runtime

logger = logging.getLogger("Override.Bootstrap")

async def boot_system(container: ServiceContainer, runtime: Runtime) -> None:
    """
    Executes the step-by-step startup sequence.
    Attaches loggers, binds the asyncio loop to the Event Bus, and starts core loops.
    """
    loop = asyncio.get_running_loop()

    # 1. Initialize logging system
    log_service = container.resolve(LoggingService)
    log_service.initialize()
    
    logger.info("Structured logging service online.")

    # 2. Configure Event Bus loop
    event_bus = container.resolve(IEventBus)
    if isinstance(event_bus, EventBus):
        event_bus.set_event_loop(loop)
        logger.info("Event Bus async dispatcher active.")

    # 3. Start the Runtime Coordinator
    runtime.set_container(container)
    runtime.start()
    logger.info("Override Runtime Coordinator successfully booted.")

