import os
import sys
import platform
import subprocess
from typing import Dict, Any
from override.runtime.pal.base import PlatformAbstractionLayer

class MacOSPAL(PlatformAbstractionLayer):
    """macOS-specific Platform Abstraction Layer stub."""

    def get_os_name(self) -> str:
        return "Darwin"

    def get_platform_info(self) -> Dict[str, Any]:
        return {
            "os_name": self.get_os_name(),
            "os_version": platform.mac_ver()[0] or platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count() or 0,
            "total_memory_bytes": self._get_total_memory(),
            "python_version": sys.version.split()[0],
            "is_admin": self.is_admin()
        }

    def is_admin(self) -> bool:
        try:
            return os.geteuid() == 0
        except Exception:
            return False

    def check_capability(self, capability: str) -> bool:
        if capability in ("screen_capture", "audio_input", "audio_output", "notifications"):
            return True
        return False

    def _get_total_memory(self) -> int:
        try:
            # Query sysctl for physical memory size
            output = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
        except Exception:
            pass
        return 0

    def get_running_applications(self) -> list:
        return []

    def get_active_window(self) -> dict:
        return {}

    def get_window_hierarchy(self) -> list:
        return []

    def get_monitor_layout(self) -> list:
        return []

    def get_clipboard_state(self) -> dict:
        return {"type": "empty", "length": 0, "hash": 0}

    def get_connected_devices(self) -> list:
        return []

    def get_network_status(self) -> dict:
        return {"connected": True, "type": "lan/wifi"}

    def get_battery_status(self) -> dict:
        return {"ac_status": "online", "percent": 100, "charging": False}

