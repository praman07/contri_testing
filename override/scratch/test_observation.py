import asyncio
import os
import sys
import logging

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.startup import boot_system
from override.runtime.bootstrap.shutdown import graceful_shutdown
from override.runtime.runtime.runtime import Runtime
from override.runtime.interfaces.event import IEventBus
from override.runtime.observation.engine import ObservationEngine

# Configure test logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.TestObservation")

async def main():
    logger.info("--- STEP 1: Initializing Service Container ---")
    container = initialize_container()
    runtime = Runtime()
    
    event_bus = container.resolve(IEventBus)
    
    # Track statistics of captured signals
    stats = {
        "screen": 0,
        "audio": 0,
        "window": 0,
        "filesystem": 0,
        "mouse_move": 0,
        "mouse_btn": 0,
        "keyboard": 0
    }

    # Define event handler callbacks
    async def handle_screen(event):
        stats["screen"] += 1
        payload = event.payload
        data_len = len(payload.get("data", ""))
        logger.info(f"[OBSERVATION] Screen Captured: size={data_len} chars (base64 BMP), format={payload.get('format')}")

    async def handle_audio(event):
        stats["audio"] += 1
        payload = event.payload
        logger.info(f"[OBSERVATION] Audio Captured: length={payload.get('data_length')} bytes, rate={payload.get('sample_rate')}Hz")

    async def handle_window(event):
        stats["window"] += 1
        payload = event.payload
        logger.info(f"[OBSERVATION] Active Window Changed: title='{payload.get('title')}' (PID={payload.get('pid')})")

    async def handle_filesystem(event):
        stats["filesystem"] += 1
        payload = event.payload
        logger.info(f"[OBSERVATION] Filesystem Change: type={payload.get('event_type')}, file={payload.get('filename')}")

    async def handle_mouse_move(event):
        stats["mouse_move"] += 1
        payload = event.payload
        # Log periodically to avoid flooding the console
        if stats["mouse_move"] % 20 == 1:
            logger.info(f"[OBSERVATION] Mouse Moved: x={payload.get('x')}, y={payload.get('y')} (Logged 1 in 20)")

    async def handle_mouse_btn(event):
        stats["mouse_btn"] += 1
        payload = event.payload
        logger.info(f"[OBSERVATION] Mouse Button Event: action={payload.get('action')} at x={payload.get('x')}, y={payload.get('y')}")

    async def handle_keyboard(event):
        stats["keyboard"] += 1
        payload = event.payload
        logger.info(f"[OBSERVATION] Keyboard Input: action={payload.get('action')}, vk_code={payload.get('vk_code')}")

    # Subscribe to Event Bus topics
    event_bus.subscribe("observation.screen_captured", handle_screen)
    event_bus.subscribe("observation.audio_captured", handle_audio)
    event_bus.subscribe("observation.window_changed", handle_window)
    event_bus.subscribe("observation.filesystem_changed", handle_filesystem)
    event_bus.subscribe("observation.mouse_moved", handle_mouse_move)
    event_bus.subscribe("observation.mouse_button", handle_mouse_btn)
    event_bus.subscribe("observation.keyboard_input", handle_keyboard)

    logger.info("--- STEP 2: Booting System ---")
    await boot_system(container, runtime)
    logger.info(f"System status: {runtime.get_status()}")

    # Let the observation run for 7 seconds to capture signal streams
    logger.info("--- STEP 3: Running Observation Stream (7 seconds) ---")
    logger.info("Try moving the mouse, pressing keys, or changing the active window now...")
    await asyncio.sleep(7.0)

    logger.info("--- STEP 4: Initiating Graceful Shutdown ---")
    graceful_shutdown(container, runtime)
    logger.info(f"Final Runtime status: {runtime.get_status()}")

    # Print final test results
    logger.info("--- FINAL STATS ---")
    for category, count in stats.items():
        logger.info(f"  {category.upper()}: {count} events captured")

    # Verify that we received at least some events (screen, window, etc.)
    if stats["screen"] > 0 or stats["window"] > 0:
        logger.info("SUCCESS: Signal collection verified!")
    else:
        logger.error("ERROR: No observation events were collected!")

if __name__ == "__main__":
    # Create configuration folder if missing
    os.makedirs("config", exist_ok=True)
    asyncio.run(main())
