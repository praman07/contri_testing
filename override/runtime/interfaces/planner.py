from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IPlannerEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 05 Planner Engine.
    Decomposes goals and reasoning results into deterministic ExecutionPlans.
    """

    @abstractmethod
    def generate_plan(
        self,
        reasoning_result: Any,
        context_snapshot: Any,
        goal: Optional[Any] = None,
        correlation_id: Optional[str] = None
    ) -> Any:
        """
        Generates a structured, validated ExecutionPlan based on reasoning,
        context state, and optionally a user goal.

        Args:
            reasoning_result: ReasoningResult containing suggested actions/decisions.
            context_snapshot: ContextSnapshot containing current system/world state.
            goal: Optional UserGoal object.
            correlation_id: Optional UUID mapping this plan to a broader task flow.

        Returns:
            An ExecutionPlan instance containing ordered, dependency-resolved steps.
        """
        pass
