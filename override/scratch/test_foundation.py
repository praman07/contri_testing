import asyncio
import os
import sys

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.startup import boot_system
from override.runtime.bootstrap.shutdown import graceful_shutdown
from override.runtime.runtime.runtime import Runtime
from override.runtime.interfaces.event import IEventBus
from override.runtime.event.event import Event
from override.runtime.health.monitor import HealthMonitor

async def main():
    print("--- STEP 1: Initializing Service Container ---")
    container = initialize_container()
    runtime = Runtime()
    
    print("--- STEP 2: Testing Early Event Buffering ---")
    event_bus = container.resolve(IEventBus)
    early_received = asyncio.Event()

    async def early_callback(event):
        print(f"Early callback received: topic='{event.topic}' payload={event.payload}")
        early_received.set()

    event_bus.subscribe("boot.early", early_callback)

    # Publish event before boot_system (no event loop active yet)
    early_event = Event(_topic="boot.early", _source="TestScript", _payload={"message": "Buffered event test"})
    event_bus.publish(early_event)

    print("--- STEP 3: Booting System ---")
    await boot_system(container, runtime)
    print(f"Runtime status: {runtime.get_status()}")

    print("Waiting for early event dispatch...")
    try:
        await asyncio.wait_for(early_received.wait(), timeout=2.0)
        print("Early event successfully recovered and processed!")
    except asyncio.TimeoutError:
        print("ERROR: Early event recovery timed out!")

    print("--- STEP 4: Testing Event Bus ---")
    event_bus = container.resolve(IEventBus)
    event_received = asyncio.Event()

    async def sample_callback(event):
        print(f"Callback received event: topic='{event.topic}' source='{event.source}' payload={event.payload}")
        event_received.set()

    # Subscribe to test topic
    event_bus.subscribe("test.topic", sample_callback)

    # Publish an event
    test_event = Event(_topic="test.topic", _source="TestScript", _payload={"message": "Hello from Override Foundation!"})
    event_bus.publish(test_event)

    print("Waiting for event dispatch...")
    try:
        await asyncio.wait_for(event_received.wait(), timeout=2.0)
        print("Event successfully routed and handled!")
    except asyncio.TimeoutError:
        print("ERROR: Event routing timed out!")

    print("--- STEP 5: Checking Health Monitor ---")
    health_mon = container.resolve(HealthMonitor)
    print(f"System Health Status: {health_mon.get_status().name}")
    metrics = health_mon.get_metrics()
    print(f"Resource Usage: CPU={metrics.cpu_percent}%, Threads={metrics.thread_count}")

    print("--- STEP 6: Initiating Graceful Shutdown ---")
    graceful_shutdown(container, runtime)
    print(f"Final Runtime status: {runtime.get_status()}")

if __name__ == "__main__":
    # Create configuration folder if missing
    os.makedirs("config", exist_ok=True)
    asyncio.run(main())
