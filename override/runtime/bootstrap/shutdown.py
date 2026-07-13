import logging
from override.runtime.container.container import ServiceContainer
from override.runtime.provider.manager import ProviderManager
from override.runtime.runtime.runtime import Runtime

logger = logging.getLogger("Override.Bootstrap")

def graceful_shutdown(container: ServiceContainer, runtime: Runtime) -> None:
    """
    Coordinates the graceful shutdown steps.
    Shuts down providers, flushes state, and updates coordinator state.
    """
    logger.info("Initiating graceful system tear-down...")

    # 1. Stop active execution providers
    try:
        prov_mgr = container.resolve(ProviderManager)
        prov_mgr.shutdown()
        logger.info("Execution providers successfully stopped.")
    except Exception as e:
        logger.error(f"Error during provider manager teardown: {e}")

    # 2. Stop the Event Bus
    try:
        from override.runtime.interfaces.event import IEventBus
        event_bus = container.resolve(IEventBus)
        event_bus.stop()
        logger.info("Event Bus async dispatcher stopped.")
    except Exception as e:
        logger.error(f"Error stopping Event Bus during teardown: {e}")

    # 3. Stop the Runtime Coordinator
    try:
        runtime.stop()
        logger.info("Runtime Coordinator stopped.")
    except Exception as e:
        logger.error(f"Error during runtime teardown: {e}")

    logger.info("Override tear-down complete.")
