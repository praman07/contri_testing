import sys
import time
import threading
import logging
from datetime import datetime
from typing import Callable, Optional
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame
from override.runtime.config.config import ConfigurationManager

logger = logging.getLogger("Override.Observation.Input")

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    # Structure definitions
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", ctypes.c_uint32),
            ("scanCode", ctypes.c_uint32),
            ("flags", ctypes.c_uint32),
            ("time", ctypes.c_uint32),
            ("dwExtraInfo", ctypes.c_void_p)
        ]

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", POINT),
            ("mouseData", ctypes.c_uint32),
            ("flags", ctypes.c_uint32),
            ("time", ctypes.c_uint32),
            ("dwExtraInfo", ctypes.c_void_p)
        ]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint32),
            ("wParam", ctypes.c_uint64),
            ("lParam", ctypes.c_int64),
            ("time", ctypes.c_uint32),
            ("pt", POINT)
        ]

    # Hook callback type
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p)

class InputListenerProvider(IObservationProvider):
    """
    Listens to low-level keyboard and mouse events.
    Uses native Windows hooks (WH_KEYBOARD_LL, WH_MOUSE_LL) via ctypes.
    """

    def __init__(self, config: ConfigurationManager):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Windows-specific handles
        self._keyboard_hook = None
        self._mouse_hook = None
        self._kbd_callback_func = None
        self._mouse_callback_func = None

    @property
    def provider_id(self) -> str:
        return "input_listener"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        logger.info("Initializing Input Listener Provider.")

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._hook_loop, name="InputHookThread", daemon=True)
            self._thread.start()
            logger.info("Input Listener Provider started.")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("Input Listener Provider stopped.")

    def _hook_loop(self) -> None:
        if not IS_WINDOWS:
            logger.info("Non-Windows platform detected; Input Listener running in stub mode.")
            while True:
                with self._lock:
                    if not self._running:
                        break
                time.sleep(0.5)
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Configure ctypes argument and return types to prevent 64-bit truncation
        kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_uint32]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        user32.UnhookWindowsHookEx.restype = ctypes.c_bool

        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p]
        user32.CallNextHookEx.restype = ctypes.c_longlong


        # Define hook callbacks inside loop to ensure reference persistence during run
        def keyboard_proc(code, wparam, lparam):
            if code >= 0 and self._callback:
                try:
                    kb_struct = KBDLLHOOKSTRUCT.from_address(lparam)
                    event_type = "keydown" if wparam in (0x100, 0x104) else "keyup"
                    frame = ObservationFrame(
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        source=self.provider_id,
                        payload={
                            "type": "keyboard",
                            "action": event_type,
                            "vk_code": kb_struct.vkCode,
                            "scan_code": kb_struct.scanCode,
                            "flags": kb_struct.flags
                        }
                    )
                    self._callback(frame)
                except Exception as ex:
                    logger.error(f"Error handling keyboard hook: {ex}")
            return user32.CallNextHookEx(0, code, wparam, lparam)

        def mouse_proc(code, wparam, lparam):
            if code >= 0 and self._callback:
                try:
                    ms_struct = MSLLHOOKSTRUCT.from_address(lparam)
                    event_name = "move"
                    if wparam == 0x0201: event_name = "left_down"
                    elif wparam == 0x0202: event_name = "left_up"
                    elif wparam == 0x0204: event_name = "right_down"
                    elif wparam == 0x0205: event_name = "right_up"
                    elif wparam == 0x0207: event_name = "middle_down"
                    elif wparam == 0x0208: event_name = "middle_up"
                    elif wparam == 0x020A: event_name = "wheel"

                    frame = ObservationFrame(
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        source=self.provider_id,
                        payload={
                            "type": "mouse",
                            "action": event_name,
                            "x": ms_struct.pt.x,
                            "y": ms_struct.pt.y,
                            "mouse_data": ms_struct.mouseData
                        }
                    )
                    self._callback(frame)
                except Exception as ex:
                    logger.error(f"Error handling mouse hook: {ex}")
            return user32.CallNextHookEx(0, code, wparam, lparam)

        # Retain references to callback functions so GC doesn't clean them up
        self._kbd_callback_func = HOOKPROC(keyboard_proc)
        self._mouse_callback_func = HOOKPROC(mouse_proc)

        # Initialize thread message queue by peeking
        msg = MSG()
        user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 0)

        # Use kernel32.dll handle which is guaranteed to be loaded
        h_mod = kernel32.GetModuleHandleW("kernel32.dll")
        self._keyboard_hook = user32.SetWindowsHookExW(13, self._kbd_callback_func, h_mod, 0)
        self._mouse_hook = user32.SetWindowsHookExW(14, self._mouse_callback_func, h_mod, 0)

        if not self._keyboard_hook or not self._mouse_hook:
            err = kernel32.GetLastError()
            logger.error(f"Failed to install native input hooks! Error code: {err}")
            self._cleanup_hooks()
            return

        logger.info("Native input hooks installed successfully.")


        msg = MSG()
        # Non-blocking peek message pump to allow clean termination checking
        while True:
            with self._lock:
                if not self._running:
                    break
            
            # PM_REMOVE = 0x0001
            if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)

        self._cleanup_hooks()
        logger.info("Native input hooks cleaned up successfully.")

    def _cleanup_hooks(self) -> None:
        if not IS_WINDOWS:
            return
        user32 = ctypes.windll.user32
        if self._keyboard_hook:
            user32.UnhookWindowsHookEx(self._keyboard_hook)
            self._keyboard_hook = None
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        self._kbd_callback_func = None
        self._mouse_callback_func = None
