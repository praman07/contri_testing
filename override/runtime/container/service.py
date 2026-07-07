from typing import Callable, Any, Optional
from override.runtime.container.lifetime import ServiceLifetime

class ServiceDescriptor:
    """
    Metadata describing a registered service.
    Tracks factory methods, registration lifetimes, and active singleton instances.
    """

    def __init__(
        self,
        service_type: type,
        factory: Callable[..., Any],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ):
        self.service_type = service_type
        self.factory = factory
        self.lifetime = lifetime
        self._instance: Optional[Any] = None

    def get_instance(self, *args, **kwargs) -> Any:
        """
        Resolves the service instance.
        Returns the cached singleton or executes the factory to build a new instance.
        """
        if self.lifetime == ServiceLifetime.SINGLETON:
            if self._instance is None:
                self._instance = self.factory(*args, **kwargs)
            return self._instance
        return self.factory(*args, **kwargs)
