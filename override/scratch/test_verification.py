"""
Integration and Unit test suite for Layer 07 — Verification Engine.
Verifies:
  1. DI Container resolution & boot ordering.
  2. Completion-triggered verification loops.
  3. Deterministic file verification rule passes and failures.
  4. Process verification rule checks.
  5. Recovery suggestions on rule failures.
  6. Upstream task failure reporting.
"""
import os
import sys
import asyncio
import logging
import datetime
import tempfile
from typing import List, Dict, Any

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.interfaces.verification import IVerificationEngine
from override.runtime.verification.models import VerificationReport
from override.runtime.execution.models import ExecutionResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Verification.Test")

async def main():
    logger.info("=== STARTING VERIFICATION ENGINE INTEGRATION TEST ===")

    # 1. Bootstrap and Registry Order Verification
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)
    config: ConfigurationManager = container.resolve(ConfigurationManager)

    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Recorded Event: {event.topic}")

    event_bus.subscribe("verification.*", recorder)

    boot_order = registry.get_boot_order()
    logger.info(f"Initialization Order: {boot_order}")
    assert "verification_engine" in boot_order
    assert boot_order.index("execution_engine") < boot_order.index("verification_engine"), "execution must initialize before verification"
    logger.info("1. Boot order verification passed.")

    # Initialize and start all modules in order
    for mod_name in boot_order:
        mod = registry.get_module(mod_name)
        mod.initialize()
        mod.start()
    logger.info("All modules initialized and started.")

    verification_engine: IVerificationEngine = container.resolve(IVerificationEngine)

    try:
        # Create a temp file to test file_exists verification
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_file_path = tmp.name

        # ------------------------------------------------------------------
        # Test 2: Successful verification (File Exists)
        # ------------------------------------------------------------------
        logger.info("\n--- Test 2: Successful Verification (File Exists) ---")
        events_received.clear()

        # Build an execution result that was successful and specifies the file exists
        exec_res = ExecutionResult(
            plan_id="plan-1",
            correlation_id="corr-1",
            status="completed",
            completed_steps=[],
            failed_steps=[],
            execution_log=["Step 1 completed"],
            execution_timing={"duration": 1.5},
            metadata={"expected_outcomes": [f"file_exists:{temp_file_path}", "process_running:notepad.exe"]}
        )

        # Publish the event to simulate execution completion
        event_bus.publish(Event(
            _topic="execution.task_completed",
            _source="test_execution_mock",
            _payload={"result": exec_res.to_dict()}
        ))

        # Give it a brief moment to process
        await asyncio.sleep(0.5)

        topics = [e.topic for e in events_received]
        assert "verification.started" in topics
        assert "verification.passed" in topics
        assert "verification.failed" not in topics
        
        # Verify report payload
        passed_event = next(e for e in events_received if e.topic == "verification.passed")
        report = VerificationReport.from_dict(passed_event.payload["report"])
        assert report.success is True
        assert report.confidence == 1.0
        logger.info("Test 2 Passed: Verification report verified successfully.")

        # ------------------------------------------------------------------
        # Test 3: Failed verification (File Missing)
        # ------------------------------------------------------------------
        logger.info("\n--- Test 3: Failed Verification (File Missing) ---")
        events_received.clear()

        # Remove the temp file to trigger a validation failure
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Publish task completed, but the file is now missing
        event_bus.publish(Event(
            _topic="execution.task_completed",
            _source="test_execution_mock",
            _payload={"result": exec_res.to_dict()}
        ))

        await asyncio.sleep(0.5)

        topics = [e.topic for e in events_received]
        assert "verification.started" in topics
        assert "verification.failed" in topics
        assert "verification.retry_suggested" in topics
        
        failed_event = next(e for e in events_received if e.topic == "verification.failed")
        report = VerificationReport.from_dict(failed_event.payload["report"])
        assert report.success is False
        assert report.confidence == 0.0
        assert len(report.findings) > 0
        assert any("does not exist" in f for f in report.findings)
        assert len(report.recovery_suggestions) > 0
        logger.info("Test 3 Passed: Missing file verification failure detected.")

        # ------------------------------------------------------------------
        # Test 4: Failed process rule
        # ------------------------------------------------------------------
        logger.info("\n--- Test 4: Failed Process Rule ---")
        events_received.clear()

        # Build execution result expecting a failed process
        exec_res_proc = ExecutionResult(
            plan_id="plan-2",
            correlation_id="corr-2",
            status="completed",
            metadata={"expected_outcomes": ["process_running:failed_process.exe"]}
        )

        event_bus.publish(Event(
            _topic="execution.task_completed",
            _source="test_execution_mock",
            _payload={"result": exec_res_proc.to_dict()}
        ))

        await asyncio.sleep(0.5)

        topics = [e.topic for e in events_received]
        assert "verification.failed" in topics
        assert "verification.retry_suggested" in topics
        logger.info("Test 4 Passed: Failed process verification detected.")

        # ------------------------------------------------------------------
        # Test 5: Upstream task failure reporting
        # ------------------------------------------------------------------
        logger.info("\n--- Test 5: Upstream Task Failure ---")
        events_received.clear()

        # Build an execution result that failed upstream
        exec_res_fail = ExecutionResult(
            plan_id="plan-3",
            correlation_id="corr-3",
            status="failed",
            metadata={"failure_reason": "Injected upstream failure"}
        )

        event_bus.publish(Event(
            _topic="execution.task_failed",
            _source="test_execution_mock",
            _payload={"result": exec_res_fail.to_dict()}
        ))

        await asyncio.sleep(0.5)

        topics = [e.topic for e in events_received]
        assert "verification.failed" in topics
        failed_event = next(e for e in events_received if e.topic == "verification.failed")
        report = VerificationReport.from_dict(failed_event.payload["report"])
        assert report.success is False
        assert any("Upstream execution failed" in f for f in report.findings)
        logger.info("Test 5 Passed: Upstream task failure processed correctly.")

    finally:
        # Cleanup
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Stop all modules in reverse order
        for mod_name in reversed(boot_order):
            registry.get_module(mod_name).stop()

    logger.info("=== ALL VERIFICATION ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(main())
