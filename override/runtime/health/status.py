from enum import Enum, auto

class HealthStatus(Enum):
    """
    Status classifications representing the health level of a registered
    service, module, or the general runtime.
    """
    HEALTHY = auto()
    DEGRADED = auto()
    CRITICAL = auto()
