import asyncio
import logging
import os
import sys
import threading
import time
from typing import List

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.pal.base import PlatformAbstractionLayer
from override.runtime.observation.engine import ObservationEngine
from override.runtime.environment.engine import EnvironmentEngine

# Configure basic logging for test visibility
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Environment.Test")

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

async def run_integration_test():
    logger.info("=== STARTING ENVIRONMENT ENGINE INTEGRATION TEST ===")
    
    # Capture initial thread/task baseline
    initial_threads = threading.active_count()
    initial_tasks = len(asyncio.all_tasks())
    
    # 1. Initialize Dependency Injection Container
    container = initialize_container()
    
    # 2. Discover and Register Modules
    discover_and_register_modules(container)
    
    # 3. Retrieve core modules and events
    registry = container.resolve(ModuleRegistry)
    event_bus = container.resolve(IEventBus)
    obs_engine = container.resolve(ObservationEngine)
    env_engine = container.resolve(EnvironmentEngine)
    real_pal = container.resolve(PlatformAbstractionLayer)
    
    # Wrap PAL to allow dynamic mocking in test
    mock_pal = MockPALWrapper(real_pal)
    # Inject wrapper into env_engine
    env_engine._pal = mock_pal
    
    # Configure event bus event loop
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)
    
    # Record all events published during the test
    captured_events: List[IEvent] = []
    async def event_recorder(event: IEvent) -> None:
        captured_events.append(event)
        print(f"RECORDER CAPTURED EVENT: {event.topic} from {event.source}")
        logger.info(f"Captured Event: {event.topic} from {event.source}")
        
    # Subscribe recorder synchronously in main thread to guarantee no missing early events
    event_bus.subscribe("environment.*", event_recorder)
    event_bus.subscribe("observation.*", event_recorder)
    
    # 4. Perform Topological Sorted Module Initialization and Start
    # Modules: observation_engine, environment_engine
    sorted_module_ids = registry.get_boot_order()
    sorted_modules = [registry.get_module(mid) for mid in sorted_module_ids]
    logger.info(f"Topological initialization order: {sorted_module_ids}")
    
    for module in sorted_modules:
        module.on_initialize()
        
    # Clear observation providers after initialization to avoid hooking real mouse/keyboard/audio
    obs_engine._providers = []
    obs_engine._provider_map = {}
        
    # Speed up polling loop interval in test by mocking stop_event.wait
    original_wait = env_engine._stop_event.wait
    env_engine._stop_event.wait = lambda timeout: original_wait(timeout=0.05)
        
    for module in sorted_modules:
        module.on_start()
    
    # Wait for startup events to register
    await asyncio.sleep(0.2)
    
    # Assert started events were published
    topics = [e.topic for e in captured_events]
    print(f"TEST TOPICS CAPTURED: {topics}")
    assert "observation.engine.started" in topics, "Observation Engine failed to publish started event."
    assert "environment.engine.started" in topics, "Environment Engine failed to publish started event."
    
    # 5. Verify Baseline Snapshot Construction
    snapshot = env_engine.get_snapshot()
    assert snapshot is not None
    assert snapshot.timestamp is not None
    logger.info(f"Baseline Snapshot timestamp: {snapshot.timestamp}")
    logger.info(f"Baseline Running Apps: {len(snapshot.running_applications)}")
    logger.info(f"Baseline Battery Status: {snapshot.battery_status}")
    logger.info(f"Baseline Network Status: {snapshot.network_status}")
    
    # 6. Simulate Event-Driven Update (active window change)
    captured_events.clear()
    mock_payload = {
        "hwnd": 99999,
        "title": "Override IDE Terminal",
        "pid": 1234,
        "bounds": {"left": 0, "top": 0, "right": 800, "bottom": 600, "width": 800, "height": 600},
        "class_name": "ConsoleWindowClass"
    }
    mock_pal.mock_active_window = mock_payload
    
    mock_window_event = Event(
        _topic="observation.window_changed",
        _source="observation_engine",
        _payload=mock_payload
    )
    logger.info("Publishing observation.window_changed event...")
    event_bus.publish(mock_window_event)
    
    # Give dispatcher loop time to process
    logger.info("Sleeping for 0.1s to let window change event process...")
    await asyncio.sleep(0.1)
    logger.info("Woke up from 0.1s sleep.")
    
    # Verify snapshot active window was updated and events published
    logger.info("Fetching updated snapshot...")
    updated_snapshot = env_engine.get_snapshot()
    logger.info("Snapshot fetched successfully.")
    assert updated_snapshot.active_window.get("hwnd") == 99999, "Snapshot active window was not updated event-driven."
    assert updated_snapshot.active_window.get("title") == "Override IDE Terminal"
    
    topics = [e.topic for e in captured_events]
    assert "environment.window_focused" in topics, "environment.window_focused event was not published."
    assert "environment.updated" in topics, "environment.updated event was not published."
    logger.info("Window focused assertions passed.")
    
    # 7. Simulate Polling Diff (application started/closed)
    captured_events.clear()
    
    # Set mock running apps list
    baseline_apps = list(updated_snapshot.running_applications)
    mock_app = {"pid": 9999, "name": "super_process.exe"}
    mock_pal.mock_running_apps = baseline_apps + [mock_app]
    
    # Wait for polling loop iteration
    logger.info("Sleeping 0.1s for polling loop to run...")
    await asyncio.sleep(0.1)
    logger.info("Woke up from polling sleep.")
    
    # Verify snapshot has the new process and event was published
    logger.info("Fetching snapshot after app added...")
    app_added_snapshot = env_engine.get_snapshot()
    logger.info("Snapshot after app added fetched.")
    app_pids = [app["pid"] for app in app_added_snapshot.running_applications]
    assert 9999 in app_pids, "Polling failed to add the new process."
    
    topics = [e.topic for e in captured_events]
    assert "environment.application_started" in topics, "environment.application_started event was not published."
    assert "environment.updated" in topics, "environment.updated event was not published."
    logger.info("App added assertions passed.")
    
    # Now simulate application closed
    captured_events.clear()
    mock_pal.mock_running_apps = baseline_apps
    
    await asyncio.sleep(0.1)
    
    app_removed_snapshot = env_engine.get_snapshot()
    app_pids_after = [app["pid"] for app in app_removed_snapshot.running_applications]
    assert 9999 not in app_pids_after, "Polling failed to remove the process."
    
    topics_after = [e.topic for e in captured_events]
    assert "environment.application_closed" in topics_after, "environment.application_closed event was not published."
    
    # 8. Shutdown and Cleanup
    logger.info("Stopping all engines in reverse order...")
    # Restore original wait before joining to prevent mock references during exit
    env_engine._stop_event.wait = original_wait
    
    for module in reversed(sorted_modules):
        module.on_stop()
        
    # Unsubscribe recorder
    event_bus.unsubscribe("environment.*", event_recorder)
    event_bus.unsubscribe("observation.*", event_recorder)
    
    # Stop event bus
    event_bus.stop()
    
    # Wait for thread cleanup
    await asyncio.sleep(0.2)
    
    final_threads = threading.active_count()
    final_tasks = len(asyncio.all_tasks())
    
    logger.info(f"Thread count delta (final - initial): {final_threads - initial_threads}")
    logger.info(f"Async task count delta (final - initial): {final_tasks - initial_tasks}")
    
    # Assert no leaks
    # (Allowing +1 thread if background worker clean up takes an extra split second, but ideally 0)
    assert final_threads - initial_threads <= 1, f"Thread leak detected! Delta: {final_threads - initial_threads}"
    assert final_tasks - initial_tasks == 0, f"Async task leak detected! Delta: {final_tasks - initial_tasks}"
    
    logger.info("=== ALL ENVIRONMENT ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    try:
        asyncio.run(run_integration_test())
    except AssertionError as e:
        logger.error(f"TEST ASSERTION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"TEST CRASHED: {e}", exc_info=True)
        sys.exit(1)
