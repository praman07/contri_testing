from abc import abstractmethod
from override.runtime.interfaces.engine import ICognitiveEngine

class OverrideModule(ICognitiveEngine):
    """
    Abstract base class for all Override cognitive engine layers.
    Forces compliance with engine lifecycle states and dependency injection patterns.
    """

    def __init__(self, module_id: str):
        self._module_id = module_id
        self._initialized = False
        self._running = False

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_running(self) -> bool:
        return self._running

    def initialize(self) -> None:
        if self._initialized:
            return
        self.on_initialize()
        self._initialized = True

    def start(self) -> None:
        if not self._initialized:
            raise RuntimeError(f"Cannot start uninitialized module: {self._module_id}")
        if self._running:
            return
        self.on_start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self.on_stop()
        self._running = False

    @abstractmethod
    def on_initialize(self) -> None:
        """Module-specific initialization hook."""
        pass

    @abstractmethod
    def on_start(self) -> None:
        """Module-specific start hook."""
        pass

    @abstractmethod
    def on_stop(self) -> None:
        """Module-specific stop hook."""
        pass
