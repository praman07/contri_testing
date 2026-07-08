import sys
import time
import threading
import logging
from datetime import datetime
from typing import Callable, Optional
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame
from override.runtime.config.config import ConfigurationManager

logger = logging.getLogger("Override.Observation.Window")

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes

class WindowProvider(IObservationProvider):
    """
    Tracks the active/foreground window in the OS.
    Uses native Windows APIs (GetForegroundWindow, GetWindowTextW) via ctypes.
    """

    def __init__(self, config: ConfigurationManager):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._poll_interval = 0.25  # Check every 250ms
        self._last_hwnd = None
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "window_tracker"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        logger.info("Initializing Active Window Provider.")

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._last_hwnd = None
            self._thread = threading.Thread(target=self._poll_loop, name="WindowTrackerThread", daemon=True)
            self._thread.start()
            logger.info("Active Window Provider started.")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Active Window Provider stopped.")

    def _poll_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            
            try:
                self._check_active_window()
            except Exception as e:
                logger.error(f"Error checking active window: {e}")

            time.sleep(self._poll_interval)

    def _check_active_window(self) -> None:
        if not IS_WINDOWS:
            # Fallback for non-Windows (stub mode)
            # Just emit a stub frame once to verify routing
            if self._last_hwnd is None:
                self._last_hwnd = 9999
                self._dispatch_window_change(9999, "Mock Foreground Window", 0)
            return

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        if hwnd != self._last_hwnd:
            self._last_hwnd = hwnd
            
            # Fetch window title
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
            else:
                title = ""

            # Fetch process ID
            pid = ctypes.c_uint32()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            self._dispatch_window_change(hwnd, title, pid.value)

    def _dispatch_window_change(self, hwnd: int, title: str, pid: int) -> None:
        if self._callback:
            frame = ObservationFrame(
                timestamp=datetime.utcnow().isoformat() + "Z",
                source=self.provider_id,
                payload={
                    "hwnd": hwnd,
                    "title": title,
                    "pid": pid
                }
            )
            self._callback(frame)
