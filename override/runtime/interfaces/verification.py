from abc import ABC, abstractmethod
from typing import Any, Dict, List
from override.runtime.interfaces.engine import ICognitiveEngine

class IVerificationEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 07 Verification Engine.
    Subscribes to execution outcomes, evaluates verification rules, and reports results.
    """

    @abstractmethod
    async def verify_plan_outcome(self, execution_result: Any) -> Any:
        """
        Asynchronously verifies the outcome of an executed plan.
        
        Args:
            execution_result: The ExecutionResult from the Execution Engine.

        Returns:
            A VerificationReport containing the status, confidence, and any recovery suggestions.
        """
        pass
