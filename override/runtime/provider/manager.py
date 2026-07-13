import logging
from typing import Dict, Any, Optional
from override.runtime.provider.registry import ProviderRegistry
from override.runtime.provider.provider import ExecutionProvider

logger = logging.getLogger("Override.ProviderManager")

class ProviderManager:
    """
    Coordinates execution providers.
    Handles task dispatch, action routing, and provider lifecycle sequencing.
    """

    def __init__(self):
        self._registry = ProviderRegistry()

    def register_provider(self, provider: ExecutionProvider) -> None:
        """Registers a provider and initiates its setup hooks."""
        logger.info(f"Registering execution provider: {provider.provider_id}")
        self._registry.register(provider)
        try:
            provider.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize provider '{provider.provider_id}': {e}", exc_info=True)
            raise e

    def get_provider(self, provider_id: str) -> Optional[ExecutionProvider]:
        return self._registry.get_provider(provider_id)

    async def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches an action request to the matching capability provider.
        Raises ValueError if no matching provider is registered.
        """
        provider = self._registry.find_provider_for_action(action_name)
        if not provider:
            raise ValueError(f"No registered execution provider found for action: {action_name}")

        logger.debug(f"Routing action '{action_name}' to provider '{provider.provider_id}'")
        try:
            return await provider.execute(action_name, params)
        except Exception as e:
            logger.error(f"Execution failed for action '{action_name}' on provider '{provider.provider_id}': {e}", exc_info=True)
            raise e

    def shutdown(self) -> None:
        """Gracefully tears down all active execution providers."""
        providers = self._registry.get_all_providers()
        for provider in providers:
            logger.info(f"Stopping provider: {provider.provider_id}")
            try:
                provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down provider '{provider.provider_id}': {e}", exc_info=True)
