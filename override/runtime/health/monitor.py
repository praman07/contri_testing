import time
import threading
from typing import Dict
from override.runtime.health.status import HealthStatus
from override.runtime.health.metrics import SystemMetricsCollector, SystemMetrics

class HealthMonitor:
    """
    Evaluates host system metrics and registers component heartbeats.
    Determines if Override has degraded or critical operational warnings.
    """

    def __init__(
        self,
        pal,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 90.0,
        heartbeat_timeout_seconds: float = 30.0
    ):
        self._collector = SystemMetricsCollector(pal)
        self._cpu_threshold = cpu_threshold
        self._memory_threshold = memory_threshold
        self._heartbeat_timeout = heartbeat_timeout_seconds
        
        # Registration tracking
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.RLock()

    def record_heartbeat(self, component_id: str) -> None:
        """Records a heartbeat timestamp for a specific component."""
        with self._lock:
            self._heartbeats[component_id] = time.time()

    def get_status(self) -> HealthStatus:
        """
        Analyzes host metrics and registered component heartbeats.
        Returns the overall HealthStatus enum.
        """
        with self._lock:
            # 1. Check system metrics
            metrics = self._collector.collect()
            if metrics.cpu_percent >= self._cpu_threshold or metrics.memory_percent >= self._memory_threshold:
                return HealthStatus.DEGRADED

            # 2. Check for stale heartbeats
            now = time.time()
            for comp_id, last_time in self._heartbeats.items():
                if now - last_time > self._heartbeat_timeout:
                    # Stale heartbeat represents a locked engine thread or unresponsive component
                    return HealthStatus.CRITICAL

            return HealthStatus.HEALTHY
            
    def get_metrics(self) -> SystemMetrics:
        """Returns the current raw SystemMetrics."""
        return self._collector.collect()
