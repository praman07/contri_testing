from typing import Optional
import logging
from override.runtime.interfaces.runtime import IRuntimeCoordinator
from override.runtime.runtime.state import RuntimeState
from override.runtime.runtime.lifecycle import LifecycleManager
from override.runtime.container.container import ServiceContainer
from override.runtime.registry.registry import ModuleRegistry

# Get basic Python logger for bootstrapping before custom Logger service starts
logger = logging.getLogger("Override.Runtime")

class Runtime(IRuntimeCoordinator):
    """
    Core implementation of the IRuntimeCoordinator.
    Orchestrates the lifecycle, startup sequence, and shutdown sequence of Override.
    """

    def __init__(self, container: Optional[ServiceContainer] = None):
        self._lifecycle = LifecycleManager(RuntimeState.BOOTING)
        self._container = container

    def set_container(self, container: ServiceContainer) -> None:
        """Sets the service container for module resolution."""
        self._container = container

    def start(self) -> None:
        """
        Coordinates the startup sequence.
        Transitions state: BOOTING -> INITIALIZING -> READY -> RUNNING
        """
        try:
            logger.info("Initializing Override Runtime...")
            self._lifecycle.transition_to(RuntimeState.INITIALIZING)

            if self._container:
                # Discover modules first
                from override.runtime.bootstrap.discovery import discover_and_register_modules
                discover_and_register_modules(self._container)

                registry = self._container.resolve(ModuleRegistry)
                boot_order = registry.get_boot_order()
                logger.info(f"Topological module boot order: {boot_order}")

                # Initialize all modules in order
                for module_id in boot_order:
                    module = registry.get_module(module_id)
                    logger.info(f"Initializing module: {module_id}")
                    module.initialize()

                logger.info("Override services ready.")
                self._lifecycle.transition_to(RuntimeState.READY)

                # Start all modules in order
                for module_id in boot_order:
                    module = registry.get_module(module_id)
                    logger.info(f"Starting module: {module_id}")
                    module.start()
            else:
                logger.info("Override services ready (no container/modules discovered).")
                self._lifecycle.transition_to(RuntimeState.READY)

            logger.info("Running Override Cognitive loop.")
            self._lifecycle.transition_to(RuntimeState.RUNNING)

        except Exception as e:
            logger.critical(f"Abrupt boot failure: {e}", exc_info=True)
            self.stop()
            raise e

    def stop(self) -> None:
        """
        Coordinates the graceful shutdown sequence.
        Transitions state: -> STOPPING -> STOPPED
        """
        current_state = self._lifecycle.get_state()
        if current_state in (RuntimeState.STOPPING, RuntimeState.STOPPED):
            return

        logger.info("Initiating graceful shutdown...")
        self._lifecycle.transition_to(RuntimeState.STOPPING)

        if self._container:
            try:
                registry = self._container.resolve(ModuleRegistry)
                boot_order = registry.get_boot_order()
                # Stop modules in reverse topological order
                for module_id in reversed(boot_order):
                    module = registry.get_module(module_id)
                    if module.is_running:
                        logger.info(f"Stopping module: {module_id}")
                        module.stop()
            except Exception as e:
                logger.error(f"Error stopping modules during shutdown: {e}")

        logger.info("Override stopped.")
        self._lifecycle.transition_to(RuntimeState.STOPPED)

    def get_status(self) -> str:
        return self._lifecycle.get_state().name

