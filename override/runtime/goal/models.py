from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

# Valid states in the Goal Lifecycle State Machine
VALID_GOAL_STATES = {
    "DRAFT",
    "ACTIVE",
    "PAUSED",
    "BLOCKED",
    "COMPLETED",
    "ABANDONED"
}

@dataclass
class GoalNode:
    """Represents a single node in the Goal Hierarchy Tree."""
    goal_id: str
    title: str
    description: str
    parent_goal_id: Optional[str] = None
    priority: int = 3  # Scale from 1 (Lowest) to 5 (Highest)
    state: str = "DRAFT"  # DRAFT, ACTIVE, PAUSED, BLOCKED, COMPLETED, ABANDONED
    progress_percent: float = 0.0  # Range: 0.0 - 100.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    target_date: Optional[datetime] = None
    blockers: List[str] = field(default_factory=list)
    criteria: List[str] = field(default_factory=list)  # Set of success conditions
    tags: List[str] = field(default_factory=list)  # Conflict tagging (e.g. "requires_focus")

    def to_dict(self) -> dict:
        """Serializes the goal node to a standard dictionary."""
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "parent_goal_id": self.parent_goal_id,
            "priority": self.priority,
            "state": self.state,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "blockers": list(self.blockers),
            "criteria": list(self.criteria),
            "tags": list(self.tags)
        }
