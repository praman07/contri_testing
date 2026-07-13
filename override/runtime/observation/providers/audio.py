import time
import threading
import logging
import numpy as np
from datetime import datetime
from typing import Callable, Optional
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame
from override.runtime.config.config import ConfigurationManager

logger = logging.getLogger("Override.Observation.Audio")

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

class AudioProvider(IObservationProvider):
    """
    Captures raw microphone audio chunks using sounddevice if available.
    Normalizes sample rate and channel sizes, failing back gracefully to stubs.
    """

    def __init__(self, config: ConfigurationManager):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False
        self._stream: Optional[Any] = None
        self._sample_rate = 16000  # Default 16kHz
        self._channels = 1        # Default Mono
        self._block_duration_ms = 1000  # Emit audio frames every 1 second
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stub_thread: Optional[threading.Thread] = None

    @property
    def provider_id(self) -> str:
        return "audio_capture"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        logger.info("Initializing Audio Capture Provider.")

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._buffer.clear()

        if HAS_SOUNDDEVICE:
            try:
                # Open non-blocking input stream
                self._stream = sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=self._channels,
                    dtype='int16',
                    callback=self._audio_callback
                )
                self._stream.start()
                logger.info("Audio stream started successfully using sounddevice.")
                return
            except Exception as e:
                logger.warning(f"Failed to start sounddevice stream: {e}. Using silent audio stub.")
        
        # Fallback to stub loop (emits silent buffers)
        self._stub_thread = threading.Thread(target=self._stub_loop, name="AudioStubThread", daemon=True)
        self._stub_thread.start()
        logger.info("Audio stub provider active.")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing sounddevice stream: {e}")
            self._stream = None

        if self._stub_thread:
            self._stub_thread.join(timeout=2.0)
            self._stub_thread = None

        logger.info("Audio Capture Provider stopped.")

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning(f"Audio stream status warning: {status}")
        
        with self._lock:
            if not self._running:
                return
            
            # indata is a numpy array of shape (frames, channels)
            self._buffer.extend(indata.tobytes())
            
            # Check if block duration threshold reached
            # 2 bytes per sample (int16) * sample_rate * channels * duration_in_sec
            bytes_needed = int(2 * self._sample_rate * self._channels * (self._block_duration_ms / 1000.0))
            if len(self._buffer) >= bytes_needed:
                chunk = bytes(self._buffer[:bytes_needed])
                del self._buffer[:bytes_needed]
                self._dispatch_chunk(chunk)

    def _dispatch_chunk(self, raw_bytes: bytes) -> None:
        if self._callback:
            frame = ObservationFrame(
                timestamp=datetime.utcnow().isoformat() + "Z",
                source=self.provider_id,
                payload={
                    "sample_rate": self._sample_rate,
                    "channels": self._channels,
                    "format": "pcm_s16le",
                    "data_length": len(raw_bytes),
                    "raw_bytes": raw_bytes
                }
            )
            self._callback(frame)

    def _stub_loop(self) -> None:
        block_sec = self._block_duration_ms / 1000.0
        # Calculate size of silent frame
        sample_count = int(self._sample_rate * self._channels * block_sec)
        silent_data = b'\x00' * (sample_count * 2) # int16 is 2 bytes

        while True:
            with self._lock:
                if not self._running:
                    break
            
            t0 = time.time()
            self._dispatch_chunk(silent_data)
            
            # Precision sleep
            elapsed = time.time() - t0
            sleep_time = max(0.01, block_sec - elapsed)
            time.sleep(sleep_time)
