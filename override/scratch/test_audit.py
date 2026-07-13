import asyncio
import os
import sys
import time
import threading
import logging
import inspect

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.startup import boot_system
from override.runtime.bootstrap.shutdown import graceful_shutdown
from override.runtime.runtime.runtime import Runtime
from override.runtime.interfaces.event import IEventBus
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.registry.metadata import ModuleMetadata
from override.runtime.observation.engine import ObservationEngine
from override.runtime.observation.providers.base import IObservationProvider
from override.runtime.observation.frame import ObservationFrame

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.MilestoneAudit")

IS_WINDOWS = sys.platform == "win32"

# -----------------------------------------------------------------------------
# OS-Specific Resource Profiling Helper
# -----------------------------------------------------------------------------
def get_memory_usage_mb() -> float:
    """Returns the RSS memory usage of the current process in Megabytes."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_uint32),
                    ("PageFaultCount", ctypes.c_uint32),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            
            GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
            GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_uint32]
            GetProcessMemoryInfo.restype = ctypes.c_bool

            GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
            GetCurrentProcess.restype = ctypes.c_void_p

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            h_process = GetCurrentProcess()
            if GetProcessMemoryInfo(h_process, ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize / (1024 * 1024)
        return 0.0

# -----------------------------------------------------------------------------
# 1. Boundary & Design Compliance Audit
# -----------------------------------------------------------------------------
def run_boundary_assertions(engine: ObservationEngine):
    logger.info("Executing Objective 1: Boundary & Design Ownership Assertions...")
    
    # 1. Verify that all providers only gather raw data and do not process it
    # We inspect the code files and runtime types
    providers = engine.get_providers()
    assert len(providers) > 0, "No providers registered in engine!"

    
    for provider in providers:
        # Check that they inherit from IObservationProvider
        assert isinstance(provider, IObservationProvider), f"Provider {provider.provider_id} must implement IObservationProvider"
        
        # Verify that their source files contain no references to models, OCR, NLP, or databases
        # We read the module file
        file_path = inspect.getfile(provider.__class__)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            
            # Assert absence of model inference, layout parsing, OCR, or memory operations
            restricted_keywords = [
                "pytesseract", "tesseract", "easyocr", "paddleocr", "openai", "claude",
                "gemini", "embedding", "vector", "llm", "pipeline", "predict",
                "inference", "classify", "memory_store", "database"
            ]

            for kw in restricted_keywords:
                assert kw not in content, f"Subsystem boundary violation! Provider {provider.provider_id} uses restricted term '{kw}' in {file_path}"
                
    logger.info("  [SUCCESS] All providers are verified to collect raw signals only (no OCR, perception, reasoning, or memory).")

# -----------------------------------------------------------------------------
# 2. Performance & Metric Profiling
# -----------------------------------------------------------------------------
async def run_performance_benchmarks():
    logger.info("Executing Objective 2 & 3: Running Integration & Performance Benchmarks...")
    
    # Capture initial resource footprints
    initial_mem = get_memory_usage_mb()
    initial_threads = threading.active_count()
    
    t_start = time.perf_counter()
    
    container = initialize_container()
    runtime = Runtime()
    
    event_bus = container.resolve(IEventBus)
    engine = container.resolve(ObservationEngine)
    
    # Assert public interface stability
    assert hasattr(engine, "initialize"), "ObservationEngine lacks public initialize() interface"
    assert hasattr(engine, "start"), "ObservationEngine lacks public start() interface"
    assert hasattr(engine, "stop"), "ObservationEngine lacks public stop() interface"
    
    # Track throughput metrics
    event_count = 0
    
    async def track_event(event):
        nonlocal event_count
        event_count += 1
        
    # Subscribe to all observation events
    event_bus.subscribe("observation.screen_captured", track_event)
    event_bus.subscribe("observation.audio_captured", track_event)
    event_bus.subscribe("observation.window_changed", track_event)
    event_bus.subscribe("observation.filesystem_changed", track_event)
    event_bus.subscribe("observation.mouse_moved", track_event)
    event_bus.subscribe("observation.mouse_button", track_event)
    event_bus.subscribe("observation.keyboard_input", track_event)

    # Startup performance
    await boot_system(container, runtime)
    t_boot = time.perf_counter()
    startup_ms = (t_boot - t_start) * 1000
    
    logger.info(f"  Startup Time: {startup_ms:.2f} ms")
    
    # CPU & Memory Profiling (under idle running state)
    cpu_measurements = []
    mem_measurements = []
    
    # Run loop for 5 seconds to profile resources
    logger.info("  Monitoring resource footprint (5 seconds running)...")
    try:
        import psutil
        p = psutil.Process(os.getpid())
        for _ in range(5):
            cpu_measurements.append(p.cpu_percent(interval=1.0))
            mem_measurements.append(p.memory_info().rss / (1024 * 1024))
    except ImportError:
        # Fallback if psutil is not present
        p_cpu = time.process_time()
        p_perf = time.perf_counter()
        for _ in range(5):
            await asyncio.sleep(1.0)
            mem_measurements.append(get_memory_usage_mb())
        p_cpu_end = time.process_time()
        p_perf_end = time.perf_counter()
        cpu_usage_est = ((p_cpu_end - p_cpu) / (p_perf_end - p_perf)) * 100
        cpu_measurements.append(cpu_usage_est)
    
    avg_cpu = sum(cpu_measurements) / len(cpu_measurements)
    avg_mem = sum(mem_measurements) / len(mem_measurements)
    mem_overhead = avg_mem - initial_mem
    throughput = event_count / 5.0
    
    logger.info(f"  Average Idle CPU: {avg_cpu:.2f}%")
    logger.info(f"  Average Memory: {avg_mem:.2f} MB (Overhead from baseline: {mem_overhead:.2f} MB)")
    logger.info(f"  Event Throughput: {throughput:.2f} events/second (Total captured: {event_count})")
    
    # Graceful Shutdown performance
    t_shutdown_start = time.perf_counter()
    graceful_shutdown(container, runtime)
    t_shutdown_end = time.perf_counter()
    shutdown_ms = (t_shutdown_end - t_shutdown_start) * 1000
    
    logger.info(f"  Shutdown Completion Time: {shutdown_ms:.2f} ms")
    
    # Assert clean resource termination
    await asyncio.sleep(1.0) # wait briefly for worker cancellations
    final_threads = threading.active_count()
    
    logger.info(f"  Pre-run Thread Count: {initial_threads}")
    logger.info(f"  Post-run Thread Count: {final_threads}")
    
    # Let's list active threads if there is a mismatch
    if final_threads > initial_threads:
        logger.warning("Active threads after shutdown:")
        for t in threading.enumerate():
            logger.warning(f"    Thread name: {t.name}, daemon: {t.daemon}")
            
    # We assert that final threads do not exceed initial threads + 1 (python main / debugger threads)
    assert final_threads <= initial_threads + 1, f"Thread leak detected! Threads remaining: {final_threads} (expected <= {initial_threads + 1})"
    
    # Verify no asyncio tasks leak
    remaining_tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"  Remaining asyncio tasks: {len(remaining_tasks)}")
    assert len(remaining_tasks) == 0, f"Asyncio task leak detected: {remaining_tasks}"
    
    logger.info("  [SUCCESS] Performance and leak verification tests passed.")
    return {
        "startup_ms": startup_ms,
        "avg_cpu": avg_cpu,
        "avg_mem": avg_mem,
        "mem_overhead": mem_overhead,
        "throughput": throughput,
        "shutdown_ms": shutdown_ms
    }

# -----------------------------------------------------------------------------
# 3. Failure-Injection Testing
# -----------------------------------------------------------------------------
class FailingProvider(IObservationProvider):
    @property
    def provider_id(self) -> str:
        return "failing_provider"
        
    def register_callback(self, callback) -> None:
        pass
        
    def initialize(self) -> None:
        raise RuntimeError("Injected provider initialization failure!")
        
    def start(self) -> None:
        pass
        
    def stop(self) -> None:
        pass

class CrashingRuntimeProvider(IObservationProvider):
    def __init__(self):
        self._callback = None
        self._thread = None
        self._running = False
        
    @property
    def provider_id(self) -> str:
        return "crashing_runtime_provider"
        
    def register_callback(self, callback) -> None:
        self._callback = callback
        
    def initialize(self) -> None:
        pass
        
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _loop(self):
        time.sleep(0.5)
        # Throw runtime exception during data collection
        if self._callback:
            logger.info("Simulating hardware disconnection in CrashingRuntimeProvider...")
            raise RuntimeError("Injected hardware disconnection error!")

async def run_failure_injections():
    logger.info("Executing Objective 4: Failure Injection Testing...")
    
    # 1. Double registration validation & Mismatch validation
    registry = ModuleRegistry()
    
    # Verify mismatch throws ValueError
    mismatch_meta = ModuleMetadata(module_id="test_mismatch", version="1.0.0", description="desc", dependencies=[])
    try:
        registry.register(ObservationEngine(None, None, None), mismatch_meta)
        assert False, "Mismatch between module ID and metadata ID should have raised a ValueError!"
    except ValueError as e:
        logger.info(f"  [SUCCESS] Mismatch ID check verified: {e}")

    # Register successfully
    meta = ModuleMetadata(module_id="observation_engine", version="1.0.0", description="desc", dependencies=[])
    registry.register(ObservationEngine(None, None, None), meta)
    
    # Try duplicate registration of same module_id
    try:
        registry.register(ObservationEngine(None, None, None), meta)
        assert False, "Double registration should have raised a ValueError!"
    except ValueError as e:
        logger.info(f"  [SUCCESS] Double registration check verified: {e}")


    # 2. Provider initialization failure
    # We will register a failing provider on an engine instance and boot
    container = initialize_container()
    event_bus = container.resolve(IEventBus)
    event_bus.set_event_loop(asyncio.get_running_loop())
    engine = container.resolve(ObservationEngine)
    
    failing_prov = FailingProvider()
    engine.register_provider(failing_prov)
    
    # Initialize must not crash the whole system, but log the error
    logger.info("  Injecting failing provider initialization...")
    engine.initialize()
    # verify it marked initialized but log warning
    assert engine._initialized, "ObservationEngine failed to initialize with one bad provider"
    logger.info("  [SUCCESS] System survived provider initialization failure.")

    # 3. Hardware disconnection / runtime failure recovery
    crashing_prov = CrashingRuntimeProvider()
    engine.register_provider(crashing_prov)
    
    logger.info("  Starting engine with a crashing provider...")
    engine.start()
    
    # Wait for crash to trigger
    await asyncio.sleep(1.0)
    
    # Ensure other providers and the engine still running
    assert engine._running, "ObservationEngine stopped running due to provider crash"
    logger.info("  [SUCCESS] System survived provider runtime exception.")
    
    # 4. Event Bus availability during shutdown
    # Confirm that events can be published onto the Event Bus during stop
    shutdown_received = False
    async def on_shutdown_event(event):
        nonlocal shutdown_received
        shutdown_received = True
        
    event_bus.subscribe("observation.engine.stopped", on_shutdown_event)
    
    logger.info("  Stopping engine and verifying Event Bus availability...")
    engine.stop()
    await asyncio.sleep(0.5)
    
    assert shutdown_received, "Event Bus failed to deliver observation.engine.stopped event during shutdown"
    logger.info("  [SUCCESS] Event Bus availability during provider shutdown verified.")
    
    # Stop the event bus to release the loop task
    event_bus.stop()


# -----------------------------------------------------------------------------
# Main Test Entry Point
# -----------------------------------------------------------------------------
async def main():
    logger.info("=================================================================")
    logger.info("STARTING OVERRIDE LAYER 01 COGNITIVE MILESTONE VERIFICATION AUDIT")
    logger.info("=================================================================")
    
    container = initialize_container()
    engine = container.resolve(ObservationEngine)
    
    # Initialize the engine to instantiate providers
    engine.initialize()
    
    # Run tests
    run_boundary_assertions(engine)

    perf_metrics = await run_performance_benchmarks()
    await run_failure_injections()
    
    logger.info("=================================================================")
    logger.info("AUDIT COMPLETED SUCCESSFULLY")
    logger.info("=================================================================")
    logger.info("RESULTS SUMMARY:")
    logger.info(f"  Startup Time: {perf_metrics['startup_ms']:.2f} ms")
    logger.info(f"  Avg CPU Usage: {perf_metrics['avg_cpu']:.2f}%")
    logger.info(f"  Avg Memory: {perf_metrics['avg_mem']:.2f} MB")
    logger.info(f"  Mem Overhead: {perf_metrics['mem_overhead']:.2f} MB")
    logger.info(f"  Throughput: {perf_metrics['throughput']:.2f} events/sec")
    logger.info(f"  Shutdown Time: {perf_metrics['shutdown_ms']:.2f} ms")
    logger.info("  No resource leaks detected.")
    logger.info("  All boundary and failure tests passed.")

if __name__ == "__main__":
    asyncio.run(main())
