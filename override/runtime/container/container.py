import threading
from typing import Dict, Type, Any, Callable
from override.runtime.container.lifetime import ServiceLifetime
from override.runtime.container.service import ServiceDescriptor

class ServiceContainer:
    """
    Thread-safe Dependency Injection (DI) Container.
    Manages registration, lifetime, and resolution of system services.
    """

    def __init__(self):
        self._registry: Dict[Type, ServiceDescriptor] = {}
        self._lock = threading.RLock()

    def register(
        self,
        service_type: Type,
        factory: Callable[..., Any],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ) -> None:
        """Registers a service type with its factory and lifetime policy."""
        with self._lock:
            if service_type in self._registry:
                # To enforce dependency stability, prevent re-registration
                raise ValueError(f"Service {service_type.__name__} is already registered.")
            
            self._registry[service_type] = ServiceDescriptor(service_type, factory, lifetime)

    def resolve(self, service_type: Type[Any]) -> Any:
        """
        Resolves and returns the requested service instance.
        Raises ValueError if the service is unregistered.
        """
        with self._lock:
            descriptor = self._registry.get(service_type)
            if not descriptor:
                raise ValueError(f"No service registered for type: {service_type.__name__}")
            
            # Resolve dependencies by recursively resolving arguments if needed
            # For simplicity, concrete factories handle their own parameter fetching,
            # or the container can pass itself as a dependency resolution helper.
            return descriptor.get_instance(container=self)
