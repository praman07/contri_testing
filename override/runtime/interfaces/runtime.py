from abc import ABC, abstractmethod

class IRuntimeCoordinator(ABC):
    """
    Interface defining the lifecycle contracts for the core Runtime Coordinator.
    Implemented by the Runtime Foundation.
    """

    @abstractmethod
    def start(self) -> None:
        """Starts the runtime initialization and service setup sequence."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Initiates the graceful shutdown sequence and stops active services."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Returns the current state name of the runtime."""
        pass
