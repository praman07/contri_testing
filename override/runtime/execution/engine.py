"""
Layer 06 — Execution Engine

Responsible for executing approved plans, scheduling steps concurrently,
resolving execution providers, handling retries, timeouts, and cancellations.
"""
import logging
import threading
import datetime
import asyncio
from typing import Dict, Any, List, Optional, Set

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.execution import IExecutionEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.provider.manager import ProviderManager
from override.runtime.planner.models import ExecutionPlan, PlanStep
from override.runtime.execution.models import ExecutionResult

logger = logging.getLogger("Override.ExecutionEngine")

class ExecutionEngine(OverrideModule, IExecutionEngine):
    """
    Layer 06 — Execution Engine.
    Coordinates execution of approved plans by routing actions to registered providers,
    managing retries/timeouts, and handling step concurrency and plan cancellations.
    """

    def __init__(self, event_bus: IEventBus, provider_manager: ProviderManager, config: ConfigurationManager):
        super().__init__("execution_engine")
        self._event_bus = event_bus
        self._provider_manager = provider_manager
        self._config = config

        self._lock = threading.RLock()
        self._active_plan_tasks: Dict[str, asyncio.Task] = {}
        self._plan_correlations: Dict[str, str] = {}
        self._cancelled_correlation_ids: Set[str] = set()

    # ------------------------------------------------------------------
    # ICognitiveEngine Interface
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        """Subscribe to planning and UI control events."""
        self._event_bus.subscribe("planning.plan_approved", self._on_plan_approved)
        self._event_bus.subscribe("ui.user_cancelled", self._on_user_cancelled)
        logger.info("ExecutionEngine initialized and subscribed to events.")

    def on_start(self) -> None:
        """Start lifecycle hook."""
        logger.info("ExecutionEngine started.")

    def on_stop(self) -> None:
        """Gracefully stop and cancel all active execution tasks."""
        logger.info("ExecutionEngine stopping. Cancelling all active plan tasks...")
        with self._lock:
            for plan_id, task in list(self._active_plan_tasks.items()):
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled plan execution task: {plan_id}")
            self._active_plan_tasks.clear()
            self._plan_correlations.clear()
            self._cancelled_correlation_ids.clear()

    # ------------------------------------------------------------------
    # IExecutionEngine Interface
    # ------------------------------------------------------------------

    async def execute_plan(self, plan: Any) -> ExecutionResult:
        """
        Asynchronously executes the given approved ExecutionPlan by scheduling
        steps, invoking capability providers, handling retries, and returning
        the final ExecutionResult.
        """
        if isinstance(plan, dict):
            plan_obj = ExecutionPlan.from_dict(plan)
        else:
            plan_obj = plan

        # 1. Basic status validation
        if plan_obj.status != "approved":
            raise ValueError(f"Cannot execute plan '{plan_obj.plan_id}' with status '{plan_obj.status}'. Only 'approved' plans can be executed.")

        # 2. Register active task for lifecycle/cancellation coordination
        with self._lock:
            current_task = asyncio.current_task()
            if current_task:
                self._active_plan_tasks[plan_obj.plan_id] = current_task
            self._plan_correlations[plan_obj.plan_id] = plan_obj.correlation_id

        # 3. Setup tracking data structures
        in_degree = {step.step_id: 0 for step in plan_obj.steps}
        adj: Dict[str, List[str]] = {step.step_id: [] for step in plan_obj.steps}
        step_map = {step.step_id: step for step in plan_obj.steps}

        for step in plan_obj.steps:
            for dep in step.dependencies:
                if dep in adj:
                    adj[dep].append(step.step_id)
                    in_degree[step.step_id] += 1

        completed_step_results: List[Dict[str, Any]] = []
        failed_step_results: List[Dict[str, Any]] = []
        execution_log: List[str] = []

        # ------------------------------------------------------------------
        # Helper step executor
        # ------------------------------------------------------------------
        async def execute_step(step: PlanStep) -> str:
            start_msg = f"Started step '{step.step_id}': action='{step.action}' using provider='{step.provider}'"
            execution_log.append(start_msg)
            logger.info(start_msg)

            # Emit ActionExecuted (running)
            self._event_bus.publish(Event(
                _topic="execution.action_executed",
                _source="execution_engine",
                _payload={
                    "plan_id": plan_obj.plan_id,
                    "correlation_id": plan_obj.correlation_id,
                    "step_id": step.step_id,
                    "action": step.action,
                    "provider": step.provider,
                    "status": "running",
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
            ))

            retries_remaining = getattr(self._config, "execution", None)
            if retries_remaining:
                retries_limit = self._config.execution.retry_count
                timeout = self._config.execution.timeout_seconds
            else:
                retries_limit = 3
                timeout = 30

            outcome = None
            last_error = None
            retries_run = 0

            while retries_run <= retries_limit:
                try:
                    outcome = await asyncio.wait_for(
                        self._provider_manager.execute(step.action, step.params),
                        timeout=timeout
                    )
                    last_error = None
                    break
                except asyncio.TimeoutError:
                    last_error = f"Step timed out after {timeout}s"
                    logger.warning(f"Step '{step.step_id}' timed out. Retries run: {retries_run}/{retries_limit}")
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Step '{step.step_id}' execution failed: {e}. Retries run: {retries_run}/{retries_limit}")

                retries_run += 1
                if retries_run <= retries_limit:
                    await asyncio.sleep(0.5)

            if last_error:
                fail_msg = f"Failed step '{step.step_id}': {last_error}"
                execution_log.append(fail_msg)
                logger.error(fail_msg)

                result_detail = {
                    "step_id": step.step_id,
                    "action": step.action,
                    "provider": step.provider,
                    "error": last_error,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
                failed_step_results.append(result_detail)

                # Emit ActionExecuted (failed)
                self._event_bus.publish(Event(
                    _topic="execution.action_executed",
                    _source="execution_engine",
                    _payload={
                        "plan_id": plan_obj.plan_id,
                        "correlation_id": plan_obj.correlation_id,
                        "step_id": step.step_id,
                        "action": step.action,
                        "provider": step.provider,
                        "status": "failed",
                        "error": last_error,
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                    }
                ))
                raise ValueError(last_error)
            else:
                success_msg = f"Completed step '{step.step_id}': outcome={outcome}"
                execution_log.append(success_msg)
                logger.info(success_msg)

                result_detail = {
                    "step_id": step.step_id,
                    "action": step.action,
                    "provider": step.provider,
                    "outcome": outcome,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
                completed_step_results.append(result_detail)

                # Emit ActionExecuted (completed)
                self._event_bus.publish(Event(
                    _topic="execution.action_executed",
                    _source="execution_engine",
                    _payload={
                        "plan_id": plan_obj.plan_id,
                        "correlation_id": plan_obj.correlation_id,
                        "step_id": step.step_id,
                        "action": step.action,
                        "provider": step.provider,
                        "status": "completed",
                        "outcome": outcome,
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                    }
                ))
                return step.step_id

        # ------------------------------------------------------------------
        # Dynamic topological scheduler
        # ------------------------------------------------------------------
        allow_parallel = getattr(self._config.planner, "allow_parallel_execution", True)
        execution_config = getattr(self._config, "execution", None)
        concurrent_limit = execution_config.concurrent_steps_limit if (execution_config and allow_parallel) else (4 if allow_parallel else 1)

        pending_step_ids = set(in_degree.keys())
        active_step_tasks: Dict[str, asyncio.Task] = {}
        plan_failed = False
        failure_reason = None
        start_time = datetime.datetime.utcnow()

        # Emit task started event
        self._event_bus.publish(Event(
            _topic="execution.task_started",
            _source="execution_engine",
            _payload={
                "plan_id": plan_obj.plan_id,
                "correlation_id": plan_obj.correlation_id,
                "timestamp": start_time.isoformat() + "Z"
            }
        ))

        try:
            while pending_step_ids or active_step_tasks:
                # 1. Check for cancellation
                if self._check_cancelled(plan_obj.correlation_id):
                    plan_failed = True
                    failure_reason = "Execution cancelled by user"
                    break

                # 2. Queue eligible steps
                if not plan_failed:
                    eligible_step_ids = [
                        sid for sid in pending_step_ids
                        if in_degree[sid] == 0 and sid not in active_step_tasks
                    ]
                    # Stabilize order
                    eligible_step_ids.sort()

                    for sid in eligible_step_ids:
                        if len(active_step_tasks) >= concurrent_limit:
                            break
                        step = step_map[sid]
                        
                        # Verify provider registry has it
                        if not self._provider_manager.get_provider(step.provider):
                            plan_failed = True
                            failure_reason = f"Provider '{step.provider}' not available for step '{sid}'"
                            break

                        task = asyncio.create_task(execute_step(step))
                        active_step_tasks[sid] = task
                        pending_step_ids.remove(sid)

                if plan_failed:
                    break

                if not active_step_tasks:
                    if pending_step_ids:
                        plan_failed = True
                        failure_reason = "Deadlock/unresolved dependency loop detected in execution queue"
                        break
                    else:
                        break

                # Wait for any active step to complete
                done, _ = await asyncio.wait(
                    active_step_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )

                completed_this_turn = []
                for task in done:
                    # Resolve step ID
                    step_id = next(sid for sid, t in active_step_tasks.items() if t == task)
                    completed_this_turn.append(step_id)

                    try:
                        await task
                        # Release dependents
                        for neighbor in adj[step_id]:
                            in_degree[neighbor] -= 1
                    except Exception as e:
                        plan_failed = True
                        failure_reason = str(e)

                for sid in completed_this_turn:
                    del active_step_tasks[sid]

        except asyncio.CancelledError:
            plan_failed = True
            if self._check_cancelled(plan_obj.correlation_id):
                failure_reason = "Execution cancelled by user"
            else:
                failure_reason = "Execution task cancelled"
        finally:
            # Clean up active tasks if plan failed/cancelled
            for task in active_step_tasks.values():
                if not task.done():
                    task.cancel()
            if active_step_tasks:
                await asyncio.gather(*active_step_tasks.values(), return_exceptions=True)

            with self._lock:
                self._active_plan_tasks.pop(plan_obj.plan_id, None)
                self._plan_correlations.pop(plan_obj.plan_id, None)
                self._cancelled_correlation_ids.discard(plan_obj.correlation_id)

        # 4. Result generation
        end_time = datetime.datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        status = "failed" if plan_failed else "completed"
        if failure_reason == "Execution cancelled by user":
            status = "cancelled"

        execution_timing = {
            "start_time": start_time.timestamp(),
            "end_time": end_time.timestamp(),
            "duration": duration
        }

        result = ExecutionResult(
            plan_id=plan_obj.plan_id,
            correlation_id=plan_obj.correlation_id,
            status=status,
            completed_steps=completed_step_results,
            failed_steps=failed_step_results,
            execution_log=execution_log,
            execution_timing=execution_timing,
            metadata={"failure_reason": failure_reason} if failure_reason else {}
        )

        # Emit final event
        if status == "completed":
            self._event_bus.publish(Event(
                _topic="execution.task_completed",
                _source="execution_engine",
                _payload={
                    "plan_id": plan_obj.plan_id,
                    "correlation_id": plan_obj.correlation_id,
                    "result": result.to_dict(),
                    "timestamp": end_time.isoformat() + "Z"
                }
            ))
        else:
            self._event_bus.publish(Event(
                _topic="execution.task_failed",
                _source="execution_engine",
                _payload={
                    "plan_id": plan_obj.plan_id,
                    "correlation_id": plan_obj.correlation_id,
                    "error": failure_reason or "Unknown execution error",
                    "result": result.to_dict(),
                    "timestamp": end_time.isoformat() + "Z"
                }
            ))

        return result

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_plan_approved(self, event: IEvent) -> None:
        """Reacts to user approved execution plans by kicking off execution task."""
        payload = event.payload or {}
        try:
            plan = ExecutionPlan.from_dict(payload)
            # Schedule execution asynchronously
            asyncio.create_task(self.execute_plan(plan))
        except Exception as e:
            logger.error(f"Error handling planning.plan_approved event: {e}", exc_info=True)

    async def _on_user_cancelled(self, event: IEvent) -> None:
        """Reacts to user cancellation events and aborts active tasks."""
        payload = event.payload or {}
        correlation_id = payload.get("correlation_id")
        if not correlation_id:
            return

        with self._lock:
            self._cancelled_correlation_ids.add(correlation_id)
            for plan_id, task in list(self._active_plan_tasks.items()):
                if self._plan_correlations.get(plan_id) == correlation_id:
                    if not task.done():
                        task.cancel()
                        logger.info(f"User cancellation triggered. Cancelled task for plan: {plan_id}")

    def _check_cancelled(self, correlation_id: str) -> bool:
        with self._lock:
            return correlation_id in self._cancelled_correlation_ids
