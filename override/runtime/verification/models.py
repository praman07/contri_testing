import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class VerificationReport:
    """
    Structured outcome of Layer 07 Verification Engine.
    Represents whether the executed plan achieved its desired goals.
    """
    plan_id: str
    correlation_id: str
    success: bool
    failure: bool
    confidence: float
    findings: List[str] = field(default_factory=list)
    recovery_suggestions: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationReport":
        return cls(
            plan_id=data["plan_id"],
            correlation_id=data["correlation_id"],
            success=data["success"],
            failure=data["failure"],
            confidence=data["confidence"],
            findings=data.get("findings", []),
            recovery_suggestions=data.get("recovery_suggestions", []),
            timestamp=data.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z"),
            metadata=data.get("metadata", {})
        )
