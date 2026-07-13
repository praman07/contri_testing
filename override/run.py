"""
Override Cognitive Runtime — Main Entry Point

Boots the full runtime stack (Layers 00–10), wires the async event bus,
and keeps the process alive until Ctrl+C triggers a graceful shutdown.
"""

import asyncio
import logging
import signal
import sys
import os

# Ensure repo root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.startup import boot_system
from override.runtime.bootstrap.shutdown import graceful_shutdown
from override.runtime.runtime.runtime import Runtime

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Override.Main")

# ─── Entrypoint ──────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("=" * 60)
    logger.info("  Override Cognitive Runtime")
    logger.info("  Layers 00–10 | Booting...")
    logger.info("=" * 60)

    container = initialize_container()
    runtime   = Runtime()

    # Register graceful shutdown on SIGINT / SIGTERM
    stop_event = asyncio.Event()

    def _request_stop():
        logger.info("Shutdown signal received. Stopping...")
        stop_event.set()

    loop = asyncio.get_running_loop()

    # Windows doesn't support add_signal_handler — use signal.signal instead
    if sys.platform == "win32":
        signal.signal(signal.SIGINT,  lambda *_: loop.call_soon_threadsafe(_request_stop))
        signal.signal(signal.SIGTERM, lambda *_: loop.call_soon_threadsafe(_request_stop))
    else:
        loop.add_signal_handler(signal.SIGINT,  _request_stop)
        loop.add_signal_handler(signal.SIGTERM, _request_stop)

    try:
        await boot_system(container, runtime)

        logger.info("=" * 60)
        logger.info("  Override is RUNNING. Press Ctrl+C to stop.")
        logger.info("=" * 60)

        # Keep process alive until shutdown is requested
        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
    finally:
        logger.info("Running graceful shutdown...")
        graceful_shutdown(container, runtime)
        logger.info("Override shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
