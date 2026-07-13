import logging
from typing import Dict, List, Optional
from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.event import IEventBus
from override.runtime.event.event import Event
from override.runtime.pal.base import PlatformAbstractionLayer
from override.runtime.config.config import ConfigurationManager
from override.runtime.observation.frame import ObservationFrame
from override.runtime.observation.providers import (
    IObservationProvider,
    ScreenProvider,
    AudioProvider,
    InputListenerProvider,
    WindowProvider,
    FilesystemProvider,
    CameraProvider,
    DeviceProvider
)

logger = logging.getLogger("Override.Observation.Engine")

class ObservationEngine(OverrideModule):
    """
    Cognitive layer module orchestrating environmental signal captures.
    Coordinates all observation providers and dispatches raw observations to the Event Bus.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        pal: PlatformAbstractionLayer,
        config: ConfigurationManager
    ):
        super().__init__("observation_engine")
        self._event_bus = event_bus
        self._pal = pal
        self._config = config
        self._providers: List[IObservationProvider] = []
        self._provider_map: Dict[str, IObservationProvider] = {}

    def on_initialize(self) -> None:
        logger.info("Initializing Observation Engine...")

        # Instantiate all known observation providers
        self._providers = [
            ScreenProvider(self._config),
            AudioProvider(self._config),
            InputListenerProvider(self._config),
            WindowProvider(self._config),
            FilesystemProvider(self._config),
            CameraProvider(self._config),
            DeviceProvider(self._config)
        ]

        self._provider_map = {p.provider_id: p for p in self._providers}

        # Initialize and register callback on each provider
        for provider in self._providers:
            provider.register_callback(self._on_frame_captured)
            try:
                provider.initialize()
                logger.info(f"Initialized provider: {provider.provider_id}")
            except Exception as e:
                logger.error(f"Error initializing provider '{provider.provider_id}': {e}", exc_info=True)

        logger.info("Observation Engine initialization complete.")

    def on_start(self) -> None:
        logger.info("Starting Observation Engine providers...")
        for provider in self._providers:
            try:
                provider.start()
                logger.info(f"Started provider: {provider.provider_id}")
            except Exception as e:
                logger.error(f"Error starting provider '{provider.provider_id}': {e}", exc_info=True)
        logger.info("Observation Engine providers started.")
        try:
            self._event_bus.publish(Event(
                _topic="observation.engine.started",
                _source="observation_engine",
                _payload={}
            ))
        except Exception as e:
            logger.error(f"Failed to publish started event: {e}")

    def on_stop(self) -> None:
        logger.info("Stopping Observation Engine providers...")
        for provider in self._providers:
            try:
                provider.stop()
                logger.info(f"Stopped provider: {provider.provider_id}")
            except Exception as e:
                logger.error(f"Error stopping provider '{provider.provider_id}': {e}", exc_info=True)
        logger.info("Observation Engine providers stopped.")
        try:
            self._event_bus.publish(Event(
                _topic="observation.engine.stopped",
                _source="observation_engine",
                _payload={}
            ))
        except Exception as e:
            logger.error(f"Failed to publish stopped event: {e}")


    def get_providers(self) -> List[IObservationProvider]:
        """Returns all registered providers."""
        return list(self._providers)

    def get_provider(self, provider_id: str) -> Optional[IObservationProvider]:
        """Resolves a provider by its unique identifier."""
        return self._provider_map.get(provider_id)

    def register_provider(self, provider: IObservationProvider) -> None:
        """Dynamically registers an observation provider."""
        self._providers.append(provider)
        self._provider_map[provider.provider_id] = provider


    def _on_frame_captured(self, frame: ObservationFrame) -> None:
        """Callback invoked when any provider captures environment signals."""
        # Map provider source identifier to Event Bus topic
        topic = "observation.generic"
        
        if frame.source == "screen_capture":
            topic = "observation.screen_captured"
        elif frame.source == "audio_capture":
            topic = "observation.audio_captured"
        elif frame.source == "window_tracker":
            topic = "observation.window_changed"
        elif frame.source == "filesystem_watcher":
            topic = "observation.filesystem_changed"
        elif frame.source == "input_listener":
            # Map based on input type
            payload_type = frame.payload.get("type")
            if payload_type == "mouse":
                # Only dispatch mouse move events if they represent button events or discrete actions 
                # (or always dispatch if required. To prevent event flooding, we can route movements 
                # as mouse_moved and click events as mouse_button).
                action = frame.payload.get("action")
                if action == "move":
                    topic = "observation.mouse_moved"
                else:
                    topic = "observation.mouse_button"
            elif payload_type == "keyboard":
                topic = "observation.keyboard_input"

        try:
            # Package observation frame payload into an Event
            event = Event(
                _topic=topic,
                _source=frame.source,
                _payload=frame.payload
            )
            # Dispatch event onto the Event Bus asynchronously
            self._event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish observation event on topic '{topic}': {e}")
