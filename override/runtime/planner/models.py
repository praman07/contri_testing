import datetime
import uuid
from dataclasses import dataclass, field, replace, asdict
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class PlanStep:
    """
    Individual atomic action within an ExecutionPlan.
    Decomposed from reasoning suggested actions.
    """
    step_id: str
    action: str
    provider: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    status: str = "pending"  # pending | running | completed | failed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        return cls(
            step_id=data["step_id"],
            action=data["action"],
            provider=data["provider"],
            params=data.get("params", {}),
            dependencies=data.get("dependencies", []),
            expected_outcome=data.get("expected_outcome", ""),
            status=data.get("status", "pending")
        )


@dataclass(frozen=True)
class ExecutionPlan:
    """
    Structured execution plan consisting of ordered, dependency-resolved steps.
    Produced by the Planner Engine (Layer 05).
    """
    plan_id: str
    correlation_id: str
    steps: List[PlanStep]
    required_providers: List[str]
    expected_outcomes: List[str]
    status: str = "created"  # created | approved | rejected | running | completed | failed
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "correlation_id": self.correlation_id,
            "steps": [step.to_dict() for step in self.steps],
            "required_providers": self.required_providers,
            "expected_outcomes": self.expected_outcomes,
            "status": self.status,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        return cls(
            plan_id=data["plan_id"],
            correlation_id=data["correlation_id"],
            steps=[PlanStep.from_dict(s) for s in data["steps"]],
            required_providers=data.get("required_providers", []),
            expected_outcomes=data.get("expected_outcomes", []),
            status=data.get("status", "created"),
            timestamp=data.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z"),
            metadata=data.get("metadata", {})
        )

    def copy_with(self, **kwargs: Any) -> "ExecutionPlan":
        """Returns a new copy of the ExecutionPlan with replaced properties."""
        return replace(self, **kwargs)

# Import cross-layer stubs from placeholders.
# The Planner Engine does not own these models; they are imported here
# as temporary placeholder imports until their respective owning engines
# are fully implemented.
from override.runtime.interfaces.placeholders import (
    ReasoningResult,
    ContextSnapshot,
    UserGoal
)
