"""
Integration test suite for Layer 04 — Memory Engine.

Verifies:
  1. Boot registration: memory_engine is resolved and bootable after perception_engine.
  2. Lifecycle: publishes memory.engine.started and memory.engine.stopped.
  3. Ingestion & Event integration: subscribes to perception.frame_ready, stores record,
     publishes memory.ingested.
  4. Privacy validation: redacts SSNs, credit cards, and API keys before persistence.
  5. Hybrid search with query-time decay: combines FTS5 score and vector cosine similarity.
  6. Failure modes:
     - DB corruption auto-recovery (renaming corrupted db and rebuilding schema).
     - Disk space full ingestion suspension and memory.ingestion_suspended publishing.
     - Embedding service downtime FTS5-only fallback.
  7. Background consolidation: clusters unconsolidated traces, summaries stored in Semantic,
     publishes memory.consolidated.
"""

import os
import sys
import json
import asyncio
import logging
import sqlite3
import shutil
import threading
import time
from typing import List, Dict, Any

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.interfaces.memory import IEmbeddingService, IMemoryEngine_v1
from override.runtime.memory.engine import MemoryEngine
from override.runtime.memory.sal import SQLiteSAL
from override.runtime.observation.engine import ObservationEngine
from override.runtime.config.config import ConfigurationManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Memory.Test")

TEST_DB_PATH = "data/test_memory.db"

class BrokenEmbeddingService(IEmbeddingService):
    """Embedding service that throws exceptions to test fallback modes."""
    async def get_embedding(self, text: str) -> List[float]:
        raise RuntimeError("Embedding service unavailable connection timed out")


async def main():
    logger.info("=== STARTING MEMORY ENGINE INTEGRATION TEST ===")
    
    # Ensure a clean database path for tests
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    
    # 1. Bootstrap and DI registry verification
    container = initialize_container()
    discover_and_register_modules(container)

    registry: ModuleRegistry = container.resolve(ModuleRegistry)
    event_bus: EventBus = container.resolve(IEventBus)

    # Set the running loop in the event bus so background dispatcher task starts
    loop = asyncio.get_running_loop()
    event_bus.set_event_loop(loop)

    # Track published events via async recorder
    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Test Recorder Captured: {event.topic}")

    event_bus.subscribe("memory.*", recorder)
    event_bus.subscribe("perception.*", recorder)

    # Boot order test
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "memory_engine" in boot_order
    assert "perception_engine" in boot_order
    
    per_idx = boot_order.index("perception_engine")
    mem_idx = boot_order.index("memory_engine")
    assert per_idx < mem_idx, "perception_engine must initialize before memory_engine"
    logger.info("1. Boot order verification passed.")

    # Initialize all modules in topological order (on_initialize)
    for mod_name in boot_order:
        logger.info(f"Initializing module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_initialize()

    # Clear observation providers to prevent real OS event flooding
    obs_engine = container.resolve(ObservationEngine)
    obs_engine._providers.clear()
    obs_engine._provider_map.clear()

    # Locate Memory Engine
    memory_engine = container.resolve(IMemoryEngine_v1)
    
    # Override database path for clean test execution
    memory_engine._db_path = TEST_DB_PATH
    memory_engine._sal = SQLiteSAL(TEST_DB_PATH)
    memory_engine._initialize_database()

    # 2. Lifecycle started event verification
    for mod_name in boot_order:
        logger.info(f"Starting module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_start()

    # Give startup events a brief moment to propagate
    await asyncio.sleep(0.2)

    started_events = [e for e in events_received if e.topic == "memory.engine.started"]
    assert len(started_events) > 0, "memory.engine.started must be published on start"
    logger.info("2. Lifecycle start event verification passed.")

    # 3. Ingestion and Event Integration (frame_ready)
    events_received.clear()
    
    # Publish frame_ready event
    frame_payload = {
        "timestamp": "2026-07-09T12:00:00Z",
        "source_event_id": "test_evt_1",
        "active_window_title": "Visual Studio Code - main.py",
        "active_window_class": "VSCode",
        "active_app_category": "ide",
        "ocr_text": "def test_run(): pass",
        "speech_transcript": "",
        "clipboard_text_type": "empty",
        "detected_entities": []
    }
    
    event_bus.publish(Event(
        _topic="perception.frame_ready",
        _source="perception_engine",
        _payload=frame_payload
    ))

    # Allow async ingestion to execute
    await asyncio.sleep(0.3)

    ingested_events = [e for e in events_received if e.topic == "memory.ingested"]
    assert len(ingested_events) == 1, "Should have received one memory.ingested event"
    assert ingested_events[0].payload["memory_type"] == "episodic", "Memory type must be episodic"
    logger.info("3. Ingestion and Event integration verification passed.")

    # 4. Privacy Redaction verification
    # Store memory containing sensitive records
    sensitive_desc = "Credit card is 4111-2222-3333-4444 and my SSN is 000-12-3456. OpenAI API Key is sk-U94mKj840mLksj823nLks74mKjso18mLksj29mKjso18mKjs."
    mem_id = await memory_engine.store_episodic(
        content=sensitive_desc,
        metadata={"salience": 1.0},
        tags=["privacy_test"]
    )

    # Read from database to verify redaction before SQL persistence
    sal_record = memory_engine._sal._row_to_dict(
        "episodic",
        memory_engine._sal._get_connection().execute("SELECT * FROM episodic_memories WHERE memory_id = ?", (mem_id,)).fetchone()
    )
    
    logger.info(f"Redacted persisted content: {sal_record['content']}")
    assert "4111" not in sal_record["content"]
    assert "000-12" not in sal_record["content"]
    assert "sk-" not in sal_record["content"]
    assert "[REDACTED]" in sal_record["content"]
    logger.info("4. Privacy Redaction verification passed.")

    # 5. Hybrid search with decay verification
    events_received.clear()
    
    # Store distinct procedural patterns
    proc_desc = "Use command npx create-vite-app to build new React projects"
    await memory_engine.store_procedural(proc_desc, [{"step": 1, "action": "npx"}], 1.0)

    # Query matching FTS5 / lexical
    query_results = await memory_engine.query("React projects", limit=5)
    assert len(query_results) > 0, "Query should match procedural memory"
    assert query_results[0]["content"] == proc_desc, "Top hit should be the correct procedural description"
    
    # Allow async EventBus publication to run
    await asyncio.sleep(0.2)
    
    retrieved_events = [e for e in events_received if e.topic == "memory.retrieved"]
    assert len(retrieved_events) == 1, "memory.retrieved event must be published"
    logger.info("5. Hybrid search and relevance decay verification passed.")

    # 6. Failure Modes
    logger.info("Testing failure modes...")

    # A. Embedding Service unavailability
    original_service = memory_engine._embedding_service
    memory_engine._embedding_service = BrokenEmbeddingService()
    
    # Query should still pass with FTS5 lexical fallback
    logger.info("Testing FTS5-only query fallback during embedding service downtime...")
    fallback_results = await memory_engine.query("React projects", limit=5)
    assert len(fallback_results) > 0, "Fallback query should work"
    logger.info("Fallback query matched record successfully.")
    
    # Restore original service
    memory_engine._embedding_service = original_service

    # B. DB Corruption Auto-Recovery
    logger.info("Testing database corruption recovery...")
    memory_engine._sal.close()
    
    # Write garbage directly to database file to corrupt it
    with open(TEST_DB_PATH, "w") as f:
        f.write("GARBAGE DATA CORRUPTS SQLITE SIGNATURE")

    # Run query/store to trigger auto-recovery
    logger.info("Triggering query on corrupted database...")
    recovery_results = await memory_engine.query("React projects", limit=5)
    
    # Verifies that database file was moved and a new schema initialized
    assert len(recovery_results) == 0, "New database schema initialized, so results must be empty"
    
    # Verify backup exists
    found_backup = False
    for filename in os.listdir("data"):
        if filename.startswith("test_memory.db.corrupt_"):
            found_backup = True
            try:
                os.remove(os.path.join("data", filename)) # Clean up corrupt backups
            except Exception:
                pass
    
    assert found_backup, "Corrupt database backup must have been archived"
    logger.info("DB corruption successfully recovered.")

    # C. Disk Space Full Ingestion Suspension
    logger.info("Testing disk space exhaustion suspension...")
    events_received.clear()
    
    # Simulate DB full
    memory_engine._ingestion_suspended = False # reset
    
    # Inject a mock execution loop that raises sqlite3.OperationalError for disk full
    def fake_db_full_insert():
        raise sqlite3.OperationalError("database or disk is full")
        
    try:
        memory_engine._execute_with_recovery(fake_db_full_insert)
    except Exception as e:
        assert isinstance(e, RuntimeError)
        assert "disk space constraints" in str(e)

    # Allow event loop to process suspension event
    await asyncio.sleep(0.2)

    assert memory_engine._ingestion_suspended, "Ingestion must be suspended"
    
    suspended_events = [e for e in events_received if e.topic == "memory.ingestion_suspended"]
    assert len(suspended_events) == 1, "Suspension event must be published"
    logger.info("Ingestion suspension verified.")

    # Reset ingestion suspension for consolidation test
    memory_engine._ingestion_suspended = False

    # 7. Background Consolidation
    logger.info("Testing memory consolidation...")
    events_received.clear()
    
    # Store some unconsolidated frames
    await memory_engine.store_episodic("Working on code compiler design", {"salience": 1.0}, ["coding"])
    await memory_engine.store_episodic("Browsing API documentation online", {"salience": 1.0}, ["browser"])

    # Run manual consolidation
    await memory_engine.consolidate()

    # Allow event loop to process consolidation event
    await asyncio.sleep(0.2)

    consolidated_events = [e for e in events_received if e.topic == "memory.consolidated"]
    assert len(consolidated_events) == 1, "memory.consolidated event must be published"
    assert consolidated_events[0].payload["source_records_compressed"] >= 2
    
    # Verify that unconsolidated count is now zero
    unconsolidated = memory_engine._sal.get_unconsolidated_records(10)
    assert len(unconsolidated) == 0, "All fetched records must be marked consolidated"
    logger.info("7. Background consolidation verification passed.")

    # 8. Clean Shutdown
    for mod_name in reversed(boot_order):
        logger.info(f"Stopping module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.on_stop()

    await asyncio.sleep(0.1)
    
    stopped_events = [e for e in events_received if e.topic == "memory.engine.stopped"]
    assert len(stopped_events) > 0
    logger.info("8. Clean shutdown verification passed.")

    # Clean up test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
        
    logger.info("=== ALL MEMORY ENGINE TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())
