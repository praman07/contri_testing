from abc import abstractmethod
from typing import Dict, Any, List
from override.runtime.interfaces.provider import IExecutionProvider

class ExecutionProvider(IExecutionProvider):
    """
    Abstract base class for all execution providers.
    Provides standard capability registration patterns.
    """

    def __init__(self, provider_id: str, supported_actions: List[str]):
        self._provider_id = provider_id
        self._supported_actions = set(supported_actions)
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def can_execute(self, action_name: str) -> bool:
        return action_name in self._supported_actions

    def initialize(self) -> None:
        """Hook to initialize external resources (e.g. browser, file system handlers)."""
        if self._initialized:
            return
        self.on_initialize()
        self._initialized = True

    def shutdown(self) -> None:
        """Hook to release resources on shutdown."""
        if not self._initialized:
            return
        self.on_shutdown()
        self._initialized = False

    @abstractmethod
    def on_initialize(self) -> None:
        pass

    @abstractmethod
    def on_shutdown(self) -> None:
        pass
