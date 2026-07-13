from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IGoalEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 10 Goal Engine.
    Tracks long-term user objectives, manages goal hierarchies, resolves conflicts,
    and publishes progress status and deviation warnings.
    """

    @abstractmethod
    async def create_goal(
        self,
        title: str,
        description: str,
        parent_goal_id: Optional[str] = None,
        priority: int = 3,
        target_date: Optional[str] = None,
        criteria: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new goal node in the hierarchy (defaults to DRAFT state).

        Args:
            title: Title of the goal.
            description: Description of the goal.
            parent_goal_id: Optional parent goal ID.
            priority: Priority scale from 1 (lowest) to 5 (highest).
            target_date: ISO target date string.
            criteria: Success criteria lists.
            tags: Conflict detection tags.

        Returns:
            The serialized GoalNode dictionary.
        """
        pass

    @abstractmethod
    async def update_goal_state(
        self,
        goal_id: str,
        state: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transitions the lifecycle state of a goal.

        Args:
            goal_id: UUID of the target goal.
            state: The new state (e.g. ACTIVE, PAUSED, COMPLETED).
            reason: Optional explanation of the transition.

        Returns:
            The updated serialized GoalNode dictionary.
        """
        pass

    @abstractmethod
    async def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a goal's detail map by ID.

        Args:
            goal_id: UUID of the target goal.

        Returns:
            The serialized GoalNode dictionary or None.
        """
        pass

    @abstractmethod
    async def get_goal_hierarchy(self) -> List[Dict[str, Any]]:
        """
        Returns the full tree representation of all goals.

        Returns:
            A list of serialized GoalNodes with their structural linkings.
        """
        pass

    @abstractmethod
    async def get_active_goals(self) -> List[Dict[str, Any]]:
        """
        Retrieves all goals currently in the ACTIVE state.

        Returns:
            A list of serialized ACTIVE GoalNodes.
        """
        pass

    @abstractmethod
    async def record_progress(
        self,
        goal_id: str,
        progress_percent: float,
        update_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records progress percentage update for a specific goal.

        Args:
            goal_id: UUID of the target goal.
            progress_percent: Percentage from 0.0 to 100.0.
            update_description: Optional detail text for the update.

        Returns:
            The updated serialized GoalNode dictionary.
        """
        pass
