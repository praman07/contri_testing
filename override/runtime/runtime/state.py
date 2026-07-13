from enum import Enum, auto

class RuntimeState(Enum):
    """
    Enums representing the strict, deterministic lifecycle states of
    the Override Cognitive Runtime.
    """
    BOOTING = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
