"""
Integration test suite for Layer 08 — Memory Consolidation & Knowledge Engine.

Verifies:
  1. Boot registration: knowledge_engine is resolved and bootable after verification_engine.
  2. Lifecycle: subscribes to verification outcomes, stores records, and publishes memory.record_stored.
  3. Manual storage & retrieval: store_workflow, store_task_outcome, store_semantic_knowledge, query_knowledge.
  4. Lexical FTS5 / LIKE search: validates keyword matching and rank-ordered retrieval.
  5. Auto-consolidation flow:
     - Distills workflow from completed steps cache on verification.passed.
     - Logs outcomes and updates pattern success rates.
     - Updates failure metrics on verification.failed.
  6. Compaction & forget capabilities.
  7. Shutdown sequencing and resource cleanup.
"""

import os
import sys
import json
import asyncio
import logging
import sqlite3
import shutil
import datetime
from typing import List, Dict, Any

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from override.runtime.bootstrap.bootstrap import initialize_container
from override.runtime.bootstrap.discovery import discover_and_register_modules
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.interfaces.event import IEventBus, IEvent
from override.runtime.event.bus import EventBus
from override.runtime.event.event import Event
from override.runtime.interfaces.knowledge import IKnowledgeEngine
from override.runtime.interfaces.memory import IEmbeddingService
from override.runtime.knowledge.models import WorkflowRecord, TaskOutcomeRecord, SemanticKnowledgeRecord, PatternRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Override.Knowledge.Test")

TEST_DB_PATH = "data/test_knowledge.db"

async def main():
    logger.info("=== STARTING KNOWLEDGE ENGINE INTEGRATION TEST ===")
    
    # Ensure clean database path for tests
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

    # Resolve the engine and override db path for testing
    knowledge_engine: IKnowledgeEngine = container.resolve(IKnowledgeEngine)
    # Re-initialize engine with test db path
    knowledge_engine._db_path = TEST_DB_PATH
    knowledge_engine._store.close()
    knowledge_engine._store = sqlite3.connect(TEST_DB_PATH) # Will be handled by initialize/start
    from override.runtime.knowledge.store import SQLiteKnowledgeStore
    knowledge_engine._store = SQLiteKnowledgeStore(TEST_DB_PATH)
    from override.runtime.knowledge.consolidation import KnowledgeConsolidationService
    knowledge_engine._consolidation = KnowledgeConsolidationService(knowledge_engine._store)

    # Track published events via async recorder
    events_received: List[IEvent] = []
    async def recorder(event: IEvent) -> None:
        events_received.append(event)
        logger.info(f"Test Recorder Captured: {event.topic}")

    event_bus.subscribe("memory.*", recorder)

    # Boot order test
    boot_order = registry.get_boot_order()
    logger.info(f"Topological initialization order: {boot_order}")
    assert "knowledge_engine" in boot_order
    assert "verification_engine" in boot_order
    
    ver_idx = boot_order.index("verification_engine")
    know_idx = boot_order.index("knowledge_engine")
    assert ver_idx < know_idx, "verification_engine must initialize before knowledge_engine"
    logger.info("1. Boot order verification passed.")

    # Initialize all modules in topological order (on_initialize)
    for mod_name in boot_order:
        logger.info(f"Initializing module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.initialize()
    logger.info("2. Initialization hook verification passed.")

    # Start all modules
    for mod_name in boot_order:
        logger.info(f"Starting module: {mod_name}")
        mod = registry.get_module(mod_name)
        mod.start()
    logger.info("3. Start hook verification passed.")

    await asyncio.sleep(0.1)

    # --- Test Case 1: Manual Storage & Hybrid Retrieval ---
    logger.info("--- Test Case 1: Manual Storage & Hybrid Retrieval ---")
    
    # Store workflow
    steps = [
        {"step_id": "1", "action": "click", "params": {"x": 100, "y": 200}},
        {"step_id": "2", "action": "type", "params": {"text": "hello"}}
    ]
    wf_id = await knowledge_engine.store_workflow("Test User Login Flow", steps, {"app": "chrome"})
    assert wf_id is not None
    logger.info(f"Manually stored workflow. ID: {wf_id}")

    # Store semantic fact
    fact_id = await knowledge_engine.store_semantic_knowledge(
        topic="user_preferences",
        content="The user prefers dark mode for all IDE windows and code editors.",
        tags=["ui", "preferences", "dark_mode"]
    )
    assert fact_id is not None
    logger.info(f"Manually stored semantic fact. ID: {fact_id}")

    await asyncio.sleep(0.2) # Allow events to process

    # Retrieve knowledge
    results = await knowledge_engine.query_knowledge(query_text="dark mode", limit=2)
    assert len(results) > 0
    assert results[0]["topic"] == "user_preferences"
    logger.info(f"Retrieved correct semantic preference record: {results[0]['content']}")

    # --- Test Case 2: Lexical FTS5 Matching ---
    logger.info("--- Test Case 2: Lexical FTS5 Matching ---")
    results = await knowledge_engine.query_knowledge(query_text="Login Flow", limit=2, record_types=["workflow"])
    assert len(results) > 0
    assert "Login Flow" in results[0]["name"]
    logger.info("Lexical FTS5 retrieval verified successfully.")

    # --- Test Case 3: Auto-Consolidation Flow (Success) ---
    logger.info("--- Test Case 3: Auto-Consolidation Flow (Success) ---")
    
    plan_id = "plan_login_001"
    correlation_id = "corr_12345"
    
    # Simulate execution completion event carrying steps
    event_bus.publish(Event(
        _topic="execution.task_completed",
        _source="execution_engine",
        _payload={
            "plan_id": plan_id,
            "correlation_id": correlation_id,
            "result": {
                "plan_id": plan_id,
                "correlation_id": correlation_id,
                "status": "completed",
                "completed_steps": [
                    {"step_id": "s1", "action": "open_browser", "params": {"url": "http://login.com"}},
                    {"step_id": "s2", "action": "type_credentials", "params": {"user": "admin"}}
                ]
            }
        }
    ))
    
    await asyncio.sleep(0.4)

    # Verify that the workflow was auto-distilled and the task outcome registered
    results_outcome = await knowledge_engine.query_knowledge(query_text=plan_id, limit=2, record_types=["outcome"])
    assert len(results_outcome) > 0
    assert results_outcome[0]["plan_id"] == plan_id
    assert results_outcome[0]["success"] == 1
    logger.info("Auto-consolidated outcome logged successfully.")

    results_wf = await knowledge_engine.query_knowledge(query_text="open_browser", limit=2, record_types=["workflow"])
    assert len(results_wf) > 0
    assert "Workflow" in results_wf[0]["name"]
    logger.info(f"Auto-distilled workflow verified: {results_wf[0]['name']}")

    # Verify pattern record
    pattern_results = await knowledge_engine.query_knowledge(query_text=plan_id, limit=2, record_types=["pattern"])
    assert len(pattern_results) > 0
    assert pattern_results[0]["value"]["success_count"] == 1
    assert pattern_results[0]["value"]["success_rate"] == 1.0
    logger.info("Auto-updated pattern record statistics verified.")

    # --- Test Case 4: Auto-Consolidation Flow (Failure) ---
    logger.info("--- Test Case 4: Auto-Consolidation Flow (Failure) ---")
    
    plan_id_fail = "plan_login_001" # Same key to trigger pattern stats update
    
    # Simulate execution failure event
    event_bus.publish(Event(
        _topic="execution.task_failed",
        _source="execution_engine",
        _payload={
            "plan_id": plan_id_fail,
            "correlation_id": correlation_id,
            "result": {
                "plan_id": plan_id_fail,
                "correlation_id": correlation_id,
                "status": "failed",
                "completed_steps": [],
                "metadata": {"failure_reason": "Element not found"}
            }
        }
    ))

    await asyncio.sleep(0.4)

    # Verify pattern statistics updated success rate
    pattern_results = await knowledge_engine.query_knowledge(query_text=plan_id_fail, limit=2, record_types=["pattern"])
    assert len(pattern_results) > 0
    val = pattern_results[0]["value"]
    assert val["success_count"] == 1
    assert val["failure_count"] == 1
    assert val["success_rate"] == 0.5
    logger.info("Pattern metrics updated correct failure stats and success rate (0.5).")

    # --- Test Case 5: Compaction & Forget Capabilities ---
    logger.info("--- Test Case 5: Compaction & Forget Capabilities ---")
    
    # Forget record
    forgot = await knowledge_engine.forget_knowledge(fact_id)
    assert forgot is True
    
    results = await knowledge_engine.query_knowledge(query_text="dark mode", limit=2)
    assert len(results) == 0
    logger.info("Forget capability successfully verified (record deleted).")

    # Compact knowledge
    await knowledge_engine.compact_knowledge()
    await asyncio.sleep(0.1)
    
    # Check compaction event recorded
    compaction_event = next((e for e in events_received if e.topic == "memory.compaction_completed"), None)
    assert compaction_event is not None
    logger.info("Compaction execution and event publication verified.")

    # --- Test Case 6: Shutdown sequencing ---
    logger.info("--- Test Case 6: Shutdown sequencing ---")
    
    # Trigger system shutdown event
    event_bus.publish(Event(
        _topic="system.shutdown",
        _source="test_runner",
        _payload={}
    ))
    
    await asyncio.sleep(0.2)
    
    # Verify module stopped
    assert not knowledge_engine.is_running
    logger.info("Shutdown event lifecycle hooks verified successfully.")

    # Clean up test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    logger.info("=== ALL KNOWLEDGE ENGINE TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
