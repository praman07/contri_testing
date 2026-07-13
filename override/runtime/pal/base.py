import sys
from abc import ABC, abstractmethod
from typing import Dict, Any

class PlatformAbstractionLayer(ABC):
    """
    Abstract Base Class for the Platform Abstraction Layer (PAL).
    Isolates Override cognitive runtime from operating-system-specific calls.
    """

    @abstractmethod
    def get_os_name(self) -> str:
        """Returns the operating system name (e.g., 'Windows', 'Linux', 'Darwin')."""
        pass

    @abstractmethod
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Returns a dictionary containing platform information:
        - os_name
        - os_version
        - architecture
        - cpu_count
        - total_memory_bytes
        - python_version
        """
        pass

    @abstractmethod
    def is_admin(self) -> bool:
        """Returns True if the current process runs with elevated/administrative privileges."""
        pass

    @abstractmethod
    def check_capability(self, capability: str) -> bool:
        """
        Checks if a specific OS capability is available:
        - 'screen_capture': Screen capturing capabilities
        - 'audio_input': Microphone/audio capture devices
        - 'audio_output': Speakers/sound reproduction devices
        - 'notifications': System tray notification capabilities
        """
        pass

    @abstractmethod
    def get_running_applications(self) -> list:
        """Returns a list of dictionaries representing running applications."""
        pass

    @abstractmethod
    def get_active_window(self) -> dict:
        """Returns details about the active/focused window."""
        pass

    @abstractmethod
    def get_window_hierarchy(self) -> list:
        """Returns the flat hierarchy/list of visible windows."""
        pass

    @abstractmethod
    def get_monitor_layout(self) -> list:
        """Returns details about connected monitor screens."""
        pass

    @abstractmethod
    def get_clipboard_state(self) -> dict:
        """Returns details of the clipboard content (type, length, hash)."""
        pass

    @abstractmethod
    def get_connected_devices(self) -> list:
        """Returns details about connected peripheral/storage devices."""
        pass

    @abstractmethod
    def get_network_status(self) -> dict:
        """Returns connection status and details."""
        pass

    @abstractmethod
    def get_battery_status(self) -> dict:
        """Returns details about battery/AC line power."""
        pass

