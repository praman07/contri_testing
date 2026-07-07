import threading
from typing import Set, Dict
from override.runtime.runtime.state import RuntimeState

class LifecycleManager:
    """
    Enforces deterministic state transitions for the Override runtime.
    Guarantees thread-safe updates and prevents illegal state hops.
    """

    def __init__(self, initial_state: RuntimeState = RuntimeState.BOOTING):
        self._state = initial_state
        self._lock = threading.RLock()

        # Define valid transitions
        self._transitions: Dict[RuntimeState, Set[RuntimeState]] = {
            RuntimeState.BOOTING: {RuntimeState.INITIALIZING, RuntimeState.STOPPING},
            RuntimeState.INITIALIZING: {RuntimeState.READY, RuntimeState.STOPPING},
            RuntimeState.READY: {RuntimeState.RUNNING, RuntimeState.STOPPING},
            RuntimeState.RUNNING: {RuntimeState.PAUSED, RuntimeState.STOPPING},
            RuntimeState.PAUSED: {RuntimeState.RUNNING, RuntimeState.STOPPING},
            RuntimeState.STOPPING: {RuntimeState.STOPPED},
            RuntimeState.STOPPED: set()
        }

    def get_state(self) -> RuntimeState:
        with self._lock:
            return self._state

    def transition_to(self, target_state: RuntimeState) -> None:
        """
        Attempts to transition the runtime state.
        Raises ValueError if the transition is illegal.
        """
        with self._lock:
            current = self._state
            if target_state == current:
                return

            valid_targets = self._transitions.get(current, set())
            if target_state not in valid_targets:
                raise ValueError(
                    f"Illegal lifecycle state transition: {current.name} -> {target_state.name}"
                )
            
            self._state = target_state
