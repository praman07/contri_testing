import logging
from typing import Callable, Optional
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame

logger = logging.getLogger("Override.Observation.Camera")

class CameraProvider(IObservationProvider):
    """
    Stub camera provider for Layer 01.
    """

    def __init__(self, config):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False

    @property
    def provider_id(self) -> str:
        return "camera_capture"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        logger.info("Initializing Camera Capture Provider (Stub).")

    def start(self) -> None:
        self._running = True
        logger.info("Camera Capture Provider (Stub) started.")

    def stop(self) -> None:
        self._running = False
        logger.info("Camera Capture Provider (Stub) stopped.")
