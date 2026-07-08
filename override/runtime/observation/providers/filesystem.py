import os
import time
import threading
import logging
from datetime import datetime
from typing import Callable, Dict, Optional, Set
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame
from override.runtime.config.config import ConfigurationManager

logger = logging.getLogger("Override.Observation.Filesystem")

class FilesystemProvider(IObservationProvider):
    """
    Watches files within the workspace for creations, updates, or deletions.
    Uses efficient directory scanning to support cross-platform execution without watchdog.
    """

    def __init__(self, config: ConfigurationManager):
        self._config = config
        self._callback: Optional[Callable[[ObservationFrame], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Watch configuration
        self._watch_dir = os.path.abspath(".")
        self._scan_interval = 2.0  # Scan every 2 seconds
        self._max_files = 1000      # Safety cap
        
        # State tracking
        self._file_state: Dict[str, float] = {}

    @property
    def provider_id(self) -> str:
        return "filesystem_watcher"

    def register_callback(self, callback: Callable[[ObservationFrame], None]) -> None:
        self._callback = callback

    def initialize(self) -> None:
        logger.info(f"Initializing Filesystem Watcher on directory: {self._watch_dir}")
        # Initial scan to populate baseline state
        self._file_state = self._scan_directory()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._watch_loop, name="FilesystemWatcherThread", daemon=True)
            self._thread.start()
            logger.info("Filesystem Watcher Provider started.")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("Filesystem Watcher Provider stopped.")

    def _watch_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            
            try:
                current_state = self._scan_directory()
                self._diff_and_dispatch(current_state)
            except Exception as e:
                logger.error(f"Error scanning directory changes: {e}")

            time.sleep(self._scan_interval)

    def _scan_directory(self) -> Dict[str, float]:
        state: Dict[str, float] = {}
        count = 0
        
        for root, dirs, files in os.walk(self._watch_dir):
            # Prune hidden folders and build folders (like .git, config, override/brain, etc)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "build", "dist", "node_modules")]
            
            for file in files:
                if count >= self._max_files:
                    break
                
                path = os.path.join(root, file)
                try:
                    state[path] = os.path.getmtime(path)
                    count += 1
                except (OSError, FileNotFoundError):
                    # File might have been deleted/moved during scan
                    continue
            
            if count >= self._max_files:
                break
                
        return state

    def _diff_and_dispatch(self, current: Dict[str, float]) -> None:
        old_keys = set(self._file_state.keys())
        new_keys = set(current.keys())
        
        created = new_keys - old_keys
        deleted = old_keys - new_keys
        modified = set()
        
        for k in (old_keys & new_keys):
            if current[k] != self._file_state[k]:
                modified.add(k)
        
        # Dispatch events
        for path in created:
            self._dispatch_change("file_created", path)
            
        for path in modified:
            self._dispatch_change("file_modified", path)
            
        for path in deleted:
            self._dispatch_change("file_deleted", path)
            
        # Update baseline state
        self._file_state = current

    def _dispatch_change(self, event_type: str, path: str) -> None:
        if self._callback:
            frame = ObservationFrame(
                timestamp=datetime.utcnow().isoformat() + "Z",
                source=self.provider_id,
                payload={
                    "event_type": event_type,
                    "path": path,
                    "filename": os.path.basename(path)
                }
            )
            self._callback(frame)
        logger.debug(f"Filesystem change: {event_type} -> {path}")
