import os
import threading
from dataclasses import dataclass

@dataclass(frozen=True)
class SystemMetrics:
    """Structure encapsulating host resource usage metrics."""
    cpu_percent: float
    memory_percent: float
    thread_count: int

class SystemMetricsCollector:
    """Collects CPU, memory, and thread counts from the host platform."""

    def __init__(self, pal):
        self._pal = pal

    def collect(self) -> SystemMetrics:
        thread_cnt = threading.active_count()
        cpu_pct = 0.0
        mem_pct = 0.0

        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
        except ImportError:
            # Fallback to PAL-native information if psutil is unavailable
            info = self._pal.get_platform_info()
            total_mem = info.get("total_memory_bytes", 0)
            # If we don't have psutil, we estimate or return default low estimates
            if total_mem > 0:
                # We can't query available memory without psutil easily, so we output 0.0
                pass

        return SystemMetrics(
            cpu_percent=cpu_pct,
            memory_percent=mem_pct,
            thread_count=thread_cnt
        )
