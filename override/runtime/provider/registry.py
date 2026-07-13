import threading
from typing import Dict, List, Optional
from override.runtime.provider.provider import ExecutionProvider

class ProviderRegistry:
    """
    Registry store for active Execution Providers.
    Allows routing tasks dynamically based on registered capabilities.
    """

    def __init__(self):
        self._providers: Dict[str, ExecutionProvider] = {}
        self._lock = threading.RLock()

    def register(self, provider: ExecutionProvider) -> None:
        with self._lock:
            if provider.provider_id in self._providers:
                raise ValueError(f"Provider '{provider.provider_id}' is already registered.")
            self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[ExecutionProvider]:
        with self._lock:
            return self._providers.get(provider_id)

    def get_all_providers(self) -> List[ExecutionProvider]:
        with self._lock:
            return list(self._providers.values())

    def find_provider_for_action(self, action_name: str) -> Optional[ExecutionProvider]:
        """Scans registered providers to locate one that supports the requested action."""
        with self._lock:
            for provider in self._providers.values():
                if provider.can_execute(action_name):
                    return provider
            return None
