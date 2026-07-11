"""
Layer 05 — Planner Engine

Responsible for transforming reasoning results and context snapshots into structured,
dependency-resolved, and validated ExecutionPlans.
Does not directly execute actions, reason, or communicate with hardware/execution providers.
"""
import logging
import threading
import uuid
import datetime
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.planner import IPlannerEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.planner.models import (
    PlanStep,
    ExecutionPlan,
    ReasoningResult,
    ContextSnapshot,
    UserGoal
)

logger = logging.getLogger("Override.Planner.Engine")

class PlannerEngine(OverrideModule, IPlannerEngine):
    """
    Layer 05 — Planner Engine.
    Subscribes to reasoning and context events, decomposes actions, resolves step
    dependencies topologically, validates schemas, and publishes execution plans.
    """

    def __init__(self, event_bus: IEventBus, config: ConfigurationManager):
        super().__init__("planner_engine")
        self._event_bus = event_bus
        self._config = config
        
        self._lock = threading.RLock()
        self._latest_context: Optional[ContextSnapshot] = None
        self._latest_goal: Optional[UserGoal] = None
        self._active_plans: Dict[str, ExecutionPlan] = {}
        self._executor: Optional[ThreadPoolExecutor] = None

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        logger.info("Initializing Planner Engine...")
        
        # Subscribe to reasoning results
        self._event_bus.subscribe("reasoning.result_ready", self._on_reasoning_result_ready)
        
        # Subscribe to context and goal updates
        self._event_bus.subscribe("context.updated", self._on_context_updated)
        self._event_bus.subscribe("goal.created", self._on_goal_created)
        
        # Subscribe to manual/user approval and rejection facts
        self._event_bus.subscribe("ui.user_approved", self._on_user_approved)
        self._event_bus.subscribe("ui.user_rejected", self._on_user_rejected)

        logger.info("Planner Engine initialized.")

    def on_start(self) -> None:
        logger.info("Starting Planner Engine...")
        
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="Override.Planner.Worker"
        )

        self._event_bus.publish(Event(
            _topic="planning.engine.started",
            _source="planner_engine",
            _payload={}
        ))
        logger.info("Planner Engine started.")

    def on_stop(self) -> None:
        logger.info("Stopping Planner Engine...")
        
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        # Unsubscribe
        self._event_bus.unsubscribe("reasoning.result_ready", self._on_reasoning_result_ready)
        self._event_bus.unsubscribe("context.updated", self._on_context_updated)
        self._event_bus.unsubscribe("goal.created", self._on_goal_created)
        self._event_bus.unsubscribe("ui.user_approved", self._on_user_approved)
        self._event_bus.unsubscribe("ui.user_rejected", self._on_user_rejected)

        self._event_bus.publish(Event(
            _topic="planning.engine.stopped",
            _source="planner_engine",
            _payload={}
        ))
        logger.info("Planner Engine stopped.")

    # ------------------------------------------------------------------
    # Public IPlannerEngine interface
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        reasoning_result: Any,
        context_snapshot: Any,
        goal: Optional[Any] = None,
        correlation_id: Optional[str] = None
    ) -> ExecutionPlan:
        """
        Transforms ReasoningResult and ContextSnapshot into a validated,
        topologically sorted ExecutionPlan.
        """
        # Convert inputs if dicts
        res = (
            ReasoningResult.from_dict(reasoning_result)
            if isinstance(reasoning_result, dict)
            else reasoning_result
        )
        ctx = (
            ContextSnapshot.from_dict(context_snapshot)
            if isinstance(context_snapshot, dict)
            else context_snapshot
        )
        g = (
            UserGoal.from_dict(goal)
            if isinstance(goal, dict)
            else goal
        )

        corr_id = correlation_id or str(uuid.uuid4())

        # Construct steps list from suggested actions
        steps: List[PlanStep] = []
        for idx, action_data in enumerate(res.suggested_actions):
            step_id = action_data.get("step_id") or f"step_{idx}"
            action = action_data.get("action", "")
            provider = action_data.get("provider", "")
            params = action_data.get("params", {})
            dependencies = action_data.get("dependencies", [])
            expected_outcome = action_data.get("expected_outcome", "")
            status = action_data.get("status", "pending")
            
            steps.append(PlanStep(
                step_id=step_id,
                action=action,
                provider=provider,
                params=params,
                dependencies=dependencies,
                expected_outcome=expected_outcome,
                status=status
            ))

        # Check for duplicate step IDs
        seen_ids = set()
        for step in steps:
            if step.step_id in seen_ids:
                raise ValueError(f"Duplicate PlanStep ID detected: {step.step_id}")
            seen_ids.add(step.step_id)

        # Check that all dependencies reference existing PlanSteps
        step_ids = {step.step_id for step in steps}
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Unknown dependency '{dep}' referenced by step '{step.step_id}'.")

        # Check that all steps have a valid provider (non-empty string)
        for step in steps:
            if not step.provider:
                raise ValueError(f"Unknown provider '{step.provider}' referenced by step '{step.step_id}'.")

        # Enforce configuration constraints
        cfg = self._config.planner
        if len(steps) > cfg.max_steps_per_plan:
            raise ValueError(
                f"Plan step count ({len(steps)}) exceeds max limit ({cfg.max_steps_per_plan})"
            )

        # Resolve step dependencies using topological sorting
        sorted_steps = self._topological_sort(steps)

        # Collect required providers and outcomes
        required_providers = list(dict.fromkeys(step.provider for step in sorted_steps if step.provider))
        expected_outcomes = [step.expected_outcome for step in sorted_steps if step.expected_outcome]

        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            correlation_id=corr_id,
            steps=sorted_steps,
            required_providers=required_providers,
            expected_outcomes=expected_outcomes,
            status="created",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            metadata={
                "confidence": res.confidence,
                "goal_id": g.goal_id if g else None
            }
        )

        with self._lock:
            self._active_plans[plan.plan_id] = plan

        return plan

    # ------------------------------------------------------------------
    # Helper & Validation routines
    # ------------------------------------------------------------------

    def _topological_sort(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Sorts steps based on dependency lists. Detects circular dependency cycles.
        Preserves original suggested sequence ordering when no dependencies constrain steps.
        """
        step_map = {step.step_id: step for step in steps}
        adj: Dict[str, List[str]] = {step_id: [] for step_id in step_map}
        in_degree: Dict[str, int] = {step_id: 0 for step_id in step_map}
        
        # Build dependency graph
        for step in steps:
            for dep in step.dependencies:
                if dep in step_map:
                    # dep must execute before step, so edge dep -> step
                    adj[dep].append(step.step_id)
                    in_degree[step.step_id] += 1
                else:
                    # External or missing dependencies in list: ignored for ordering
                    pass

        # Sort queue by original index to keep ordering deterministic
        original_order = {step.step_id: idx for idx, step in enumerate(steps)}
        queue = [step_id for step_id, deg in in_degree.items() if deg == 0]
        queue.sort(key=lambda sid: original_order[sid])
        
        ordered_step_ids: List[str] = []
        while queue:
            # Pop next in original sequence order
            queue.sort(key=lambda sid: original_order[sid])
            curr = queue.pop(0)
            ordered_step_ids.append(curr)
            
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_step_ids) != len(steps):
            raise ValueError("Circular dependency detected in plan steps")

        return [step_map[step_id] for step_id in ordered_step_ids]

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_reasoning_result_ready(self, event: IEvent) -> None:
        """Runs on reasoning engine result ready."""
        payload = event.payload or {}
        correlation_id = payload.get("correlation_id") or str(uuid.uuid4())
        
        with self._lock:
            ctx = self._latest_context or ContextSnapshot()
            goal = self._latest_goal

        if self._executor:
            self._executor.submit(
                self._process_planning_task,
                payload,
                ctx,
                goal,
                correlation_id
            )

    async def _on_context_updated(self, event: IEvent) -> None:
        """Keeps planner context current with latest perception updates."""
        payload = event.payload or {}
        ctx = ContextSnapshot.from_dict(payload)
        with self._lock:
            self._latest_context = ctx

    async def _on_goal_created(self, event: IEvent) -> None:
        """Stores active target goal."""
        payload = event.payload or {}
        goal = UserGoal.from_dict(payload)
        with self._lock:
            self._latest_goal = goal

    async def _on_user_approved(self, event: IEvent) -> None:
        """Handles user approval facts."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id") or payload.get("target_id")
        if not plan_id:
            return
            
        with self._lock:
            plan = self._active_plans.get(plan_id)
            if plan and plan.status in ("created", "running"):
                approved_plan = plan.copy_with(status="approved")
                self._active_plans[plan_id] = approved_plan
                
                # Publish approved plan
                self._event_bus.publish(Event(
                    _topic="planning.plan_approved",
                    _source="planner_engine",
                    _payload=approved_plan.to_dict()
                ))

    async def _on_user_rejected(self, event: IEvent) -> None:
        """Handles user rejection facts."""
        payload = event.payload or {}
        plan_id = payload.get("plan_id") or payload.get("target_id")
        if not plan_id:
            return
            
        with self._lock:
            plan = self._active_plans.get(plan_id)
            if plan:
                rejected_plan = plan.copy_with(status="rejected")
                self._active_plans[plan_id] = rejected_plan
                
                # Publish rejected plan
                self._event_bus.publish(Event(
                    _topic="planning.plan_rejected",
                    _source="planner_engine",
                    _payload=rejected_plan.to_dict()
                ))

    # ------------------------------------------------------------------
    # Background Processing task
    # ------------------------------------------------------------------

    def _process_planning_task(
        self,
        reasoning_data: Dict[str, Any],
        ctx: ContextSnapshot,
        goal: Optional[UserGoal],
        correlation_id: str
    ) -> None:
        """Compiles planning inputs into an ExecutionPlan and broadcasts to the system."""
        try:
            plan = self.generate_plan(reasoning_data, ctx, goal, correlation_id)
            
            # Publish Plan Created
            self._event_bus.publish(Event(
                _topic="planning.plan_created",
                _source="planner_engine",
                _payload=plan.to_dict()
            ))

            # Publish Task Scheduled
            self._event_bus.publish(Event(
                _topic="planning.task_scheduled",
                _source="planner_engine",
                _payload={
                    "plan_id": plan.plan_id,
                    "correlation_id": correlation_id,
                    "timestamp": plan.timestamp
                }
            ))



        except Exception as e:
            logger.error(f"Planning compilation failed: {e}", exc_info=True)
            self._event_bus.publish(Event(
                _topic="planning.plan_rejected",
                _source="planner_engine",
                _payload={
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            ))
