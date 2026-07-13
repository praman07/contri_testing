from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid
import datetime

@dataclass(frozen=True)
class ActiveWindowContext:
    title: str = ""
    process_name: str = ""
    bounds: Dict[str, int] = field(default_factory=dict)
    is_minimized: bool = False

@dataclass(frozen=True)
class HostEnvironmentSummary:
    cpu_usage_percent: float = 0.0
    available_memory_mb: float = 0.0
    network_status: str = "connected"  # connected, disconnected
    power_source: str = "AC"           # battery, AC
    battery_percent: float = 100.0

@dataclass(frozen=True)
class TaskStateContext:
    active_plan_id: Optional[str] = None
    active_step_id: Optional[str] = None
    executor_status: str = "idle"      # idle, planning, executing, verifying

@dataclass(frozen=True)
class EntityNode:
    entity_id: str
    entity_type: str                   # e.g., "application", "file", "web_page", "user"
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EntityEdge:
    source_id: str
    target_id: str
    relationship_type: str             # e.g., "focuses", "modifies", "contains"
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class WorldState:
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    active_window: ActiveWindowContext = field(default_factory=ActiveWindowContext)
    running_applications: List[Dict[str, Any]] = field(default_factory=list)
    clipboard_summary: Optional[str] = None
    host_environment: HostEnvironmentSummary = field(default_factory=HostEnvironmentSummary)
    task_state: TaskStateContext = field(default_factory=TaskStateContext)
    perceived_user_activity: str = "active"  # active, idle, system_executing
    detected_anomalies: List[str] = field(default_factory=list)
    entities: List[EntityNode] = field(default_factory=list)
    relationships: List[EntityEdge] = field(default_factory=list)
