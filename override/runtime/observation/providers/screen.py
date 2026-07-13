import os
import sys
import time
import base64
import struct
import threading
import logging
from datetime import datetime
from typing import Callable, Optional
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame
from override.runtime.config.config import ConfigurationManager

logger = logging.getLogger("Override.Observation.Screen")

# Define Windows GDI structures if running on Windows
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import ctypes
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', ctypes.c_uint32),
            ('biWidth', ctypes.c_int32),
            ('biHeight', ctypes.c_int32),
            ('biPlanes', ctypes.c_uint16),
            ('biBitCount', ctypes.c_uint16),
            ('biCompression', ctypes.c_uint32),
            ('biSizeImage', ctypes.c_uint32),
            ('biXPelsPerMeter', ctypes.c_int32),
            ('biYPelsPerMeter', ctypes.c_int32),
            ('biClrUsed', ctypes.c_uint32),
            ('biClrImportant', ctypes.c_uint32)
        ]

class ScreenProvider(IObservationProvider):
    """
    Captures screenshots at regular intervals.
    Uses native Windows GDI calls via ctypes for zero dependencies.
    """

    def __init__(self, config: ConfigurationManager):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        # Default sampling rate of 1 frame every 2.0 seconds
        self._interval = 2.0 
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "screen_capture"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        # Read interval from configuration if available
        # E.g. config.observation.screen_interval
        logger.info("Initializing Screen Capture Provider.")

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, name="ScreenCaptureThread", daemon=True)
            self._thread.start()
            logger.info("Screen Capture Provider started.")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("Screen Capture Provider stopped.")

    def _capture_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            
            try:
                t0 = time.time()
                bmp_bytes = self._grab_screen()
                if bmp_bytes and self._callback:
                    b64_data = base64.b64encode(bmp_bytes).decode("utf-8")
                    frame = ObservationFrame(
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        source=self.provider_id,
                        payload={
                            "format": "bmp",
                            "data": b64_data,
                            "encoding": "base64"
                        }
                    )
                    self._callback(frame)
            except Exception as e:
                logger.error(f"Error capturing screen: {e}", exc_info=True)

            # Sleep remaining time to maintain interval
            elapsed = time.time() - t0
            sleep_time = max(0.01, self._interval - elapsed)
            time.sleep(sleep_time)

    def _grab_screen(self) -> bytes:
        if not IS_WINDOWS:
            return self._grab_screen_fallback()

        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            # Use system metrics to find bounds
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)

            if width <= 0 or height <= 0:
                # Fallback if metrics are zero
                return self._grab_screen_fallback()

            hdc_screen = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)

            old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

            # SRCCOPY = 0x00CC0020
            gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020)

            # Retrieve pixels BGRA (32 bits)
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height # negative for top-down image
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0 # BI_RGB

            buffer_size = width * height * 4
            pixel_buffer = ctypes.create_string_buffer(buffer_size)

            # GetDIBits
            gdi32.GetDIBits(hdc_screen, hbmp, 0, height, pixel_buffer, ctypes.byref(bmi), 0)

            # Cleanup
            gdi32.SelectObject(hdc_mem, old_bmp)
            gdi32.DeleteObject(hbmp)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)

            # Build BMP file header and info header
            # File header (14 bytes): 'BM' (2 bytes), size (4 bytes), reserved (4 bytes), offset (4 bytes)
            file_header = struct.pack('<2sIHHI', b'BM', 14 + 40 + buffer_size, 0, 0, 14 + 40)
            info_header = struct.pack('<IiiHHIIIIII', 40, width, -height, 1, 32, 0, buffer_size, 0, 0, 0, 0)

            return file_header + info_header + pixel_buffer.raw
        except Exception as e:
            logger.error(f"Native Windows screen capture failed: {e}. Falling back.")
            return self._grab_screen_fallback()

    def _grab_screen_fallback(self) -> bytes:
        # Generates a tiny 1x1 green BMP to prevent failures on Linux/macOS
        width, height = 1, 1
        buffer_size = 4
        pixel_data = b'\x00\xff\x00\xff' # BGRA green
        file_header = struct.pack('<2sIHHI', b'BM', 14 + 40 + buffer_size, 0, 0, 14 + 40)
        info_header = struct.pack('<IiiHHIIIIII', 40, width, -height, 1, 32, 0, buffer_size, 0, 0, 0, 0)
        return file_header + info_header + pixel_data
