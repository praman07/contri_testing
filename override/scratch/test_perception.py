"""
Integration test suite for Layer 03 — Perception Engine.

Tests:
  1. Topological bootstrap: perception_engine appears after observation_engine and environment_engine.
  2. perception.engine.started published on boot.
  3. observation.window_changed → perception.window_context_classified published.
  4. observation.window_changed → perception.frame_ready published.
  5. PerceptionFrame has correct app category (VSCode → 'ide').
  6. observation.audio_captured with transcript → perception.speech_recognized published.
  7. PerceptionFrame speech_transcript is normalized.
  8. environment.updated with clipboard URL → perception.clipboard_classified published.
  9. PerceptionFrame clipboard_text_type == 'url'.
 10. Clean shutdown with zero thread leaks.
"""

import asyncio
import logging
import threading
import time
import sys
import os
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.pal.base import PlatformAbstractionLayer
from override.runtime.perception.engine import PerceptionEngine
from override.runtime.observation.engine import ObservationEngine
from override.runtime.environment.engine import EnvironmentEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Perception.Test")


class MockPALWrapper:
    """Wrapper to dynamically override PAL methods during testing."""
    def __init__(self, real_pal: PlatformAbstractionLayer):
        self._real_pal = real_pal
        self.mock_running_apps = []
        self.mock_active_window = {}

    def get_running_applications(self):
        return self.mock_running_apps

    def get_active_window(self):
        return self.mock_active_window

    def get_window_hierarchy(self):
        return []

    def get_monitor_layout(self):
        return []

    def get_clipboard_state(self):
        return {"type": "text", "text": "", "length": 0, "hash": 0}

    def get_connected_devices(self):
        return []

    def get_network_status(self):
        return {"connected": True, "type": "lan/wifi", "flags": 0}

    def get_battery_status(self):
        return {"ac_status": "online", "percent": 100, "charging": False, "life_time_seconds": -1}


async def main():
    logger.info("=== STARTING PERCEPTION ENGINE INTEGRATION TEST ===")

    # ---- Baseline resource count ------------------------------------------
    initial_thread_count = threading.active_count()

    # ---- Bootstrap -----------------------------------------------------------
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)

    # ---- Topological boot order verification --------------------------------
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "perception_engine" in boot_order
    assert "observation_engine" in boot_order
    assert "environment_engine" in boot_order
    obs_idx = boot_order.index("observation_engine")
    env_idx = boot_order.index("environment_engine")
    per_idx = boot_order.index("perception_engine")
    assert obs_idx < per_idx, "observation_engine must initialize before perception_engine"
    assert env_idx < per_idx, "environment_engine must initialize before perception_engine"
    logger.info("Boot order assertion passed.")

    # ---- Configure event loop in EventBus -----------------------------------
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    # ---- Event capture setup ------------------------------------------------
    captured_events: List[IEvent] = []

    async def recorder(event: IEvent) -> None:
        captured_events.append(event)
        print(f"RECORDER CAPTURED EVENT: {event.topic} from {event.source}")

    event_bus.subscribe("perception.*", recorder)
    event_bus.subscribe("observation.*", recorder)
    event_bus.subscribe("environment.*", recorder)

    # ---- Initialize all modules (use on_initialize to avoid double-init guard) ----
    for module_id in boot_order:
        registry.get_module(module_id).on_initialize()

    # ---- Clear observation providers to prevent real OS event flooding ------
    obs_engine: ObservationEngine = container.resolve(ObservationEngine)
    obs_engine._providers.clear()
    obs_engine._provider_map.clear()

    # ---- Speed up environment engine poll to prevent 3s blocking on thread join ----
    env_engine: EnvironmentEngine = container.resolve(EnvironmentEngine)
    real_pal = container.resolve(PlatformAbstractionLayer)
    mock_pal = MockPALWrapper(real_pal)
    env_engine._pal = mock_pal
    
    # Mock stop_event.wait to use a very short timeout in test
    original_wait = env_engine._stop_event.wait
    env_engine._stop_event.wait = lambda timeout: original_wait(timeout=0.05)

    # ---- Start all modules --------------------------------------------------
    for module_id in boot_order:
        registry.get_module(module_id).on_start()

    await asyncio.sleep(0.2)

    # ---- Test 1: perception.engine.started was published --------------------
    topics = [e.topic for e in captured_events]
    assert "perception.engine.started" in topics, f"Missing perception.engine.started. Got: {topics}"
    logger.info("TEST 1 PASSED: perception.engine.started published.")

    # ---- Test 2 & 3: window_changed → window_context_classified + frame_ready --
    window_payload = {
        "hwnd": 12345,
        "title": "Visual Studio Code",
        "class_name": "Chrome_WidgetWin_1",
        "pid": 999,
        "bounds": {"left": 0, "top": 0, "right": 1920, "bottom": 1080, "width": 1920, "height": 1080}
    }
    event_bus.publish(Event(
        _topic="observation.window_changed",
        _source="observation_engine",
        _payload=window_payload
    ))
    await asyncio.sleep(0.3)

    topics = [e.topic for e in captured_events]
    assert "perception.window_context_classified" in topics, (
        f"Missing perception.window_context_classified. Got: {topics}"
    )
    logger.info("TEST 2 PASSED: perception.window_context_classified published.")

    assert "perception.frame_ready" in topics, f"Missing perception.frame_ready. Got: {topics}"
    logger.info("TEST 3 PASSED: perception.frame_ready published.")

    # ---- Test 4: PerceptionFrame category is 'ide' --------------------------
    perception_engine: PerceptionEngine = container.resolve(PerceptionEngine)
    frame = perception_engine.get_current_frame()
    assert frame.active_window_title == "Visual Studio Code", (
        f"Expected title 'Visual Studio Code', got '{frame.active_window_title}'"
    )
    assert frame.active_app_category == "ide", (
        f"Expected category 'ide', got '{frame.active_app_category}'"
    )
    logger.info(f"TEST 4 PASSED: PerceptionFrame category = '{frame.active_app_category}'.")

    # ---- Test 5 & 6: audio_captured + transcript ----------------------------
    event_bus.publish(Event(
        _topic="observation.audio_captured",
        _source="observation_engine",
        _payload={"transcript": "   open  terminal   "}
    ))
    await asyncio.sleep(0.3)

    topics = [e.topic for e in captured_events]
    assert "perception.speech_recognized" in topics, (
        f"Missing perception.speech_recognized. Got: {topics}"
    )
    logger.info("TEST 5 PASSED: perception.speech_recognized published.")

    frame2 = perception_engine.get_current_frame()
    assert frame2.speech_transcript == "open terminal", (
        f"Expected normalized 'open terminal', got '{frame2.speech_transcript}'"
    )
    logger.info("TEST 6 PASSED: Transcript normalized correctly.")

    # ---- Test 7 & 8: clipboard classified as 'url' via environment.updated ---
    event_bus.publish(Event(
        _topic="environment.updated",
        _source="environment_engine",
        _payload={
            "active_window": window_payload,
            "clipboard_state": {
                "type": "text",
                "length": 42,
                "hash": 9999,
                "text": "https://github.com/override/cognitive-runtime"
            }
        }
    ))
    await asyncio.sleep(0.3)

    topics = [e.topic for e in captured_events]
    assert "perception.clipboard_classified" in topics, (
        f"Missing perception.clipboard_classified. Got: {topics}"
    )
    logger.info("TEST 7 PASSED: perception.clipboard_classified published.")

    frame3 = perception_engine.get_current_frame()
    assert frame3.clipboard_text_type == "url", (
        f"Expected clipboard_text_type 'url', got '{frame3.clipboard_text_type}'"
    )
    logger.info("TEST 8 PASSED: clipboard_text_type correctly classified as 'url'.")

    # ---- Shutdown (reverse order) -------------------------------------------
    logger.info("Stopping all engines in reverse order...")
    for module_id in reversed(boot_order):
        registry.get_module(module_id).on_stop()

    event_bus.stop()
    await asyncio.sleep(0.2)

    # ---- Resource leak check ------------------------------------------------
    final_thread_count = threading.active_count()
    thread_delta = final_thread_count - initial_thread_count
    logger.info(f"Thread count delta (final - initial): {thread_delta}")
    assert thread_delta == 0, f"Thread leak detected! Delta = {thread_delta}"
    logger.info("TEST 9 PASSED: Zero thread leaks.")

    # ---- Final report --------------------------------------------------------
    all_topics = sorted(set(e.topic for e in captured_events))
    print(f"\nTEST TOPICS CAPTURED: {all_topics}\n")
    logger.info("=== ALL PERCEPTION ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())
