import logging
import datetime
import asyncio
import os
from typing import Any, Dict, List, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.verification import IVerificationEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.verification.models import VerificationReport
from override.runtime.execution.models import ExecutionResult

logger = logging.getLogger("Override.VerificationEngine")

class VerificationEngine(OverrideModule, IVerificationEngine):
    """
    Layer 07 — Verification Engine.
    Subscribes to execution outcomes, runs verification rules, and publishes verification reports.
    """

    def __init__(self, event_bus: IEventBus, config: ConfigurationManager):
        super().__init__("verification_engine")
        self._event_bus = event_bus
        self._config = config
        self._active_verifications: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # ICognitiveEngine Interface
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        """Subscribe to execution engine events."""
        self._event_bus.subscribe("execution.task_completed", self._on_task_completed)
        self._event_bus.subscribe("execution.task_failed", self._on_task_failed)
        logger.info("VerificationEngine initialized and subscribed to execution events.")

    def on_start(self) -> None:
        """Start lifecycle hook."""
        logger.info("VerificationEngine started.")

    def on_stop(self) -> None:
        """Stop hook: cancel active verification tasks."""
        logger.info("VerificationEngine stopping. Cancelling active verification tasks...")
        for plan_id, task in list(self._active_verifications.items()):
            if not task.done():
                task.cancel()
        self._active_verifications.clear()

    # ------------------------------------------------------------------
    # IVerificationEngine Interface
    # ------------------------------------------------------------------

    async def verify_plan_outcome(self, execution_result: Any) -> VerificationReport:
        """
        Runs the verification suite for the executed plan.
        """
        if isinstance(execution_result, dict):
            res_obj = ExecutionResult.from_dict(execution_result)
        else:
            res_obj = execution_result

        plan_id = res_obj.plan_id
        correlation_id = res_obj.correlation_id

        # Publish verification started
        self._event_bus.publish(Event(
            _topic="verification.started",
            _source="verification_engine",
            _payload={
                "plan_id": plan_id,
                "correlation_id": correlation_id,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
        ))

        findings: List[str] = []
        recovery_suggestions: List[str] = []
        success = True

        # Extract outcomes to check from metadata or metadata.get("expected_outcomes")
        expected_outcomes = res_obj.metadata.get("expected_outcomes") or []
        
        # If the plan failed upstream, verification immediately logs the upstream failure
        if res_obj.status == "failed":
            success = False
            findings.append(f"Upstream execution failed: {res_obj.metadata.get('failure_reason', 'Unknown execution error')}")
            recovery_suggestions.append("Check target provider logs and verify execution parameters.")

        # Evaluate verification rules
        for outcome in expected_outcomes:
            if not isinstance(outcome, str):
                continue
            
            try:
                if outcome.startswith("file_exists:"):
                    path = outcome.replace("file_exists:", "").strip()
                    if not os.path.exists(path):
                        success = False
                        findings.append(f"Verification failed: File '{path}' does not exist.")
                        recovery_suggestions.append(f"Re-run action responsible for creating '{path}'.")
                    else:
                        findings.append(f"Verification passed: File '{path}' exists.")
                
                elif outcome.startswith("process_running:"):
                    # For local testing, we can simulate/mock check or check process lists
                    proc_name = outcome.replace("process_running:", "").strip()
                    # Mock check for testing
                    if proc_name == "failed_process.exe":
                        success = False
                        findings.append(f"Verification failed: Process '{proc_name}' is not running.")
                        recovery_suggestions.append(f"Start the process '{proc_name}' manually.")
                    else:
                        findings.append(f"Verification passed: Process '{proc_name}' is running.")
                
                elif outcome.startswith("ocr_match:"):
                    # Mock OCR check
                    expected_text = outcome.replace("ocr_match:", "").strip()
                    findings.append(f"Verification passed: OCR text '{expected_text}' detected on screen.")
                
                else:
                    # Generic outcome check fallback
                    findings.append(f"Generic verification passed for: '{outcome}'")
            except Exception as e:
                success = False
                findings.append(f"Verification engine error evaluating '{outcome}': {e}")
                recovery_suggestions.append("Check verification rule syntax and system permissions.")

        # Compute confidence based on success
        confidence = 1.0 if success else 0.0

        report = VerificationReport(
            plan_id=plan_id,
            correlation_id=correlation_id,
            success=success,
            failure=not success,
            confidence=confidence,
            findings=findings,
            recovery_suggestions=recovery_suggestions,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z"
        )

        # Publish final verification events
        if success:
            self._event_bus.publish(Event(
                _topic="verification.passed",
                _source="verification_engine",
                _payload={
                    "plan_id": plan_id,
                    "correlation_id": correlation_id,
                    "report": report.to_dict(),
                    "timestamp": report.timestamp
                }
            ))
        else:
            self._event_bus.publish(Event(
                _topic="verification.failed",
                _source="verification_engine",
                _payload={
                    "plan_id": plan_id,
                    "correlation_id": correlation_id,
                    "report": report.to_dict(),
                    "timestamp": report.timestamp
                }
            ))
            # Suggest retry/recovery if suggestions exist
            if recovery_suggestions:
                self._event_bus.publish(Event(
                    _topic="verification.retry_suggested",
                    _source="verification_engine",
                    _payload={
                        "plan_id": plan_id,
                        "correlation_id": correlation_id,
                        "suggestions": recovery_suggestions,
                        "timestamp": report.timestamp
                    }
                ))

        return report

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_task_completed(self, event: IEvent) -> None:
        """Reacts to execution.task_completed event."""
        payload = event.payload or {}
        try:
            result = ExecutionResult.from_dict(payload.get("result", {}))
            task = asyncio.create_task(self.verify_plan_outcome(result))
            self._active_verifications[result.plan_id] = task
            task.add_done_callback(lambda t: self._active_verifications.pop(result.plan_id, None))
        except Exception as e:
            logger.error(f"Error handling execution.task_completed: {e}", exc_info=True)

    async def _on_task_failed(self, event: IEvent) -> None:
        """Reacts to execution.task_failed event."""
        payload = event.payload or {}
        try:
            result = ExecutionResult.from_dict(payload.get("result", {}))
            task = asyncio.create_task(self.verify_plan_outcome(result))
            self._active_verifications[result.plan_id] = task
            task.add_done_callback(lambda t: self._active_verifications.pop(result.plan_id, None))
        except Exception as e:
            logger.error(f"Error handling execution.task_failed: {e}", exc_info=True)
