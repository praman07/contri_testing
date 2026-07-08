import logging
import threading
import datetime
from typing import Dict, Any, List, Optional
from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.pal.base import PlatformAbstractionLayer
from override.runtime.config.config import ConfigurationManager
from override.runtime.environment.snapshot import EnvironmentSnapshot

logger = logging.getLogger("Override.Environment.Engine")

class EnvironmentEngine(OverrideModule):
    """
    Layer 02 — Environment Engine.
    Consumes Observation events and polls Platform Abstraction Layer (PAL) to maintain a live
    EnvironmentSnapshot. Publishes environment facts to the Event Bus.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        pal: PlatformAbstractionLayer,
        config: ConfigurationManager
    ):
        super().__init__("environment_engine")
        self._event_bus = event_bus
        self._pal = pal
        self._config = config
        
        self._lock = threading.RLock()
        self._current_snapshot: EnvironmentSnapshot = EnvironmentSnapshot()
        
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def get_snapshot(self) -> EnvironmentSnapshot:
        """Returns the current immutable EnvironmentSnapshot thread-safely."""
        with self._lock:
            return self._current_snapshot

    def on_initialize(self) -> None:
        logger.info("Initializing Environment Engine...")
        
        # Subscribe to Observation Engine event for active window changes
        self._event_bus.subscribe("observation.window_changed", self._on_window_changed)
        
        logger.info("Environment Engine initialized.")

    def on_start(self) -> None:
        logger.info("Starting Environment Engine...")
        self._stop_event.clear()
        
        try:
            logger.info("Environment Engine capturing baseline apps...")
            apps = self._pal.get_running_applications()
            logger.info("Environment Engine capturing baseline active window...")
            act = self._pal.get_active_window()
            logger.info("Environment Engine capturing baseline hierarchy...")
            hier = self._pal.get_window_hierarchy()
            logger.info("Environment Engine capturing baseline monitors...")
            mons = self._pal.get_monitor_layout()
            logger.info("Environment Engine capturing baseline clipboard...")
            clip = self._pal.get_clipboard_state()
            logger.info("Environment Engine capturing baseline devices...")
            devs = self._pal.get_connected_devices()
            logger.info("Environment Engine capturing baseline network...")
            net = self._pal.get_network_status()
            logger.info("Environment Engine capturing baseline battery...")
            bat = self._pal.get_battery_status()
            
            initial_snapshot = EnvironmentSnapshot(
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                running_applications=apps,
                active_window=act,
                window_hierarchy=hier,
                monitor_layout=mons,
                clipboard_state=clip,
                connected_devices=devs,
                network_status=net,
                battery_status=bat
            )
            with self._lock:
                self._current_snapshot = initial_snapshot
            logger.info("Captured initial baseline EnvironmentSnapshot successfully.")
        except Exception as e:
            logger.error(f"Failed to capture initial EnvironmentSnapshot: {e}", exc_info=True)
            
        # 2. Spawn background monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._environment_monitor_loop,
            name="Override.Environment.Monitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        # 3. Publish engine started event
        self._event_bus.publish(Event(
            _topic="environment.engine.started",
            _source="environment_engine",
            _payload={}
        ))
        
        logger.info("Environment Engine started successfully.")

    def on_stop(self) -> None:
        logger.info("Stopping Environment Engine...")
        
        # 1. Stop background monitoring thread
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
            logger.info("Environment Engine monitor thread joined.")
            
        # 2. Unsubscribe from events
        self._event_bus.unsubscribe("observation.window_changed", self._on_window_changed)
        
        # 3. Publish engine stopped event
        self._event_bus.publish(Event(
            _topic="environment.engine.stopped",
            _source="environment_engine",
            _payload={}
        ))
        
        logger.info("Environment Engine stopped.")

    async def _on_window_changed(self, event: IEvent) -> None:
        """Handles observation.window_changed to update snapshot instantaneously."""
        payload = event.payload
        new_active = {
            "hwnd": payload.get("hwnd", 0),
            "title": payload.get("title", ""),
            "pid": payload.get("pid", 0),
            "bounds": payload.get("bounds", {}),
            "class_name": payload.get("class_name", "")
        }
        
        with self._lock:
            old_active = self._current_snapshot.active_window
            if old_active.get("hwnd") != new_active.get("hwnd") or old_active.get("title") != new_active.get("title"):
                self._current_snapshot = EnvironmentSnapshot(
                    timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                    running_applications=self._current_snapshot.running_applications,
                    active_window=new_active,
                    window_hierarchy=self._current_snapshot.window_hierarchy,
                    monitor_layout=self._current_snapshot.monitor_layout,
                    clipboard_state=self._current_snapshot.clipboard_state,
                    connected_devices=self._current_snapshot.connected_devices,
                    network_status=self._current_snapshot.network_status,
                    battery_status=self._current_snapshot.battery_status
                )
                
                # Publish WindowFocused event (fact)
                self._event_bus.publish(Event(
                    _topic="environment.window_focused",
                    _source="environment_engine",
                    _payload=new_active
                ))
                
                # Publish EnvironmentUpdated event (fact)
                self._event_bus.publish(Event(
                    _topic="environment.updated",
                    _source="environment_engine",
                    _payload=self._current_snapshot.to_dict()
                ))
                logger.debug(f"Instantaneous active window update processed: {new_active.get('title')}")

    def _environment_monitor_loop(self) -> None:
        logger.info("Environment Engine background monitor loop started.")
        while not self._stop_event.is_set():
            try:
                # 1. Fetch state from PAL
                running_apps = self._pal.get_running_applications()
                active_win = self._pal.get_active_window()
                hierarchy = self._pal.get_window_hierarchy()
                monitors = self._pal.get_monitor_layout()
                clipboard = self._pal.get_clipboard_state()
                devices = self._pal.get_connected_devices()
                network = self._pal.get_network_status()
                battery = self._pal.get_battery_status()
                
                changed = False
                events_to_publish = []
                
                with self._lock:
                    prev = self._current_snapshot
                    
                    # A. Diff Running Applications
                    prev_pids = {app["pid"]: app["name"] for app in prev.running_applications}
                    curr_pids = {app["pid"]: app["name"] for app in running_apps}
                    
                    added_pids = set(curr_pids.keys()) - set(prev_pids.keys())
                    removed_pids = set(prev_pids.keys()) - set(curr_pids.keys())
                    
                    for pid in added_pids:
                        events_to_publish.append(Event(
                            _topic="environment.application_started",
                            _source="environment_engine",
                            _payload={"pid": pid, "name": curr_pids[pid]}
                        ))
                        changed = True
                        
                    for pid in removed_pids:
                        events_to_publish.append(Event(
                            _topic="environment.application_closed",
                            _source="environment_engine",
                            _payload={"pid": pid, "name": prev_pids[pid]}
                        ))
                        changed = True
                        
                    # B. Diff Active Window
                    if active_win and prev.active_window.get("hwnd") != active_win.get("hwnd"):
                        events_to_publish.append(Event(
                            _topic="environment.window_focused",
                            _source="environment_engine",
                            _payload=active_win
                        ))
                        changed = True
                    else:
                        active_win = prev.active_window
                        
                    # C. Diff Network
                    if prev.network_status.get("connected") != network.get("connected") or prev.network_status.get("type") != network.get("type"):
                        events_to_publish.append(Event(
                            _topic="environment.network_changed",
                            _source="environment_engine",
                            _payload=network
                        ))
                        changed = True
                        
                    # D. Diff Battery
                    if (prev.battery_status.get("percent") != battery.get("percent") or 
                            prev.battery_status.get("ac_status") != battery.get("ac_status") or 
                            prev.battery_status.get("charging") != battery.get("charging")):
                        events_to_publish.append(Event(
                            _topic="environment.battery_changed",
                            _source="environment_engine",
                            _payload=battery
                        ))
                        changed = True
                        
                    # E. Diff Connected Devices
                    prev_devs = {d["id"]: d for d in prev.connected_devices}
                    curr_devs = {d["id"]: d for d in devices}
                    
                    added_devs = set(curr_devs.keys()) - set(prev_devs.keys())
                    removed_devs = set(prev_devs.keys()) - set(curr_devs.keys())
                    
                    for dev_id in added_devs:
                        events_to_publish.append(Event(
                            _topic="environment.device_connected",
                            _source="environment_engine",
                            _payload=curr_devs[dev_id]
                        ))
                        changed = True
                        
                    for dev_id in removed_devs:
                        events_to_publish.append(Event(
                            _topic="environment.device_disconnected",
                            _source="environment_engine",
                            _payload=prev_devs[dev_id]
                        ))
                        changed = True
                        
                    # F. Diff Monitors
                    if (len(prev.monitor_layout) != len(monitors) or 
                            any(prev.monitor_layout[i].get("name") != monitors[i].get("name") for i in range(min(len(prev.monitor_layout), len(monitors))))):
                        events_to_publish.append(Event(
                            _topic="environment.monitor_changed",
                            _source="environment_engine",
                            _payload={"monitors": monitors}
                        ))
                        changed = True
                        
                    # G. Diff Clipboard & Hierarchy checks (do not trigger separate events in Layer 2 but trigger environment.updated)
                    if prev.clipboard_state.get("hash") != clipboard.get("hash"):
                        changed = True
                    if len(prev.window_hierarchy) != len(hierarchy):
                        changed = True
                        
                    # If anything changed, update current snapshot and append EnvironmentUpdated event
                    if changed:
                        self._current_snapshot = EnvironmentSnapshot(
                            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                            running_applications=running_apps,
                            active_window=active_win,
                            window_hierarchy=hierarchy,
                            monitor_layout=monitors,
                            clipboard_state=clipboard,
                            connected_devices=devices,
                            network_status=network,
                            battery_status=battery
                        )
                        events_to_publish.append(Event(
                            _topic="environment.updated",
                            _source="environment_engine",
                            _payload=self._current_snapshot.to_dict()
                        ))
                
                # Publish events outside of lock to prevent lock contention
                for event in events_to_publish:
                    self._event_bus.publish(event)
                    
            except Exception as e:
                logger.error(f"Error in Environment Engine polling loop: {e}", exc_info=True)
                
            self._stop_event.wait(timeout=3.0)
        logger.info("Environment Engine background monitor loop stopped.")
