import os
import re
import uuid
import math
import sqlite3
import datetime
import threading
import logging
from typing import List, Dict, Any, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.interfaces.memory import IEmbeddingService, IMemoryEngine_v1
from override.runtime.memory.sal import SQLiteSAL

logger = logging.getLogger("Override.Memory.Engine")

class MemoryEngine(OverrideModule, IMemoryEngine_v1):
    """
    Layer 04 — Memory Engine.
    Handles ingestion, indexing, retrieval, consolidation, and privacy validation
    of episodic, semantic, and procedural memories.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        config: ConfigurationManager,
        embedding_service: Optional[IEmbeddingService],
        db_path: str = "data/memory.db"
    ):
        super().__init__("memory_engine")
        self._event_bus = event_bus
        self._config = config
        self._embedding_service = embedding_service
        self._db_path = db_path
        self._sal = SQLiteSAL(self._db_path)

        self._lock = threading.RLock()
        self._ingestion_suspended = False
        self._shutdown_event = threading.Event()
        self._consolidation_thread: Optional[threading.Thread] = None

        # Regex patterns for second-stage privacy redaction
        self._pii_patterns = [
            # Credit Cards
            re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
            # Social Security Numbers (SSN)
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            # Google API Keys
            re.compile(r"AIza[0-9A-Za-z-_]{35}"),
            # OpenAI API Keys
            re.compile(r"sk-[0-9A-Za-z]{48}"),
            # Generic secret/password/token mappings
            re.compile(r"\b(?:api|auth|secret|private|private_key|token)[_-]?(?:key|token)?\s*[:=]\s*['\"][0-9a-zA-Z-_]{16,}['\"]", re.IGNORECASE)
        ]

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        logger.info("Initializing Memory Engine...")
        self._initialize_database()

        # Event Bus subscriptions
        self._event_bus.subscribe("perception.frame_ready", self._on_frame_ready)
        self._event_bus.subscribe("context.updated", self._on_context_updated)
        self._event_bus.subscribe("planner.action_executed", self._on_action_executed)
        self._event_bus.subscribe("system.shutdown", self._on_system_shutdown)

        logger.info("Memory Engine initialized.")

    def on_start(self) -> None:
        logger.info("Starting Memory Engine...")
        self._shutdown_event.clear()
        
        # Standard lifecycle event
        self._event_bus.publish(Event(
            _topic="memory.engine.started",
            _source="memory_engine",
            _payload={}
        ))

        # Start low-priority background consolidation thread
        self._consolidation_thread = threading.Thread(
            target=self._run_consolidation_loop,
            name="override-memory-consolidation",
            daemon=True
        )
        self._consolidation_thread.start()
        logger.info("Memory Engine started.")

    def on_stop(self) -> None:
        logger.info("Stopping Memory Engine...")
        self._shutdown_event.set()
        
        if self._consolidation_thread is not None:
            self._consolidation_thread.join(timeout=2.0)
            self._consolidation_thread = None

        self._sal.close()

        self._event_bus.publish(Event(
            _topic="memory.engine.stopped",
            _source="memory_engine",
            _payload={}
        ))
        logger.info("Memory Engine stopped.")

    # ------------------------------------------------------------------
    # Public IMemoryEngine_v1 API
    # ------------------------------------------------------------------

    async def store_episodic(self, content: str, metadata: Dict[str, Any], tags: List[str]) -> str:
        self._check_ingestion_status()
        memory_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        # Apply second-stage privacy redaction
        clean_content = self._redact_secrets(content)

        # Generate embedding vector
        vector = await self._generate_embedding_safe(clean_content)

        record = {
            "memory_id": memory_id,
            "content": clean_content,
            "timestamp": timestamp,
            "salience": metadata.get("salience", 1.0),
            "vector": vector,
            "metadata": metadata,
            "tags": tags,
            "consolidated": 0
        }

        self._execute_with_recovery(
            lambda: self._sal.insert_record("episodic", record)
        )

        self._event_bus.publish(Event(
            _topic="memory.ingested",
            _source="memory_engine",
            _payload={"memory_id": memory_id, "memory_type": "episodic", "timestamp": timestamp}
        ))
        return memory_id

    async def store_semantic(self, fact: str, entity: str, relationship: str, confidence: float) -> str:
        self._check_ingestion_status()
        memory_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        clean_fact = self._redact_secrets(fact)
        vector = await self._generate_embedding_safe(clean_fact)

        record = {
            "memory_id": memory_id,
            "content": clean_fact,
            "entity": entity,
            "relationship": relationship,
            "confidence": confidence,
            "timestamp": timestamp,
            "vector": vector,
            "metadata": {}
        }

        self._execute_with_recovery(
            lambda: self._sal.insert_record("semantic", record)
        )

        self._event_bus.publish(Event(
            _topic="memory.ingested",
            _source="memory_engine",
            _payload={"memory_id": memory_id, "memory_type": "semantic", "timestamp": timestamp}
        ))
        return memory_id

    async def store_procedural(self, description: str, steps: List[Dict[str, Any]], success_rate: float) -> str:
        self._check_ingestion_status()
        memory_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        clean_description = self._redact_secrets(description)
        vector = await self._generate_embedding_safe(clean_description)

        record = {
            "memory_id": memory_id,
            "content": clean_description,
            "steps": steps,
            "success_rate": success_rate,
            "timestamp": timestamp,
            "vector": vector,
            "metadata": {}
        }

        self._execute_with_recovery(
            lambda: self._sal.insert_record("procedural", record)
        )

        self._event_bus.publish(Event(
            _topic="memory.ingested",
            _source="memory_engine",
            _payload={"memory_id": memory_id, "memory_type": "procedural", "timestamp": timestamp}
        ))
        return memory_id

    async def query(
        self,
        query_text: str,
        limit: int = 5,
        memory_types: Optional[List[str]] = None,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        # Generate query vector embedding if service is available
        query_vector = await self._generate_embedding_safe(query_text)

        # Retrieve candidate records via Storage Abstraction Layer (SAL)
        candidates = self._execute_with_recovery(
            lambda: self._sal.search_hybrid(query_vector, query_text, limit * 2, memory_types)
        )

        # Apply query-time rank decay
        now = datetime.datetime.utcnow()
        scored_candidates = []

        for candidate in candidates:
            # Parse record timestamp
            try:
                created_at = datetime.datetime.fromisoformat(candidate["timestamp"].rstrip("Z"))
            except ValueError:
                created_at = now

            # Calculate age in hours
            age_hours = (now - created_at).total_seconds() / 3600.0
            
            # Simple exponential decay score
            decay_factor = math.exp(-0.01 * age_hours)  # lambda = 0.01

            # Base relevance calculated at SQL search layer
            # (In SQLiteSAL, candidate query similarity is already computed)
            base_similarity = candidate.get("salience", 1.0)
            relevance = base_similarity * decay_factor

            if relevance >= min_relevance:
                candidate["relevance_score"] = relevance
                scored_candidates.append(candidate)

        # Sort based on relevance scores and slice to the limit
        scored_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        results = scored_candidates[:limit]

        # Publish retrieval notification
        self._event_bus.publish(Event(
            _topic="memory.retrieved",
            _source="memory_engine",
            _payload={"query": query_text, "returned_count": len(results)}
        ))

        return results

    async def forget(self, memory_id: str) -> bool:
        deleted = self._execute_with_recovery(
            lambda: self._sal.delete_record(memory_id)
        )
        return deleted

    async def consolidate(self) -> None:
        """Triggers manual background consolidation run."""
        await self._consolidate_batch()

    # ------------------------------------------------------------------
    # Internal Helpers & Event Listeners
    # ------------------------------------------------------------------

    def _initialize_database(self) -> None:
        try:
            self._sal.initialize_schema()
            # If we successfully initialize database after a suspension, resume ingestion
            if self._ingestion_suspended:
                self._ingestion_suspended = False
                self._event_bus.publish(Event(
                    _topic="memory.ingestion_resumed",
                    _source="memory_engine",
                    _payload={}
                ))
        except Exception as e:
            self._handle_database_failure(e, "initialize")

    def _check_ingestion_status(self) -> None:
        if self._ingestion_suspended:
            raise RuntimeError("Memory ingestion suspended due to disk space constraints")

    def _redact_secrets(self, text: str) -> str:
        if not text:
            return text
        clean = text
        for pattern in self._pii_patterns:
            clean = pattern.sub("[REDACTED]", clean)
        return clean

    async def _generate_embedding_safe(self, text: str) -> Optional[List[float]]:
        if self._embedding_service is None:
            return None
        try:
            return await self._embedding_service.get_embedding(text)
        except Exception as e:
            logger.warning(f"Embedding service failed. Falling back to keyword search. Error: {e}")
            return None

    async def _on_frame_ready(self, event: IEvent) -> None:
        payload = event.payload
        if not payload:
            return
        
        # Assemble episodic content
        title = payload.get("active_window_title", "")
        category = payload.get("active_app_category", "")
        ocr = payload.get("ocr_text", "")
        speech = payload.get("speech_transcript", "")

        content_parts = []
        if title:
            content_parts.append(f"Window Title: {title}")
        if category:
            content_parts.append(f"Category: {category}")
        if ocr:
            content_parts.append(f"Screen Text: {ocr}")
        if speech:
            content_parts.append(f"User Speech: {speech}")

        content = " | ".join(content_parts)
        if not content.strip():
            return

        tags = [category] if category else []
        if payload.get("clipboard_text_type") != "empty":
            tags.append(payload.get("clipboard_text_type"))

        await self.store_episodic(content, {"salience": 1.0, "source_event_id": event.event_id}, tags)

    async def _on_context_updated(self, event: IEvent) -> None:
        # Context updates can be stored as episodic or semantic facts
        pass

    async def _on_action_executed(self, event: IEvent) -> None:
        payload = event.payload
        if not payload:
            return
        desc = payload.get("description", "Executed action")
        steps = payload.get("steps", [])
        rate = payload.get("success_rate", 1.0)

        await self.store_procedural(desc, steps, rate)

    async def _on_system_shutdown(self, event: IEvent) -> None:
        logger.info("System shutting down. Flushing Memory Engine database connection...")
        with self._lock:
            self._sal.close()

    def _execute_with_recovery(self, operation):
        """Wraps database queries with robust corruption and disk exhaustion recovery loops."""
        with self._lock:
            try:
                return operation()
            except sqlite3.DatabaseError as e:
                return self._handle_database_failure(e, "execute", operation)

    def _handle_database_failure(self, exception: Exception, context: str, operation=None) -> Any:
        msg = str(exception).lower()
        
        # 1. Disk Full or Read-Only File System
        if "full" in msg or "readonly" in msg or "read-only" in msg:
            logger.error(f"Memory persistence suspended: storage space exhausted. Details: {exception}")
            self._ingestion_suspended = True
            self._event_bus.publish(Event(
                _topic="memory.ingestion_suspended",
                _source="memory_engine",
                _payload={"error": str(exception)}
            ))
            if context == "execute":
                raise RuntimeError("Memory ingestion suspended due to disk space constraints") from exception
            return None

        # 2. Database Corruption
        if "corrupt" in msg or "malformed" in msg or "is not a database" in msg:
            logger.critical(f"Memory database corruption detected! Initiating automated recovery. Details: {exception}")
            self._sal.close()
            
            # Backup the corrupt file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self._db_path}.corrupt_{timestamp}"
            try:
                if os.path.exists(self._db_path):
                    os.rename(self._db_path, backup_path)
                    logger.info(f"Corrupt database archived to: {backup_path}")
            except Exception as backup_err:
                logger.error(f"Failed to backup corrupt database file: {backup_err}")

            # Re-initialize clean schema
            self._sal = SQLiteSAL(self._db_path)
            self._initialize_database()

            # Retry operation if provided
            if operation is not None:
                try:
                    return operation()
                except Exception as retry_err:
                    logger.error(f"Failed to execute operation even after database re-initialization: {retry_err}")
                    raise retry_err
            return None

        # Raise other unhandled sqlite/db errors
        raise exception

    def _run_consolidation_loop(self) -> None:
        while not self._shutdown_event.is_set():
            # Run every 60 seconds (or wake up on shutdown)
            self._shutdown_event.wait(timeout=60.0)
            if self._shutdown_event.is_set():
                break
            
            # Run batch consolidation
            try:
                import asyncio
                asyncio.run(self._consolidate_batch())
            except Exception as e:
                logger.error(f"Error during background memory consolidation: {e}")

    async def _consolidate_batch(self) -> None:
        if self._ingestion_suspended:
            return

        # Fetch unconsolidated records
        unconsolidated = self._execute_with_recovery(
            lambda: self._sal.get_unconsolidated_records(limit=10)
        )
        if not unconsolidated:
            return

        logger.info(f"Consolidating {len(unconsolidated)} episodic memory records...")

        # Formulate non-destructive summary of consolidated records
        timestamps = [r["timestamp"] for r in unconsolidated]
        categories = list(set([r["tags"][0] for r in unconsolidated if r.get("tags")]))
        summary_fact = f"Consolidated {len(unconsolidated)} episodic interactions occurring between {min(timestamps)} and {max(timestamps)}."
        if categories:
            summary_fact += f" Activities involved interaction with: {', '.join(categories)}."

        # Save summary to Semantic Memory
        summary_id = await self.store_semantic(
            fact=summary_fact,
            entity="system",
            relationship="consolidated_activity",
            confidence=0.9
        )

        # Mark source records consolidated
        record_ids = [r["memory_id"] for r in unconsolidated]
        self._execute_with_recovery(
            lambda: self._sal.mark_records_consolidated(record_ids)
        )

        # Publish notification
        self._event_bus.publish(Event(
            _topic="memory.consolidated",
            _source="memory_engine",
            _payload={
                "source_records_compressed": len(unconsolidated),
                "created_summaries": 1,
                "summary_id": summary_id
            }
        ))
        logger.info("Memory consolidation batch completed.")
