from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IEmbeddingService(ABC):
    """
    Interface for generating text embeddings.
    Allows the Memory Engine to be completely model-agnostic.
    """

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates a dense vector representation of the given text.
        
        Args:
            text: The text to vectorize.
            
        Returns:
            A list of floats representing the embedding vector.
        """
        pass


class IMemoryEngine_v1(ICognitiveEngine):
    """
    Versioned public interface for the Layer 04 Memory Engine.
    Handles long-term persistence, retrieval, and consolidation of memories.
    """

    @abstractmethod
    async def store_episodic(self, content: str, metadata: Dict[str, Any], tags: List[str]) -> str:
        """
        Stores an episodic memory trace.
        
        Args:
            content: The text description of the event or interaction.
            metadata: Associated contextual metadata.
            tags: Descriptive tags.
            
        Returns:
            The unique UUID of the stored memory record.
        """
        pass

    @abstractmethod
    async def store_semantic(self, fact: str, entity: str, relationship: str, confidence: float) -> str:
        """
        Stores a semantic fact or rule.
        
        Args:
            fact: The text fact or rule.
            entity: The subject entity.
            relationship: The predicate or relationship type.
            confidence: A confidence score between 0.0 and 1.0.
            
        Returns:
            The unique UUID of the stored memory record.
        """
        pass

    @abstractmethod
    async def store_procedural(self, description: str, steps: List[Dict[str, Any]], success_rate: float) -> str:
        """
        Stores a procedural memory pattern.
        
        Args:
            description: Description of the procedure.
            steps: The list of actions/steps.
            success_rate: Observed success rate between 0.0 and 1.0.
            
        Returns:
            The unique UUID of the stored memory record.
        """
        pass

    @abstractmethod
    async def query(
        self, 
        query_text: str, 
        limit: int = 5, 
        memory_types: Optional[List[str]] = None, 
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Queries memories using hybrid search (lexical + vector).
        
        Args:
            query_text: The search query string.
            limit: Maximum number of memories to return.
            memory_types: Optional list of types to filter by ("episodic", "semantic", "procedural").
            min_relevance: Minimum relevance threshold between 0.0 and 1.0.
            
        Returns:
            A list of dictionary records matching the query.
        """
        pass

    @abstractmethod
    async def forget(self, memory_id: str) -> bool:
        """
        Deletes a specific memory record by ID.
        
        Args:
            memory_id: The UUID of the record to delete.
            
        Returns:
            True if deletion was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def consolidate(self) -> None:
        """
        Triggers background episodic memory consolidation.
        """
        pass
