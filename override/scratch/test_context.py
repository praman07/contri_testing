"""
Integration test suite for Layer 09 — Context / World Model Engine.

Verifies:
  1. Boot registration: context_engine is resolved and bootable after perception_engine & memory_engine.
  2. Event routing & state synthesis: window_changed, frame_ready, environment_changed.
  3. Context snapshot consistency: active window, running apps, clipboard, system resources.
  4. Entity Graph updates: node and relationship creation.
  5. PII Redaction: scrubs credentials, SSNs, credit cards from window titles and clipboard.
  6. Sliding history window: history buffer size capped at 10.
  7. Anomaly detection: low battery, high CPU usage, network loss.
  8. Teardown & resource cleanup.
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
from override.runtime.interfaces.context import IContextEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Context.Test")

async def main():
    logger.info("=== STARTING CONTEXT ENGINE INTEGRATION TEST ===")

    # 1. Bootstrap and DI container setup
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)

    # Wire event bus loops
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    # Resolve context engine
    context_engine: IContextEngine = container.resolve(IContextEngine)

    # Track published events
    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Test Recorder Captured: {event.topic}")

    event_bus.subscribe("context.*", recorder)

    # 2. Boot Order Verification
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "context_engine" in boot_order
    assert "perception_engine" in boot_order
    assert "memory_engine" in boot_order

    perp_idx = boot_order.index("perception_engine")
    mem_idx = boot_order.index("memory_engine")
    ctx_idx = boot_order.index("context_engine")
    assert perp_idx < ctx_idx, "perception_engine must initialize before context_engine"
    assert mem_idx < ctx_idx, "memory_engine must initialize before context_engine"
    logger.info("Step 1: Boot order verification passed.")

    # Initialize all modules
    for mod_name in boot_order:
        mod = registry.get_module(mod_name)
        mod.initialize()
        mod.start()

    logger.info("Step 2: Lifecycle startup passed.")

    # 3. Test Event Ingestion: focused window change
    logger.info("--- Test Case 1: Focused Window Change ---")
    event_bus.publish(Event(
        _topic="observation.window_changed",
        _source="test",
        _payload={
            "title": "VS Code - main.py",
            "process_name": "code.exe",
            "bounds": {"x": 100, "y": 100, "width": 800, "height": 600},
            "is_minimized": False
        }
    ))
    await asyncio.sleep(0.1)

    active_win = await context_engine.get_active_window()
    assert active_win["process_name"] == "code.exe"
    assert active_win["title"] == "VS Code - main.py"
    logger.info("Test Case 1 passed.")

    # 4. Test Event Ingestion: perception OCR & clipboard with PII
    logger.info("--- Test Case 2: Perception Frame Ingestion & PII Redaction ---")
    # Clipboard and Title containing PII values
    sensitive_clipboard = "My API key is secret-api-key: sk-1234567890abcdef1234567890abcdef"
    sensitive_title = "Bank Account Details - SSN: 123-45-6789"
    
    event_bus.publish(Event(
        _topic="observation.window_changed",
        _source="test",
        _payload={
            "title": sensitive_title,
            "process_name": "chrome.exe"
        }
    ))
    event_bus.publish(Event(
        _topic="perception.frame_ready",
        _source="test",
        _payload={
            "ocr_text": "Please open chrome.exe and visit www.google.com and https://github.com/override",
            "clipboard": sensitive_clipboard
        }
    ))
    await asyncio.sleep(0.1)

    # Assert PII is redacted
    scrubbed_clip = await context_engine.get_clipboard_context()
    scrubbed_win = await context_engine.get_active_window()

    logger.info(f"Scrubbed Clipboard: {scrubbed_clip}")
    logger.info(f"Scrubbed Window Title: {scrubbed_win['title']}")

    assert "[CREDENTIALS_REDACTED]" in scrubbed_clip or "REDACTED" in scrubbed_clip
    assert "[SSN_REDACTED]" in scrubbed_win["title"]
    logger.info("Test Case 2 passed.")

    # 5. Entity Graph Assertions
    logger.info("--- Test Case 3: Entity Graph Validation ---")
    state = await context_engine.get_current_state()
    entities = state["entities"]
    relationships = state["relationships"]

    entity_ids = [e["entity_id"] for e in entities]
    relationship_types = [r["relationship_type"] for r in relationships]

    logger.info(f"Entities in WorldState: {entity_ids}")
    logger.info(f"Relationships in WorldState: {relationship_types}")

    assert "user" in entity_ids
    assert "host_os" in entity_ids
    assert "app:chrome.exe" in entity_ids
    assert "url:https://github.com/override" in entity_ids
    assert "focuses" in relationship_types
    assert "contains" in relationship_types
    logger.info("Test Case 3 passed.")

    # 6. Environmental metrics & anomaly triggers
    logger.info("--- Test Case 4: Anomaly Detection ---")
    event_bus.publish(Event(
        _topic="environment.changed",
        _source="test",
        _payload={
            "running_applications": [{"process_name": "chrome.exe"}],
            "network_status": "disconnected",
            "power_source": "battery",
            "metrics": {
                "cpu_percent": 98.5,
                "available_memory_mb": 4096.0,
                "battery_percent": 12.0
            }
        }
    ))
    await asyncio.sleep(0.1)

    state = await context_engine.get_current_state()
    anomalies = state["detected_anomalies"]
    logger.info(f"Detected Anomalies: {anomalies}")

    assert "high_cpu_usage" in anomalies
    assert "low_battery" in anomalies
    assert "network_disconnected" in anomalies

    # Verify context.anomaly_detected events were published
    anomaly_events = [e for e in events_received if e.topic == "context.anomaly_detected"]
    assert len(anomaly_events) >= 3
    logger.info("Test Case 4 passed.")

    # 7. Sliding History limit (max 10)
    logger.info("--- Test Case 5: Sliding History Boundary ---")
    # Fire 15 successive updates
    for i in range(15):
        event_bus.publish(Event(
            _topic="observation.window_changed",
            _source="test",
            _payload={"title": f"Frame {i}", "process_name": "tester.exe"}
        ))
    await asyncio.sleep(0.2)

    # Check history length in context_engine
    logger.info(f"Total history frames captured: {len(context_engine._history)}")
    assert len(context_engine._history) == 10
    logger.info("Test Case 5 passed.")

    # 8. User Activity States
    logger.info("--- Test Case 6: User Activity State ---")
    # Simulate step started -> should set perceived activity to system_executing
    event_bus.publish(Event(
        _topic="execution.step_started",
        _source="test",
        _payload={"step_id": "step_001"}
    ))
    await asyncio.sleep(0.1)
    state = await context_engine.get_current_state()
    assert state["perceived_user_activity"] == "system_executing"

    # Simulate plan completed and then idle delay (set threshold to negative for instant idle)
    event_bus.publish(Event(
        _topic="planning.plan_completed",
        _source="test",
        _payload={"plan_id": "plan_001"}
    ))
    context_engine._idle_threshold_seconds = -1.0
    await asyncio.sleep(0.1)
    state = await context_engine.get_current_state()
    assert state["perceived_user_activity"] == "idle"

    # Simulate keyboard activity
    event_bus.publish(Event(
        _topic="observation.keyboard_input",
        _source="test",
        _payload={}
    ))
    context_engine._idle_threshold_seconds = 300.0
    await asyncio.sleep(0.1)
    state = await context_engine.get_current_state()
    assert state["perceived_user_activity"] == "active"
    logger.info("Test Case 6 passed.")

    # 9. Teardown
    logger.info("--- Test Case 7: Teardown & Resource Cleanup ---")
    # Stop all modules
    for mod_name in reversed(boot_order):
        mod = registry.get_module(mod_name)
        mod.stop()

    assert len(context_engine._history) == 0
    assert len(context_engine._running_applications) == 0
    logger.info("Test Case 7 passed.")

    logger.info("=== ALL CONTEXT ENGINE INTEGRATION TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
