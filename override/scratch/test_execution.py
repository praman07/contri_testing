"""
Integration and Unit test suite for Layer 06 — Execution Engine.
Verifies:
  1. DI Container resolution & boot ordering.
  2. Sequential execution of step dependencies.
  3. Concurrent execution of independent steps.
  4. Step-level retry policies under action failures.
  5. Timeout enforcements for slow actions.
  6. Plan cancellation via user intervention.
  7. Fail-fast verification when actions map to unregistered providers.
"""
import os
import sys
import asyncio
import logging
import datetime
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
from override.runtime.provider.manager import ProviderManager
from override.runtime.provider.provider import ExecutionProvider
from override.runtime.interfaces.execution import IExecutionEngine
from override.runtime.execution.engine import ExecutionEngine
from override.runtime.planner.models import ExecutionPlan, PlanStep

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Execution.Test")

class MockActionProvider(ExecutionProvider):
    """
    Mock capability provider to test successful executions, simulated failures,
    retries, and timeouts.
    """
    def __init__(self, provider_id: str, supported_actions: List[str]):
        super().__init__(provider_id, supported_actions)
        self.execution_counts: Dict[str, int] = {}
        self.last_params: Dict[str, Any] = {}

    def on_initialize(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    async def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.execution_counts[action_name] = self.execution_counts.get(action_name, 0) + 1
        self.last_params = params
        
        if action_name == "fail":
            raise RuntimeError("Simulated action failure")
        elif action_name == "slow":
            await asyncio.sleep(1.0)
            return {"status": "slow_done"}
        
        return {"status": "success", "action": action_name, "params": params}

async def main():
    logger.info("=== STARTING EXECUTION ENGINE INTEGRATION TEST ===")

    # ------------------------------------------------------------------
    # 1. Bootstrap and Registry Order Verification
    # ------------------------------------------------------------------
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)
    provider_manager: ProviderManager = container.resolve(ProviderManager)
    config: ConfigurationManager = container.resolve(ConfigurationManager)

    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Recorded Event: {event.topic}")

    event_bus.subscribe("execution.*", recorder)

    boot_order = registry.get_boot_order()
    logger.info(f"Initialization Order: {boot_order}")
    assert "execution_engine" in boot_order
    assert "planner_engine" in boot_order
    assert boot_order.index("planner_engine") < boot_order.index("execution_engine"), "planner must initialize before execution"
    logger.info("1. Boot order verification passed.")

    # Initialize all modules
    for mod_name in boot_order:
        registry.get_module(mod_name).on_initialize()

    execution_engine = container.resolve(IExecutionEngine)
    assert isinstance(execution_engine, ExecutionEngine)

    for mod_name in boot_order:
        registry.get_module(mod_name).on_start()
    
    await asyncio.sleep(0.1)

    # Register Mock Providers
    mock_browser = MockActionProvider("browser", ["click", "type", "slow"])
    mock_desktop = MockActionProvider("desktop", ["click", "wait", "fail"])
    provider_manager.register_provider(mock_browser)
    provider_manager.register_provider(mock_desktop)
    logger.info("Mock providers registered successfully.")

    # ------------------------------------------------------------------
    # 2. Sequential Plan Execution
    # ------------------------------------------------------------------
    logger.info("--- TEST 2: Sequential Execution ---")
    events_received.clear()
    
    plan = ExecutionPlan(
        plan_id="plan_seq_1",
        correlation_id="corr_seq_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_1", action="click", provider="browser", params={"element": "button"}, dependencies=[]),
            PlanStep(step_id="step_2", action="type", provider="browser", params={"text": "hello"}, dependencies=["step_1"]),
            PlanStep(step_id="step_3", action="wait", provider="desktop", params={"seconds": 1}, dependencies=["step_2"])
        ],
        required_providers=["browser", "desktop"],
        expected_outcomes=["success", "success", "success"]
    )

    result = await execution_engine.execute_plan(plan)
    assert result.status == "completed"
    assert len(result.completed_steps) == 3
    assert len(result.failed_steps) == 0
    
    # Confirm correct order of executions in log
    log_str = "\n".join(result.execution_log)
    assert log_str.index("step_1") < log_str.index("step_2")
    assert log_str.index("step_2") < log_str.index("step_3")

    # Verify event propagation
    await asyncio.sleep(0.1)
    started_evs = [e for e in events_received if e.topic == "execution.task_started" and e.payload.get("plan_id") == "plan_seq_1"]
    completed_evs = [e for e in events_received if e.topic == "execution.task_completed" and e.payload.get("plan_id") == "plan_seq_1"]
    action_evs = [e for e in events_received if e.topic == "execution.action_executed" and e.payload.get("plan_id") == "plan_seq_1"]

    assert len(started_evs) == 1
    assert len(completed_evs) == 1
    # 3 steps * 2 events each (running, completed) = 6 events
    assert len(action_evs) == 6
    logger.info("2. Sequential execution verification passed.")

    # ------------------------------------------------------------------
    # 3. Concurrent Execution
    # ------------------------------------------------------------------
    logger.info("--- TEST 3: Concurrent Execution ---")
    events_received.clear()

    # Steps 1 and 2 are independent, Step 3 depends on both
    plan_parallel = ExecutionPlan(
        plan_id="plan_par_1",
        correlation_id="corr_par_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_a", action="slow", provider="browser", params={}, dependencies=[]),
            PlanStep(step_id="step_b", action="click", provider="desktop", params={}, dependencies=[]),
            PlanStep(step_id="step_c", action="wait", provider="desktop", params={}, dependencies=["step_a", "step_b"])
        ],
        required_providers=["browser", "desktop"],
        expected_outcomes=["success", "success", "success"]
    )

    start_time = asyncio.get_event_loop().time()
    result_par = await execution_engine.execute_plan(plan_parallel)
    end_time = asyncio.get_event_loop().time()

    assert result_par.status == "completed"
    duration = end_time - start_time
    logger.info(f"Parallel plan completed in {duration:.2f}s")
    assert duration < 1.8, "Parallel execution seems serialized"
    logger.info("3. Concurrent plan execution verification passed.")

    # ------------------------------------------------------------------
    # 4. Step-level Retry Policies
    # ------------------------------------------------------------------
    logger.info("--- TEST 4: Retry Policies ---")
    events_received.clear()

    mock_desktop.execution_counts["fail"] = 0

    plan_retry = ExecutionPlan(
        plan_id="plan_retry_1",
        correlation_id="corr_retry_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_fail", action="fail", provider="desktop", params={}, dependencies=[])
        ],
        required_providers=["desktop"],
        expected_outcomes=["failure_handled"]
    )

    result_retry = await execution_engine.execute_plan(plan_retry)
    assert result_retry.status == "failed"
    attempts = mock_desktop.execution_counts["fail"]
    logger.info(f"Number of execution attempts for failing action: {attempts}")
    assert attempts == 4, f"Should run 4 attempts (1 initial + 3 retries), got {attempts}"
    logger.info("4. Step retries verification passed.")

    # ------------------------------------------------------------------
    # 5. Timeout Enforcements
    # ------------------------------------------------------------------
    logger.info("--- TEST 5: Timeout Enforcements ---")
    events_received.clear()

    from dataclasses import replace
    original_schema = config.schema

    # Update config timeout to 1.0s, retry_count = 1
    new_execution = replace(config.schema.execution, timeout_seconds=1.0, retry_count=1)
    config._schema = replace(config.schema, execution=new_execution)

    plan_timeout = ExecutionPlan(
        plan_id="plan_timeout_1",
        correlation_id="corr_timeout_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_slow", action="slow", provider="browser", params={}, dependencies=[])
        ],
        required_providers=["browser"],
        expected_outcomes=["timeout"]
    )

    # step_slow sleeps 1.0s, timeout is set to 0.1s. It should timeout!
    new_execution = replace(config.schema.execution, timeout_seconds=0.1, retry_count=1)
    config._schema = replace(config.schema, execution=new_execution)

    result_timeout = await execution_engine.execute_plan(plan_timeout)
    assert result_timeout.status == "failed"
    assert "timed out" in result_timeout.failed_steps[0]["error"]
    logger.info("5. Timeout enforcements verification passed.")

    # Restore original config values
    config._schema = original_schema

    # ------------------------------------------------------------------
    # 6. Cancellation Handling
    # ------------------------------------------------------------------
    logger.info("--- TEST 6: User Cancellation ---")
    events_received.clear()

    plan_cancel = ExecutionPlan(
        plan_id="plan_cancel_1",
        correlation_id="corr_cancel_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_cancel_slow", action="slow", provider="browser", params={}, dependencies=[])
        ],
        required_providers=["browser"],
        expected_outcomes=["cancelled"]
    )

    async def trigger_cancel_after_delay():
        await asyncio.sleep(0.2)
        logger.info("Publishing user cancellation event...")
        event_bus.publish(Event(
            _topic="ui.user_cancelled",
            _source="ui",
            _payload={"correlation_id": "corr_cancel_1"}
        ))

    exec_task = asyncio.create_task(execution_engine.execute_plan(plan_cancel))
    cancel_task = asyncio.create_task(trigger_cancel_after_delay())
    
    result_cancel = await exec_task
    await cancel_task

    assert result_cancel.status == "cancelled"
    await asyncio.sleep(0.1)
    
    failed_evs = [e for e in events_received if e.topic == "execution.task_failed" and e.payload.get("plan_id") == "plan_cancel_1"]
    assert len(failed_evs) == 1
    assert failed_evs[0].payload["error"] == "Execution cancelled by user"
    logger.info("6. User cancellation handling verification passed.")

    # ------------------------------------------------------------------
    # 7. Fail-Fast Unregistered Provider
    # ------------------------------------------------------------------
    logger.info("--- TEST 7: Fail-Fast Unregistered Provider ---")
    events_received.clear()

    plan_invalid = ExecutionPlan(
        plan_id="plan_invalid_1",
        correlation_id="corr_invalid_1",
        status="approved",
        steps=[
            PlanStep(step_id="step_bad", action="click", provider="unknown_provider", params={}, dependencies=[])
        ],
        required_providers=["unknown_provider"],
        expected_outcomes=["fail_fast"]
    )

    result_invalid = await execution_engine.execute_plan(plan_invalid)
    assert result_invalid.status == "failed"
    assert "unknown_provider" in result_invalid.metadata["failure_reason"]
    logger.info("7. Fail-fast unregistered provider verification passed.")

    # ------------------------------------------------------------------
    # Clean module tear-down
    # ------------------------------------------------------------------
    for mod_name in reversed(boot_order):
        registry.get_module(mod_name).on_stop()

    await asyncio.sleep(0.1)
    logger.info("=== ALL EXECUTION ENGINE TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(main())
