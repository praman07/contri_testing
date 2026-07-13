import json
import uuid
import datetime
from typing import Dict, Any, List, Optional

class WorkflowRecord:
    """Represents a reusable execution workflow."""
    def __init__(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        workflow_id: Optional[str] = None,
        frequency: int = 1,
        timestamp: Optional[str] = None,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.name = name
        self.steps = steps
        self.frequency = frequency
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        self.vector = vector
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "steps": self.steps,
            "frequency": self.frequency,
            "timestamp": self.timestamp,
            "vector": self.vector,
            "metadata": self.metadata,
            "record_type": "workflow"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowRecord":
        steps = data.get("steps")
        if isinstance(steps, str):
            steps = json.loads(steps)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        vector = data.get("vector")
        if isinstance(vector, str):
            vector = json.loads(vector)
            
        return cls(
            name=data["name"],
            steps=steps or [],
            workflow_id=data.get("workflow_id"),
            frequency=data.get("frequency", 1),
            timestamp=data.get("timestamp"),
            vector=vector,
            metadata=metadata
        )


class TaskOutcomeRecord:
    """Represents the outcome trace of a completed task/plan."""
    def __init__(
        self,
        plan_id: str,
        correlation_id: str,
        success: bool,
        report: Dict[str, Any],
        outcome_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.outcome_id = outcome_id or str(uuid.uuid4())
        self.plan_id = plan_id
        self.correlation_id = correlation_id
        self.success = success
        self.report = report
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        self.vector = vector
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "plan_id": self.plan_id,
            "correlation_id": self.correlation_id,
            "success": self.success,
            "report": self.report,
            "timestamp": self.timestamp,
            "vector": self.vector,
            "metadata": self.metadata,
            "record_type": "outcome"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskOutcomeRecord":
        report = data.get("report")
        if isinstance(report, str):
            report = json.loads(report)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        vector = data.get("vector")
        if isinstance(vector, str):
            vector = json.loads(vector)

        return cls(
            plan_id=data["plan_id"],
            correlation_id=data["correlation_id"],
            success=bool(data["success"]),
            report=report or {},
            outcome_id=data.get("outcome_id"),
            timestamp=data.get("timestamp"),
            vector=vector,
            metadata=metadata
        )


class SemanticKnowledgeRecord:
    """Represents general semantic facts, rules, or preferences."""
    def __init__(
        self,
        topic: str,
        content: str,
        tags: List[str],
        knowledge_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.knowledge_id = knowledge_id or str(uuid.uuid4())
        self.topic = topic
        self.content = content
        self.tags = tags
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        self.vector = vector
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "topic": self.topic,
            "content": self.content,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "vector": self.vector,
            "metadata": self.metadata,
            "record_type": "semantic"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticKnowledgeRecord":
        tags = data.get("tags")
        if isinstance(tags, str):
            tags = json.loads(tags)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        vector = data.get("vector")
        if isinstance(vector, str):
            vector = json.loads(vector)

        return cls(
            topic=data["topic"],
            content=data["content"],
            tags=tags or [],
            knowledge_id=data.get("knowledge_id"),
            timestamp=data.get("timestamp"),
            vector=vector,
            metadata=metadata
        )


class PatternRecord:
    """Represents learned system heuristics or patterns."""
    def __init__(
        self,
        key: str,
        value: Dict[str, Any],
        pattern_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.pattern_id = pattern_id or str(uuid.uuid4())
        self.key = key
        self.value = value
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        self.vector = vector
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "vector": self.vector,
            "metadata": self.metadata,
            "record_type": "pattern"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternRecord":
        value = data.get("value")
        if isinstance(value, str):
            value = json.loads(value)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        vector = data.get("vector")
        if isinstance(vector, str):
            vector = json.loads(vector)

        return cls(
            key=data["key"],
            value=value or {},
            pattern_id=data.get("pattern_id"),
            timestamp=data.get("timestamp"),
            vector=vector,
            metadata=metadata
        )
