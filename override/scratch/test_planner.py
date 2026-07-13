"""
Integration test suite for Layer 05 — Planner Engine.

Verifies:
  1. Boot registration: planner_engine is resolved and registered properly, booting after perception_engine and memory_engine.
  2. Lifecycle: publishes planning.engine.started and planning.engine.stopped.
  3. Plan creation: generates an ExecutionPlan from ReasoningResult and ContextSnapshot, publishing planning.plan_created and planning.task_scheduled.
  4. Dependency resolution & topological sort: resolves step orders, detecting cycles (throwing ValueError) and enforcing max steps limit.
  5. User confirmation & approval flow: respects safety_confirmations_required config flag, handling manual approve/reject events.
  6. Clean resources shutdown: unsubscribes event handlers and shuts down thread pool cleanly.
"""

import os
import sys
import asyncio
import logging
import uuid
from typing import List, Dict, Any

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.interfaces.planner import IPlannerEngine
from override.runtime.planner.engine import PlannerEngine
from override.runtime.planner.models import ReasoningResult, ContextSnapshot, UserGoal, ExecutionPlan
from override.runtime.config.config import ConfigurationManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Planner.Test")


async def main():
    logger.info("=== STARTING PLANNER ENGINE INTEGRATION TEST ===")

    # 1. Bootstrap and DI registry verification
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)

    # Set the running loop in the event bus so background dispatcher task starts
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    # Track published events via async recorder
    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Test Recorder Captured Event: {event.topic}")

    event_bus.subscribe("planning.*", recorder)

    # Boot order test
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "planner_engine" in boot_order
    assert "perception_engine" in boot_order
    assert "memory_engine" in boot_order
    
    per_idx = boot_order.index("perception_engine")
    mem_idx = boot_order.index("memory_engine")
    plan_idx = boot_order.index("planner_engine")
    
    assert per_idx < plan_idx, "perception_engine must initialize before planner_engine"
    assert mem_idx < plan_idx, "memory_engine must initialize before planner_engine"
    logger.info("1. Boot order verification passed.")

    # Initialize all modules in topological order (on_initialize)
    for mod_name in boot_order:
        logger.info(f"Initializing module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_initialize()

    # Locate Planner Engine
    planner_engine = container.resolve(IPlannerEngine)
    assert isinstance(planner_engine, PlannerEngine)

    # 2. Lifecycle started event verification
    for mod_name in boot_order:
        logger.info(f"Starting module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_start()

    # Give startup events a brief moment to propagate
    await asyncio.sleep(0.1)

    started_events = [e for e in events_received if e.topic == "planning.engine.started"]
    assert len(started_events) > 0, "planning.engine.started must be published on start"
    logger.info("2. Lifecycle start event verification passed.")

    # 3. Plan Creation
    events_received.clear()

    reasoning_data = {
        "analysis": "Open the browser to search for coding examples",
        "suggested_actions": [
            {
                "step_id": "step_1",
                "action": "open_browser",
                "provider": "chrome",
                "params": {"url": "https://google.com"},
                "dependencies": [],
                "expected_outcome": "browser_opened"
            },
            {
                "step_id": "step_2",
                "action": "search",
                "provider": "chrome",
                "params": {"query": "python decorators"},
                "dependencies": ["step_1"],
                "expected_outcome": "results_shown"
            }
        ],
        "confidence": 0.95
    }

    # Generate via public API directly first
    ctx = ContextSnapshot(active_applications=["VSCode"])
    goal = UserGoal(goal_id="g_1", description="Find python decorator tips", target_outcome="tips_found")
    
    plan = planner_engine.generate_plan(reasoning_data, ctx, goal, correlation_id="c_1")
    assert isinstance(plan, ExecutionPlan)
    assert plan.correlation_id == "c_1"
    assert len(plan.steps) == 2
    assert plan.steps[0].step_id == "step_1"
    assert plan.steps[1].step_id == "step_2"
    assert plan.required_providers == ["chrome"]
    assert plan.expected_outcomes == ["browser_opened", "results_shown"]
    logger.info("Direct generate_plan execution succeeded.")

    # 4. Dependency Resolution & Topological Sorting
    # Test case A: Linear dependencies
    # Test case B: Cycle detection
    cycle_data = {
        "analysis": "Circular dependency test case",
        "suggested_actions": [
            {
                "step_id": "step_A",
                "action": "click",
                "provider": "system",
                "dependencies": ["step_B"]
            },
            {
                "step_id": "step_B",
                "action": "type",
                "provider": "system",
                "dependencies": ["step_A"]
            }
        ]
    }
    try:
        planner_engine.generate_plan(cycle_data, ctx)
        assert False, "Should have thrown ValueError on circular dependencies"
    except ValueError as ve:
        logger.info(f"Expected failure caught for circular dependencies: {ve}")
        assert "Circular dependency" in str(ve)

    # Test case C: Max steps enforcement
    config_manager = container.resolve(ConfigurationManager)
    # Temporary override configuration limit to 1 step
    original_max = config_manager.planner.max_steps_per_plan
    # We can patch max steps by setting it
    object.__setattr__(config_manager.planner, 'max_steps_per_plan', 1)
    
    try:
        planner_engine.generate_plan(reasoning_data, ctx)
        assert False, "Should have thrown ValueError since steps count (2) > max limit (1)"
    except ValueError as ve:
        logger.info(f"Expected failure caught for max steps limit: {ve}")
        assert "exceeds max limit" in str(ve)
        
    # Restore original config
    object.__setattr__(config_manager.planner, 'max_steps_per_plan', original_max)

    # New Test: Missing dependency detection
    missing_dep_data = {
        "analysis": "Missing dependency test case",
        "suggested_actions": [
            {
                "step_id": "step_A",
                "action": "click",
                "provider": "system",
                "dependencies": ["step_Z"]
            }
        ]
    }
    try:
        planner_engine.generate_plan(missing_dep_data, ctx)
        assert False, "Should have thrown ValueError on missing dependencies"
    except ValueError as ve:
        logger.info(f"Expected failure caught for missing dependencies: {ve}")
        assert "Unknown dependency 'step_Z' referenced by step 'step_A'." in str(ve)

    # New Test: Duplicate step IDs detection
    duplicate_id_data = {
        "analysis": "Duplicate step ID test case",
        "suggested_actions": [
            {
                "step_id": "step_A",
                "action": "click",
                "provider": "system",
                "dependencies": []
            },
            {
                "step_id": "step_A",
                "action": "type",
                "provider": "system",
                "dependencies": []
            }
        ]
    }
    try:
        planner_engine.generate_plan(duplicate_id_data, ctx)
        assert False, "Should have thrown ValueError on duplicate step IDs"
    except ValueError as ve:
        logger.info(f"Expected failure caught for duplicate step IDs: {ve}")
        assert "Duplicate PlanStep ID detected: step_A" in str(ve)

    # New Test: Unknown provider detection
    unknown_provider_data = {
        "analysis": "Unknown provider test case",
        "suggested_actions": [
            {
                "step_id": "step_A",
                "action": "click",
                "provider": "",
                "dependencies": []
            }
        ]
    }
    try:
        planner_engine.generate_plan(unknown_provider_data, ctx)
        assert False, "Should have thrown ValueError on unknown provider"
    except ValueError as ve:
        logger.info(f"Expected failure caught for unknown provider: {ve}")
        assert "Unknown provider '' referenced by step 'step_A'." in str(ve)

    # New Test: Unreachable step detection
    unreachable_step_data = {
        "analysis": "Unreachable step test case",
        "suggested_actions": [
            {
                "step_id": "step_A",
                "action": "click",
                "provider": "system",
                "dependencies": []
            },
            {
                "step_id": "step_B",
                "action": "type",
                "provider": "system",
                "dependencies": ["step_C"]
            },
            {
                "step_id": "step_C",
                "action": "type",
                "provider": "system",
                "dependencies": ["step_B"]
            }
        ]
    }
    try:
        planner_engine.generate_plan(unreachable_step_data, ctx)
        assert False, "Should have thrown ValueError on unreachable steps (circular dependency)"
    except ValueError as ve:
        logger.info(f"Expected failure caught for unreachable steps (circular dependency): {ve}")
        assert "Circular dependency" in str(ve)

    logger.info("4. Dependency and cycle validation passed.")

    # 5. User Confirmation & Event Flow
    # Case A: safety_confirmations_required = True (default)
    # The event should be created, task scheduled, but NOT auto-approved.
    events_received.clear()
    
    event_bus.publish(Event(
        _topic="reasoning.result_ready",
        _source="reasoning_engine",
        _payload={
            "analysis": "Open browser",
            "suggested_actions": [
                {"step_id": "step_1", "action": "open", "provider": "chrome"}
            ],
            "correlation_id": "c_confirm"
        }
    ))
    
    await asyncio.sleep(0.2)
    
    created_events = [e for e in events_received if e.topic == "planning.plan_created"]
    assert len(created_events) == 1, "Should publish planning.plan_created"
    
    scheduled_events = [e for e in events_received if e.topic == "planning.task_scheduled"]
    assert len(scheduled_events) == 1, "Should publish planning.task_scheduled"

    approved_events = [e for e in events_received if e.topic == "planning.plan_approved"]
    assert len(approved_events) == 0, "Should not auto-approve when safety confirmations are required"
    
    # Trigger manual approval
    target_plan_id = created_events[0].payload["plan_id"]
    event_bus.publish(Event(
        _topic="ui.user_approved",
        _source="ui",
        _payload={"plan_id": target_plan_id}
    ))
    await asyncio.sleep(0.2)
    
    approved_events = [e for e in events_received if e.topic == "planning.plan_approved"]
    assert len(approved_events) == 1, "Should publish planning.plan_approved on manual approve event"
    assert approved_events[0].payload["status"] == "approved"

    # Case B: safety_confirmations_required = False
    # The Planner engine does not auto-approve on its own.
    # We verify it publishes the created event, and we mock the coordinator
    # publishing the ui.user_approved event to trigger approval.
    object.__setattr__(config_manager._schema, 'safety_confirmations_required', False)
    events_received.clear()

    event_bus.publish(Event(
        _topic="reasoning.result_ready",
        _source="reasoning_engine",
        _payload={
            "analysis": "Open browser fast",
            "suggested_actions": [
                {"step_id": "step_1", "action": "open", "provider": "chrome"}
            ],
            "correlation_id": "c_auto"
        }
    ))

    await asyncio.sleep(0.2)

    created_events = [e for e in events_received if e.topic == "planning.plan_created"]
    assert len(created_events) == 1
    
    # Verify no auto-approval was performed by the Planner Engine itself
    approved_events = [e for e in events_received if e.topic == "planning.plan_approved"]
    assert len(approved_events) == 0, "Planner should not auto-approve on its own"
    
    # Simulate higher-level coordinator auto-approving by publishing ui.user_approved
    target_plan_id_auto = created_events[0].payload["plan_id"]
    event_bus.publish(Event(
        _topic="ui.user_approved",
        _source="workflow_coordinator",
        _payload={"plan_id": target_plan_id_auto}
    ))
    await asyncio.sleep(0.2)
    
    approved_events = [e for e in events_received if e.topic == "planning.plan_approved"]
    assert len(approved_events) == 1
    assert approved_events[0].payload["status"] == "approved"
    
    # Restore original setting
    object.__setattr__(config_manager._schema, 'safety_confirmations_required', True)

    # Case C: Rejection testing
    events_received.clear()
    event_bus.publish(Event(
        _topic="reasoning.result_ready",
        _source="reasoning_engine",
        _payload={
            "analysis": "Open browser to reject",
            "suggested_actions": [
                {"step_id": "step_1", "action": "open", "provider": "chrome"}
            ],
            "correlation_id": "c_reject"
        }
    ))
    await asyncio.sleep(0.2)
    
    created_events = [e for e in events_received if e.topic == "planning.plan_created"]
    assert len(created_events) == 1
    
    # Trigger manual rejection
    target_plan_id_reject = created_events[0].payload["plan_id"]
    event_bus.publish(Event(
        _topic="ui.user_rejected",
        _source="ui",
        _payload={"plan_id": target_plan_id_reject}
    ))
    await asyncio.sleep(0.2)
    
    rejected_events = [e for e in events_received if e.topic == "planning.plan_rejected"]
    assert len(rejected_events) == 1, "Should publish planning.plan_rejected on manual reject event"
    assert rejected_events[0].payload["status"] == "rejected"
    
    logger.info("5. Confirmation and approval/rejection/coordinator flow verification passed.")

    # 6. Clean Shutdown
    for mod_name in reversed(boot_order):
        logger.info(f"Stopping module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_stop()

    await asyncio.sleep(0.1)

    stopped_events = [e for e in events_received if e.topic == "planning.engine.stopped"]
    assert len(stopped_events) > 0, "planning.engine.stopped must be published on stop"
    logger.info("6. Clean shutdown verification passed.")

    logger.info("=== ALL PLANNER ENGINE TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())
