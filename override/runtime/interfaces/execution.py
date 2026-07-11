from abc import ABC, abstractmethod
from typing import Any, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IExecutionEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 06 Execution Engine.
    Executes PlanSteps within an approved ExecutionPlan, orchestrating provider execution.
    """

    @abstractmethod
    async def execute_plan(self, plan: Any) -> Any:
        """
        Asynchronously executes the given approved ExecutionPlan by scheduling
        steps, invoking capability providers, handling retries, and returning
        the final ExecutionResult.

        Args:
            plan: The approved ExecutionPlan instance containing resolved steps.

        Returns:
            An ExecutionResult dataclass.
        """
        pass
