from abc import ABC, abstractmethod
from typing import Dict, Any

class IExecutionProvider(ABC):
    """
    Interface defining the execution contract for stateless action providers
    (e.g., Browser automation, Filesystem manipulation, Command execution).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier of the execution provider."""
        pass

    @abstractmethod
    def can_execute(self, action_name: str) -> bool:
        """Determines if this provider supports the given action."""
        pass

    @abstractmethod
    async def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously executes the action with the given parameters.
        Returns a dictionary containing the execution outcome.
        """
        pass
