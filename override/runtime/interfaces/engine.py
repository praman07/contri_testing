from abc import ABC, abstractmethod

class ICognitiveEngine(ABC):
    """
    Interface defining the operational contract for a cognitive engine module
    within the Override runtime.
    """

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Unique identifier of the cognitive engine module."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initializes the engine module, registering events and validating assets."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts engine execution loops or subscription hooks."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops active threads or processes owned by this engine."""
        pass
