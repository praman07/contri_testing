import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class ExecutionResult:
    """
    Structured outcome of the execution of an entire ExecutionPlan.
    Produced by the Execution Engine (Layer 06).
    """
    plan_id: str
    correlation_id: str
    status: str  # completed | failed | cancelled
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = field(default_factory=list)
    execution_log: List[str] = field(default_factory=list)
    execution_timing: Dict[str, float] = field(default_factory=dict)  # start_time, end_time, duration
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionResult":
        return cls(
            plan_id=data["plan_id"],
            correlation_id=data["correlation_id"],
            status=data["status"],
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            execution_log=data.get("execution_log", []),
            execution_timing=data.get("execution_timing", {}),
            metadata=data.get("metadata", {})
        )
