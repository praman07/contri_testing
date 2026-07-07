from enum import Enum, auto

class ServiceLifetime(Enum):
    """
    Specifies the lifetime management of a service inside the
    Override dependency injection container.
    """
    SINGLETON = auto()  # Instance instantiated once and shared globally
    TRANSIENT = auto()  # New instance constructed on every resolution request
