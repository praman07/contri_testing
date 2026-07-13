from abc import ABC, abstractmethod
from typing import Callable, Any
from override.runtime.observation.frame import ObservationFrame

class IObservationProvider(ABC):
    """
    Interface defining the lifecycle and communication protocol for all
    signal collection providers in the Observation Engine.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier of the provider."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initializes system resources, opens handles, and sets up hooks."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts background monitoring, recording loops, or active polling."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops running loops, drops OS hooks, and releases handles."""
        pass

    @abstractmethod
    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        """Registers a callback method for publishing captured ObservationFrames."""
        pass
