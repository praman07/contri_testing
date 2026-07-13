"""
Integration test suite for Layer 10 — Goal Engine.

Verifies:
  1. Boot registration: goal_engine is resolved and bootable after context_engine & planner_engine.
  2. State transitions: enforces strict lifecycle state machine and raises ValueError for invalid paths.
  3. Hierarchy and rollup: cascading progress rollup and automatic completion when child progress hits 100%.
  4. tag-based priority conflict resolution: active tag collisions resolve to the higher-priority goal.
  5. Context deviation watchdog: emits warning event when focused apps distract from active goals.
  6. Verification triggers: maps plans to goals and transitions goal state on verification passed/failed.
  7. Teardown cleanup.
"""

import os
import sys
import asyncio
import logging
from typing import List

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.interfaces.goal import IGoalEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Goal.Test")

async def main():
    logger.info("=== STARTING GOAL ENGINE INTEGRATION TEST ===")

    # 1. Bootstrap and DI container setup
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)

    # Wire event bus loops
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    # Resolve goal engine
    goal_engine: IGoalEngine = container.resolve(IGoalEngine)

    # Track published events
    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Test Recorder Captured Event: {event.topic} -> {event.payload}")

    event_bus.subscribe("goal.*", recorder)

    # 2. Boot Order Verification
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "goal_engine" in boot_order
    assert "context_engine" in boot_order
    assert "planner_engine" in boot_order

    ctx_idx = boot_order.index("context_engine")
    plan_idx = boot_order.index("planner_engine")
    goal_idx = boot_order.index("goal_engine")
    assert ctx_idx < goal_idx, "context_engine must initialize before goal_engine"
    assert plan_idx < goal_idx, "planner_engine must initialize before goal_engine"
    logger.info("Step 1: Boot order verification passed.")

    # Initialize all modules
    for mod_name in boot_order:
        mod = registry.get_module(mod_name)
        mod.initialize()
        mod.start()

    logger.info("Step 2: Lifecycle startup passed.")

    # 3. Test goal creation and state machine transitions
    logger.info("--- Test Case 1: State Machine Transitions ---")
    goal_dict = await goal_engine.create_goal(
        title="Test Transition Goal",
        description="Verifies valid and invalid transitions"
    )
    goal_id = goal_dict["goal_id"]
    assert goal_dict["state"] == "DRAFT"

    # Try invalid transition: DRAFT -> COMPLETED
    try:
        await goal_engine.update_goal_state(goal_id, "COMPLETED")
        assert False, "Should have raised ValueError for DRAFT -> COMPLETED"
    except ValueError as e:
        logger.info(f"Expected failure caught: {e}")

    # Valid transition: DRAFT -> ACTIVE
    g_active = await goal_engine.update_goal_state(goal_id, "ACTIVE")
    assert g_active["state"] == "ACTIVE"

    # Valid transition: ACTIVE -> PAUSED
    g_paused = await goal_engine.update_goal_state(goal_id, "PAUSED")
    assert g_paused["state"] == "PAUSED"

    # Valid transition: PAUSED -> ACTIVE
    g_active_2 = await goal_engine.update_goal_state(goal_id, "ACTIVE")
    assert g_active_2["state"] == "ACTIVE"

    # Valid transition: ACTIVE -> COMPLETED
    g_comp = await goal_engine.update_goal_state(goal_id, "COMPLETED")
    assert g_comp["state"] == "COMPLETED"

    # Give event bus dispatch loop time to flush queued events
    await asyncio.sleep(0.2)

    # Verify event routing for state change
    state_changed_events = [e for e in events_received if e.topic == "goal.state_changed"]
    logger.info(f"State changed events captured: {len(state_changed_events)}")
    assert len(state_changed_events) > 0
    logger.info("Test Case 1 passed.")

    # 4. Test Goal hierarchy and progress rollup
    logger.info("--- Test Case 2: Hierarchy and Progress Rollup ---")
    parent_dict = await goal_engine.create_goal("Parent Goal", "Root parent goal")
    parent_id = parent_dict["goal_id"]

    child1 = await goal_engine.create_goal("Child 1", "First child leaf", parent_goal_id=parent_id)
    child2 = await goal_engine.create_goal("Child 2", "Second child leaf", parent_goal_id=parent_id)
    child3 = await goal_engine.create_goal("Child 3", "Third child leaf", parent_goal_id=parent_id)

    # Activate all of them to watch rollups
    await goal_engine.update_goal_state(parent_id, "ACTIVE")
    await goal_engine.update_goal_state(child1["goal_id"], "ACTIVE")
    await goal_engine.update_goal_state(child2["goal_id"], "ACTIVE")
    await goal_engine.update_goal_state(child3["goal_id"], "ACTIVE")

    # Direct progress updates should fail on parent
    try:
        await goal_engine.record_progress(parent_id, 50.0)
        assert False, "Should have failed to record progress directly on parent"
    except ValueError as e:
        logger.info(f"Expected failure caught on parent progress record: {e}")

    # Record 100% on child 1
    await goal_engine.record_progress(child1["goal_id"], 100.0)
    
    # Parent progress should be round(100 / 3, 2) = 33.33%
    parent_node_dict = await goal_engine.get_goal(parent_id)
    logger.info(f"Parent progress after child 1 complete: {parent_node_dict['progress_percent']}%")
    assert 33.3 <= parent_node_dict["progress_percent"] <= 33.4

    # Complete child 2 and child 3
    await goal_engine.record_progress(child2["goal_id"], 100.0)
    await goal_engine.record_progress(child3["goal_id"], 100.0)

    # Parent progress should be 100%, and state automatically COMPLETED
    parent_node_dict = await goal_engine.get_goal(parent_id)
    logger.info(f"Parent progress after all children complete: {parent_node_dict['progress_percent']}%")
    logger.info(f"Parent state after all children complete: {parent_node_dict['state']}")
    assert parent_node_dict["progress_percent"] == 100.0
    assert parent_node_dict["state"] == "COMPLETED"
    logger.info("Test Case 2 passed.")

    # 5. tag-based priority conflict check
    logger.info("--- Test Case 3: Priority Conflict Resolution ---")
    # Goal A: Priority 5, tag: "workspace_focus"
    goal_a = await goal_engine.create_goal(
        title="High Priority Goal A",
        description="Priority 5",
        priority=5,
        tags=["workspace_focus"]
    )
    # Goal B: Priority 2, tag: "workspace_focus"
    goal_b = await goal_engine.create_goal(
        title="Low Priority Goal B",
        description="Priority 2",
        priority=2,
        tags=["workspace_focus"]
    )

    # Activate Goal B first -> goes to ACTIVE
    await goal_engine.update_goal_state(goal_b["goal_id"], "ACTIVE")
    node_b_active = await goal_engine.get_goal(goal_b["goal_id"])
    assert node_b_active["state"] == "ACTIVE"

    # Activate Goal A -> A becomes ACTIVE, B is paused due to conflict
    await goal_engine.update_goal_state(goal_a["goal_id"], "ACTIVE")
    
    node_a_final = await goal_engine.get_goal(goal_a["goal_id"])
    node_b_final = await goal_engine.get_goal(goal_b["goal_id"])
    
    logger.info(f"Goal A state: {node_a_final['state']}")
    logger.info(f"Goal B state: {node_b_final['state']}")
    
    assert node_a_final["state"] == "ACTIVE"
    assert node_b_final["state"] == "PAUSED"

    # Wait for async event bus to flush conflict events
    await asyncio.sleep(0.2)

    conflict_events = [e for e in events_received if e.topic == "goal.conflict_detected"]
    logger.info(f"Conflict events captured: {len(conflict_events)}")
    assert len(conflict_events) > 0
    assert conflict_events[-1].payload["conflict_tag"] == "workspace_focus"
    logger.info("Test Case 3 passed.")

    # 6. Context updated & deviation alarm
    logger.info("--- Test Case 4: Deviation Alarm ---")
    goal_c = await goal_engine.create_goal(
        title="Write Code",
        description="Needs focus",
        tags=["requires_focus"]
    )
    await goal_engine.update_goal_state(goal_c["goal_id"], "ACTIVE")
    
    # Set deviation threshold to 0.0 seconds for instant deviation detection
    goal_engine.deviation_threshold_seconds = 0.0

    # Publish distracting context update
    event_bus.publish(Event(
        _topic="context.updated",
        _source="test",
        _payload={
            "active_window": {
                "process_name": "YouTube",
                "title": "Watching Cat Videos"
            },
            "perceived_user_activity": "active"
        }
    ))
    
    await asyncio.sleep(0.1)

    deviation_events = [e for e in events_received if e.topic == "goal.deviation_detected"]
    assert len(deviation_events) > 0
    payload = deviation_events[-1].payload
    assert payload["goal_id"] == goal_c["goal_id"]
    assert payload["deviation_type"] == "distracting_media_usage"
    
    # PII scrubbing check: details or payload must not contain "Cat Videos" or window title
    logger.info(f"Deviation Event Payload: {payload}")
    assert "Cat Videos" not in payload.get("details", "")
    logger.info("Test Case 4 passed.")

    # 7. Verification triggers
    logger.info("--- Test Case 5: Verification Triggers ---")
    goal_d = await goal_engine.create_goal(
        title="Verify Workflow Goal",
        description="Triggers on plan outcome"
    )
    await goal_engine.update_goal_state(goal_d["goal_id"], "ACTIVE")

    # Start a plan linked to goal_d
    plan_id = "plan_xyz_123"
    event_bus.publish(Event(
        _topic="planning.plan_started",
        _source="test",
        _payload={"plan_id": plan_id, "goal_id": goal_d["goal_id"]}
    ))
    await asyncio.sleep(0.1)

    # Publish verification failure first
    event_bus.publish(Event(
        _topic="verification.failed",
        _source="test",
        _payload={"plan_id": plan_id}
    ))
    await asyncio.sleep(0.1)

    node_d_failed = await goal_engine.get_goal(goal_d["goal_id"])
    logger.info(f"Goal D state after failure: {node_d_failed['state']}")
    assert node_d_failed["state"] == "BLOCKED"
    assert any("Verification failed" in b for b in node_d_failed["blockers"])

    # Resolve and activate again
    await goal_engine.update_goal_state(goal_d["goal_id"], "ACTIVE")

    # Publish verification success
    event_bus.publish(Event(
        _topic="verification.passed",
        _source="test",
        _payload={"plan_id": plan_id}
    ))
    await asyncio.sleep(0.1)

    node_d_passed = await goal_engine.get_goal(goal_d["goal_id"])
    logger.info(f"Goal D state after success: {node_d_passed['state']}")
    assert node_d_passed["state"] == "COMPLETED"
    logger.info("Test Case 5 passed.")

    # 8. Teardown
    logger.info("--- Test Case 6: Teardown Cleanup ---")
    for mod_name in reversed(boot_order):
        mod = registry.get_module(mod_name)
        mod.stop()

    assert len(await goal_engine.get_goal_hierarchy()) == 0
    logger.info("Test Case 6 passed.")

    logger.info("=== ALL GOAL ENGINE INTEGRATION TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
