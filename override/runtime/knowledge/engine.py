import logging
import datetime
import threading
from typing import List, Dict, Any, Optional

from override.runtime.registry.module import OverrideModule
from override.runtime.interfaces.knowledge import IKnowledgeEngine
from override.runtime.interfaces.event import IEvent, IEventBus
from override.runtime.event.event import Event
from override.runtime.config.config import ConfigurationManager
from override.runtime.interfaces.memory import IEmbeddingService
from override.runtime.knowledge.store import SQLiteKnowledgeStore
from override.runtime.knowledge.consolidation import KnowledgeConsolidationService
from override.runtime.knowledge.models import WorkflowRecord, TaskOutcomeRecord, SemanticKnowledgeRecord, PatternRecord

logger = logging.getLogger("Override.KnowledgeEngine")

class KnowledgeEngine(OverrideModule, IKnowledgeEngine):
    """
    Layer 08 — Memory Consolidation & Knowledge Engine.
    Consolidates episodic details into durable workflows, logs outcomes, tracks performance patterns,
    and supports hybrid query operations.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        config: ConfigurationManager,
        embedding_service: IEmbeddingService,
        db_path: str = "data/knowledge.db"
    ):
        super().__init__("knowledge_engine")
        self._event_bus = event_bus
        self._config = config
        self._embedding_service = embedding_service
        self._db_path = db_path
        self._lock = threading.RLock()
        
        self._store = SQLiteKnowledgeStore(self._db_path)
        self._consolidation = KnowledgeConsolidationService(self._store)
        self._completed_steps_cache: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # ICognitiveEngine Lifecycle Hooks
    # ------------------------------------------------------------------

    def on_initialize(self) -> None:
        """Initialize schema and event subscriptions."""
        logger.info("Initializing Knowledge Engine...")
        with self._lock:
            self._store.initialize_schema()

        # Event Bus subscriptions
        self._event_bus.subscribe("verification.passed", self._on_verification_passed)
        self._event_bus.subscribe("verification.failed", self._on_verification_failed)
        self._event_bus.subscribe("execution.task_completed", self._on_execution_task_completed)
        self._event_bus.subscribe("memory.store_requested", self._on_store_requested)
        self._event_bus.subscribe("memory.retrieve_requested", self._on_retrieve_requested)
        self._event_bus.subscribe("system.shutdown", self._on_system_shutdown)

        logger.info("Knowledge Engine initialized.")

    def on_start(self) -> None:
        """Start engine hooks."""
        logger.info("Knowledge Engine started.")

    def on_stop(self) -> None:
        """Stop engine and close database connection."""
        logger.info("Stopping Knowledge Engine...")
        with self._lock:
            self._store.close()
            self._completed_steps_cache.clear()
        logger.info("Knowledge Engine stopped.")

    # ------------------------------------------------------------------
    # IKnowledgeEngine Interface Methods
    # ------------------------------------------------------------------

    async def store_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        with self._lock:
            # Generate embedding for search relevance
            vector = await self._generate_embedding(name)
            record = WorkflowRecord(
                name=name,
                steps=steps,
                vector=vector,
                metadata=metadata
            )
            self._store.insert_workflow(record)
            
            # Emit record stored event
            self._event_bus.publish(Event(
                _topic="memory.record_stored",
                _source="knowledge_engine",
                _payload={"record_id": record.workflow_id, "record_type": "workflow"}
            ))
            return record.workflow_id

    async def store_task_outcome(
        self,
        plan_id: str,
        correlation_id: str,
        success: bool,
        report: Dict[str, Any]
    ) -> str:
        with self._lock:
            vector = await self._generate_embedding(str(report))
            record = TaskOutcomeRecord(
                plan_id=plan_id,
                correlation_id=correlation_id,
                success=success,
                report=report,
                vector=vector
            )
            self._store.insert_task_outcome(record)
            
            self._event_bus.publish(Event(
                _topic="memory.record_stored",
                _source="knowledge_engine",
                _payload={"record_id": record.outcome_id, "record_type": "outcome"}
            ))
            return record.outcome_id

    async def store_semantic_knowledge(
        self,
        topic: str,
        content: str,
        tags: List[str]
    ) -> str:
        with self._lock:
            vector = await self._generate_embedding(content)
            record = SemanticKnowledgeRecord(
                topic=topic,
                content=content,
                tags=tags,
                vector=vector
            )
            self._store.insert_semantic_knowledge(record)
            
            self._event_bus.publish(Event(
                _topic="memory.record_stored",
                _source="knowledge_engine",
                _payload={"record_id": record.knowledge_id, "record_type": "semantic"}
            ))
            return record.knowledge_id

    async def query_knowledge(
        self,
        query_text: str,
        limit: int = 5,
        record_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            # Generate query embedding
            query_vector = None
            if query_text.strip():
                query_vector = await self._generate_embedding(query_text)
            
            results = self._store.search_hybrid(
                query_vector=query_vector,
                query_text=query_text,
                limit=limit,
                record_types=record_types
            )
            return results

    async def forget_knowledge(self, record_id: str) -> bool:
        with self._lock:
            success = self._store.delete_record(record_id)
            if success:
                self._event_bus.publish(Event(
                    _topic="memory.record_deleted",
                    _source="knowledge_engine",
                    _payload={"record_id": record_id}
                ))
            return success

    async def compact_knowledge(self) -> None:
        with self._lock:
            await self._consolidation.run_compaction()
            self._event_bus.publish(Event(
                _topic="memory.compaction_completed",
                _source="knowledge_engine",
                _payload={"timestamp": datetime.datetime.utcnow().isoformat() + "Z"}
            ))

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _generate_embedding(self, text: str) -> List[float]:
        try:
            return await self._embedding_service.get_embedding(text)
        except Exception as e:
            logger.error(f"Error generating embedding vector: {e}")
            return []

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    async def _on_verification_passed(self, event: IEvent) -> None:
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        correlation_id = payload.get("correlation_id")
        report = payload.get("report", {})

        if not plan_id:
            return

        with self._lock:
            steps = self._completed_steps_cache.pop(plan_id, [])
            
        try:
            record_ids = await self._consolidation.consolidate_success(
                plan_id=plan_id,
                correlation_id=correlation_id,
                report=report,
                steps=steps
            )
            # Emit stored events for consolidation output
            for rid in record_ids:
                # We already publish record_stored inside the consolidation, but let's publish record_updated as well if it updates frequency.
                pass
        except Exception as e:
            logger.error(f"Failed to consolidate successful plan verification: {e}", exc_info=True)

    async def _on_verification_failed(self, event: IEvent) -> None:
        payload = event.payload or {}
        plan_id = payload.get("plan_id")
        correlation_id = payload.get("correlation_id")
        report = payload.get("report", {})

        if not plan_id:
            return

        with self._lock:
            # Pop steps cache to avoid memory leak
            self._completed_steps_cache.pop(plan_id, None)

        try:
            await self._consolidation.consolidate_failure(
                plan_id=plan_id,
                correlation_id=correlation_id,
                report=report
            )
        except Exception as e:
            logger.error(f"Failed to consolidate failed plan verification: {e}", exc_info=True)

    async def _on_execution_task_completed(self, event: IEvent) -> None:
        payload = event.payload or {}
        result = payload.get("result", {})
        plan_id = result.get("plan_id")
        if plan_id:
            with self._lock:
                self._completed_steps_cache[plan_id] = result.get("completed_steps", [])

    async def _on_store_requested(self, event: IEvent) -> None:
        payload = event.payload or {}
        record_type = payload.get("record_type")
        data = payload.get("data", {})

        try:
            if record_type == "workflow":
                await self.store_workflow(
                    name=data.get("name", ""),
                    steps=data.get("steps", []),
                    metadata=data.get("metadata")
                )
            elif record_type == "outcome":
                await self.store_task_outcome(
                    plan_id=data.get("plan_id", ""),
                    correlation_id=data.get("correlation_id", ""),
                    success=bool(data.get("success", False)),
                    report=data.get("report", {})
                )
            elif record_type == "semantic":
                await self.store_semantic_knowledge(
                    topic=data.get("topic", ""),
                    content=data.get("content", ""),
                    tags=data.get("tags", [])
                )
            elif record_type == "pattern":
                with self._lock:
                    vector = await self._generate_embedding(data.get("key", ""))
                    record = PatternRecord(
                        key=data.get("key", ""),
                        value=data.get("value", {}),
                        vector=vector
                    )
                    self._store.insert_pattern(record)
                    self._event_bus.publish(Event(
                        _topic="memory.record_stored",
                        _source="knowledge_engine",
                        _payload={"record_id": record.pattern_id, "record_type": "pattern"}
                    ))
        except Exception as e:
            logger.error(f"Failed to handle memory.store_requested: {e}", exc_info=True)

    async def _on_retrieve_requested(self, event: IEvent) -> None:
        payload = event.payload or {}
        query_text = payload.get("query_text", "")
        limit = payload.get("limit", 5)
        record_types = payload.get("record_types")
        correlation_id = payload.get("correlation_id")

        try:
            results = await self.query_knowledge(
                query_text=query_text,
                limit=limit,
                record_types=record_types
            )
            self._event_bus.publish(Event(
                _topic="memory.query_completed",
                _source="knowledge_engine",
                _payload={
                    "correlation_id": correlation_id,
                    "query_text": query_text,
                    "results": results,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
            ))
        except Exception as e:
            logger.error(f"Failed to handle memory.retrieve_requested: {e}", exc_info=True)

    async def _on_system_shutdown(self, event: IEvent) -> None:
        logger.info("System shutdown received in Knowledge Engine.")
        self.stop()
