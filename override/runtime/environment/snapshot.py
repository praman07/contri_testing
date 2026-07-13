import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass(frozen=True)
class EnvironmentSnapshot:
    """
    Immutable representation of the host environment state at a specific point in time.
    """
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    running_applications: List[Dict[str, Any]] = field(default_factory=list)
    active_window: Dict[str, Any] = field(default_factory=dict)
    window_hierarchy: List[Dict[str, Any]] = field(default_factory=list)
    monitor_layout: List[Dict[str, Any]] = field(default_factory=list)
    clipboard_state: Dict[str, Any] = field(default_factory=dict)
    connected_devices: List[Dict[str, Any]] = field(default_factory=list)
    network_status: Dict[str, Any] = field(default_factory=dict)
    battery_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the snapshot to a dictionary representation."""
        return asdict(self)
