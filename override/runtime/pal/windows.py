import os
import sys
import platform
import ctypes
from typing import Dict, Any
from override.runtime.pal.base import PlatformAbstractionLayer

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

class WindowsPAL(PlatformAbstractionLayer):
    """Windows-specific Platform Abstraction Layer implementation."""

    def __init__(self):
        super().__init__()
        # Enforce 64-bit safe ctypes definitions
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        
        # CreateToolhelp32Snapshot
        kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
        kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
        
        # CloseHandle
        kernel32.CloseHandle.restype = ctypes.c_bool
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        
        # GetForegroundWindow
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetForegroundWindow.argtypes = []
        
        # GetWindowTextLengthW
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        
        # GetWindowTextW
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        
        # GetWindowThreadProcessId
        user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
        user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        
        # GetWindowRect
        user32.GetWindowRect.restype = ctypes.c_bool
        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        
        # GetClassNameW
        user32.GetClassNameW.restype = ctypes.c_int
        user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        
        # IsWindowVisible
        user32.IsWindowVisible.restype = ctypes.c_bool
        user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        
        # GetMonitorInfoW
        user32.GetMonitorInfoW.restype = ctypes.c_bool
        user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        
        # OpenClipboard
        user32.OpenClipboard.restype = ctypes.c_bool
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]

    def get_os_name(self) -> str:
        return "Windows"

    def get_platform_info(self) -> Dict[str, Any]:
        info = {
            "os_name": self.get_os_name(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count() or 0,
            "total_memory_bytes": self._get_total_memory(),
            "python_version": sys.version.split()[0],
            "is_admin": self.is_admin()
        }
        return info

    def is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def check_capability(self, capability: str) -> bool:
        # Platform support abstractions
        if capability == "screen_capture":
            # Windows always supports screen capture natively
            return True
        elif capability == "audio_input":
            # Verify if audio input device detection is successful
            return self._has_audio_device(input_device=True)
        elif capability == "audio_output":
            return self._has_audio_device(input_device=False)
        elif capability == "notifications":
            # Native Windows notifications are supported
            return True
        return False

    def _get_total_memory(self) -> int:
        try:
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return stat.ullTotalPhys
        except Exception:
            pass
        return 0

    def _has_audio_device(self, input_device: bool) -> bool:
        # Check using sounddevice library if available, otherwise assume True on host standard windows
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for dev in devices:
                if input_device and dev["max_input_channels"] > 0:
                    return True
                if not input_device and dev["max_output_channels"] > 0:
                    return True
        except Exception:
            # Fallback check: on Windows, if PyAudio/sounddevice isn't set up yet,
            # we default to True since Windows OS has native audio subsystems.
            return True
        return False

    def get_running_applications(self) -> list:
        # Enumerate all processes via Toolhelp snapshot
        processes = []
        TH32CS_SNAPPROCESS = 0x00000002
        hSnapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if hSnapshot == -1:
            return []
        
        try:
            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", ctypes.c_ulong),
                    ("cntUsage", ctypes.c_ulong),
                    ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong),
                    ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", ctypes.c_ulong),
                    ("szExeFile", ctypes.c_wchar * 260)
                ]
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if ctypes.windll.kernel32.Process32FirstW(hSnapshot, ctypes.byref(pe)):
                while True:
                    processes.append({
                        "pid": pe.th32ProcessID,
                        "name": pe.szExeFile
                    })
                    if not ctypes.windll.kernel32.Process32NextW(hSnapshot, ctypes.byref(pe)):
                        break
        except Exception:
            pass
        finally:
            ctypes.windll.kernel32.CloseHandle(hSnapshot)
        return processes

    def get_active_window(self) -> dict:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {}
        
        # Title
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            
        # Process ID
        pid = ctypes.c_uint32()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        # Bounds
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        bounds = {
            "left": rect.left,
            "top": rect.top,
            "right": rect.right,
            "bottom": rect.bottom,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top
        }
        
        # Class Name
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value
        
        return {
            "hwnd": hwnd,
            "title": title,
            "pid": pid.value,
            "bounds": bounds,
            "class_name": class_name
        }

    def get_window_hierarchy(self) -> list:
        windows = []
        user32 = ctypes.windll.user32
        
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
            
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        
        def foreach_window(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                
                pid = ctypes.c_uint32()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                bounds = {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top
                }
                
                class_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buf, 256)
                class_name = class_buf.value
                
                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "pid": pid.value,
                    "bounds": bounds,
                    "class_name": class_name
                })
            return True
            
        EnumWindows(EnumWindowsProc(foreach_window), 0)
        return windows

    def get_monitor_layout(self) -> list:
        monitors = []
        user32 = ctypes.windll.user32
        
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
            
        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
                ("szDevice", ctypes.c_wchar * 32)
            ]
            
        EnumDisplayMonitors = user32.EnumDisplayMonitors
        MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
        
        def foreach_monitor(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                is_primary = (info.dwFlags & 1) != 0
                monitors.append({
                    "name": info.szDevice,
                    "bounds": {
                        "left": info.rcMonitor.left,
                        "top": info.rcMonitor.top,
                        "right": info.rcMonitor.right,
                        "bottom": info.rcMonitor.bottom,
                        "width": info.rcMonitor.right - info.rcMonitor.left,
                        "height": info.rcMonitor.bottom - info.rcMonitor.top
                    },
                    "work_area": {
                        "left": info.rcWork.left,
                        "top": info.rcWork.top,
                        "right": info.rcWork.right,
                        "bottom": info.rcWork.bottom,
                        "width": info.rcWork.right - info.rcWork.left,
                        "height": info.rcWork.bottom - info.rcWork.top
                    },
                    "is_primary": is_primary
                })
            return True
            
        EnumDisplayMonitors(None, None, MonitorEnumProc(foreach_monitor), 0)
        return monitors

    def get_clipboard_state(self) -> dict:
        text = ""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        try:
            user32.GetClipboardData.restype = ctypes.c_void_p
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            
            if user32.OpenClipboard(None):
                CF_UNICODETEXT = 13
                if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                    hData = user32.GetClipboardData(CF_UNICODETEXT)
                    if hData:
                        pData = kernel32.GlobalLock(hData)
                        if pData:
                            text = ctypes.c_wchar_p(pData).value
                            kernel32.GlobalUnlock(hData)
                user32.CloseClipboard()
        except Exception:
            pass
            
        return {
            "type": "text" if text else "empty",
            "length": len(text) if text else 0,
            "hash": hash(text) if text else 0
        }

    def get_connected_devices(self) -> list:
        devices = []
        kernel32 = ctypes.windll.kernel32
        try:
            buf_size = kernel32.GetLogicalDriveStringsW(0, None)
            if buf_size > 0:
                buf = ctypes.create_unicode_buffer(buf_size)
                kernel32.GetLogicalDriveStringsW(buf_size, buf)
                drives = [d for d in buf.value.split('\x00') if d]
                for drive in drives:
                    drive_type = kernel32.GetDriveTypeW(drive)
                    type_str = "unknown"
                    if drive_type == 2:
                        type_str = "removable_disk"
                    elif drive_type == 3:
                        type_str = "fixed_disk"
                    elif drive_type == 5:
                        type_str = "cdrom"
                    devices.append({
                        "id": drive,
                        "name": f"Logical Drive {drive}",
                        "type": type_str
                    })
        except Exception:
            pass
        return devices

    def get_network_status(self) -> dict:
        flags = ctypes.c_ulong()
        connected = False
        try:
            connected = ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0) != 0
        except Exception:
            pass
            
        return {
            "connected": connected,
            "type": "lan/wifi" if connected else "disconnected",
            "flags": flags.value
        }

    def get_battery_status(self) -> dict:
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong)
            ]
        try:
            status = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                ac_status = "offline"
                if status.ACLineStatus == 1:
                    ac_status = "online"
                elif status.ACLineStatus == 255:
                    ac_status = "unknown"
                    
                percent = status.BatteryLifePercent
                if percent == 255:
                    percent = -1
                    
                return {
                    "ac_status": ac_status,
                    "percent": percent,
                    "charging": (status.BatteryFlag & 8) != 0,
                    "life_time_seconds": status.BatteryLifeTime
                }
        except Exception:
            pass
        return {
            "ac_status": "unknown",
            "percent": -1,
            "charging": False,
            "life_time_seconds": -1
        }

