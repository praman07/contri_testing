from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

class IModelClient(ABC):
    """
    Interface defining standard model execution contracts
    (e.g., chat completions, embeddings generation).
    """

    @abstractmethod
    async def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        """Asynchronously queries the target model and returns a text response."""
        pass

    @abstractmethod
    async def stream_response(self, prompt: str, system_instruction: str = "") -> AsyncGenerator[str, None]:
        """Asynchronously streams model response tokens."""
        pass
