from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IKnowledgeEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 08 Memory Consolidation & Knowledge Engine.
    Handles long-term persistence, learning, distillation, and retrieval of consolidated facts and workflows.
    """

    @abstractmethod
    async def store_workflow(
        self, 
        name: str, 
        steps: List[Dict[str, Any]], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Stores a reusable action sequence or workflow.
        
        Args:
            name: Human-readable identifier for the workflow.
            steps: The list of execution steps.
            metadata: Associated contextual metadata.
            
        Returns:
            The unique UUID of the stored workflow record.
        """
        pass

    @abstractmethod
    async def store_task_outcome(
        self, 
        plan_id: str, 
        correlation_id: str, 
        success: bool, 
        report: Dict[str, Any]
    ) -> str:
        """
        Stores a trace of a plan execution's outcome.
        
        Args:
            plan_id: The ID of the plan.
            correlation_id: The tracking context ID.
            success: Whether verification succeeded.
            report: The full verification report findings.
            
        Returns:
            The unique UUID of the stored task outcome record.
        """
        pass

    @abstractmethod
    async def store_semantic_knowledge(
        self, 
        topic: str, 
        content: str, 
        tags: List[str]
    ) -> str:
        """
        Stores long-term semantic knowledge, preferences, or configurations.
        
        Args:
            topic: General topic category.
            content: The semantic text content.
            tags: Descriptive classification tags.
            
        Returns:
            The unique UUID of the stored knowledge record.
        """
        pass

    @abstractmethod
    async def query_knowledge(
        self, 
        query_text: str, 
        limit: int = 5, 
        record_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries long-term consolidated memories using FTS5 lexical matching or vector similarity.
        
        Args:
            query_text: The search text query.
            limit: Maximum count of results.
            record_types: Optional filter by record types ('workflow', 'outcome', 'semantic', 'pattern').
            
        Returns:
            A list of dictionary records matching the query.
        """
        pass

    @abstractmethod
    async def forget_knowledge(self, record_id: str) -> bool:
        """
        Deletes a specific knowledge record by ID.
        
        Args:
            record_id: The UUID of the record to delete.
            
        Returns:
            True if deletion succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def compact_knowledge(self) -> None:
        """
        Triggers an offline compaction run to optimize schema indexing or compress logs.
        """
        pass
