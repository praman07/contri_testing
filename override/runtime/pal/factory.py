import platform
from override.runtime.pal.base import PlatformAbstractionLayer

def get_pal() -> PlatformAbstractionLayer:
    """
    Factory function to detect the host operating system and instantiate
    the appropriate Platform Abstraction Layer implementation.
    """
    sys_name = platform.system()
    if sys_name == "Windows":
        from override.runtime.pal.windows import WindowsPAL
        return WindowsPAL()
    elif sys_name == "Linux":
        from override.runtime.pal.linux import LinuxPAL
        return LinuxPAL()
    elif sys_name == "Darwin":
        from override.runtime.pal.macos import MacOSPAL
        return MacOSPAL()
    else:
        # Fallback to generic Linux-like stub
        from override.runtime.pal.linux import LinuxPAL
        return LinuxPAL()
