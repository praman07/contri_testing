import os
import sqlite3
import json
import math
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from override.runtime.knowledge.models import WorkflowRecord, TaskOutcomeRecord, SemanticKnowledgeRecord, PatternRecord

logger = logging.getLogger("Override.Knowledge.Store")

class IKnowledgeStore(ABC):
    """
    Interface for the Knowledge Engine storage backend.
    Decouples SQLite operations from core knowledge/consolidation logic.
    """

    @abstractmethod
    def initialize_schema(self) -> None:
        """Applies database migrations and index schemas."""
        pass

    @abstractmethod
    def insert_workflow(self, record: WorkflowRecord) -> None:
        """Inserts or updates a workflow record."""
        pass

    @abstractmethod
    def insert_task_outcome(self, record: TaskOutcomeRecord) -> None:
        """Inserts a task execution outcome trace."""
        pass

    @abstractmethod
    def insert_semantic_knowledge(self, record: SemanticKnowledgeRecord) -> None:
        """Inserts long-term semantic knowledge."""
        pass

    @abstractmethod
    def insert_pattern(self, record: PatternRecord) -> None:
        """Inserts or updates a learned pattern."""
        pass

    @abstractmethod
    def get_pattern_by_key(self, key: str) -> Optional[PatternRecord]:
        """Retrieves a pattern by its unique key."""
        pass

    @abstractmethod
    def delete_record(self, record_id: str) -> bool:
        """Deletes a record matching the ID from all tables."""
        pass

    @abstractmethod
    def search_hybrid(
        self,
        query_vector: Optional[List[float]],
        query_text: str,
        limit: int,
        record_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Executes a hybrid keyword + vector similarity query across knowledge tables."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes any open database connections."""
        pass


class SQLiteKnowledgeStore(IKnowledgeStore):
    """
    Concrete SQLite implementation of IKnowledgeStore.
    Utilizes FTS5 virtual tables and custom cosine-similarity calculations.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._fts_supported = True

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, timeout=10.0)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.error(f"Error closing SQLite connection: {e}")
            finally:
                self._conn = None

    def initialize_schema(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Create Core Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                steps TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_outcomes (
                outcome_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                report TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id TEXT PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        # 2. Add Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_plan ON task_outcomes(plan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_correlation ON task_outcomes(correlation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_semantic_topic ON semantic_knowledge(topic)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_key ON patterns(key)")

        # 3. Initialize FTS5 Tables
        try:
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS workflows_fts USING fts5(workflow_id UNINDEXED, content)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS outcomes_fts USING fts5(outcome_id UNINDEXED, content)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(knowledge_id UNINDEXED, content)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(pattern_id UNINDEXED, content)")
            self._fts_supported = True
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 is not supported by current SQLite build. Falling back. Error: {e}")
            self._fts_supported = False

        conn.commit()

    def insert_workflow(self, record: WorkflowRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        steps_str = json.dumps(record.steps)
        vector_str = json.dumps(record.vector) if record.vector is not None else None
        metadata_str = json.dumps(record.metadata)

        cursor.execute("""
            INSERT INTO workflows (workflow_id, name, steps, frequency, timestamp, vector, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workflow_id) DO UPDATE SET
                name=excluded.name,
                steps=excluded.steps,
                frequency=excluded.frequency,
                timestamp=excluded.timestamp,
                vector=excluded.vector,
                metadata=excluded.metadata
        """, (
            record.workflow_id,
            record.name,
            steps_str,
            record.frequency,
            record.timestamp,
            vector_str,
            metadata_str
        ))

        if self._fts_supported:
            cursor.execute("DELETE FROM workflows_fts WHERE workflow_id = ?", (record.workflow_id,))
            content_str = f"{record.name} {steps_str}"
            cursor.execute("INSERT INTO workflows_fts (workflow_id, content) VALUES (?, ?)", (record.workflow_id, content_str))

        conn.commit()

    def insert_task_outcome(self, record: TaskOutcomeRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        report_str = json.dumps(record.report)
        vector_str = json.dumps(record.vector) if record.vector is not None else None
        metadata_str = json.dumps(record.metadata)

        cursor.execute("""
            INSERT INTO task_outcomes (outcome_id, plan_id, correlation_id, success, report, timestamp, vector, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(outcome_id) DO UPDATE SET
                plan_id=excluded.plan_id,
                correlation_id=excluded.correlation_id,
                success=excluded.success,
                report=excluded.report,
                timestamp=excluded.timestamp,
                vector=excluded.vector,
                metadata=excluded.metadata
        """, (
            record.outcome_id,
            record.plan_id,
            record.correlation_id,
            1 if record.success else 0,
            report_str,
            record.timestamp,
            vector_str,
            metadata_str
        ))

        if self._fts_supported:
            cursor.execute("DELETE FROM outcomes_fts WHERE outcome_id = ?", (record.outcome_id,))
            content_str = f"{record.plan_id} {record.correlation_id} {report_str}"
            cursor.execute("INSERT INTO outcomes_fts (outcome_id, content) VALUES (?, ?)", (record.outcome_id, content_str))

        conn.commit()

    def insert_semantic_knowledge(self, record: SemanticKnowledgeRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        tags_str = json.dumps(record.tags)
        vector_str = json.dumps(record.vector) if record.vector is not None else None
        metadata_str = json.dumps(record.metadata)

        cursor.execute("""
            INSERT INTO semantic_knowledge (knowledge_id, topic, content, tags, timestamp, vector, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(knowledge_id) DO UPDATE SET
                topic=excluded.topic,
                content=excluded.content,
                tags=excluded.tags,
                timestamp=excluded.timestamp,
                vector=excluded.vector,
                metadata=excluded.metadata
        """, (
            record.knowledge_id,
            record.topic,
            record.content,
            tags_str,
            record.timestamp,
            vector_str,
            metadata_str
        ))

        if self._fts_supported:
            cursor.execute("DELETE FROM semantic_fts WHERE knowledge_id = ?", (record.knowledge_id,))
            content_str = f"{record.topic} {record.content} {tags_str}"
            cursor.execute("INSERT INTO semantic_fts (knowledge_id, content) VALUES (?, ?)", (record.knowledge_id, content_str))

        conn.commit()

    def insert_pattern(self, record: PatternRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        value_str = json.dumps(record.value)
        vector_str = json.dumps(record.vector) if record.vector is not None else None
        metadata_str = json.dumps(record.metadata)

        cursor.execute("""
            INSERT INTO patterns (pattern_id, key, value, timestamp, vector, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                timestamp=excluded.timestamp,
                vector=excluded.vector,
                metadata=excluded.metadata
        """, (
            record.pattern_id,
            record.key,
            value_str,
            record.timestamp,
            vector_str,
            metadata_str
        ))

        if self._fts_supported:
            cursor.execute("DELETE FROM patterns_fts WHERE pattern_id = ?", (record.pattern_id,))
            content_str = f"{record.key} {value_str}"
            cursor.execute("INSERT INTO patterns_fts (pattern_id, content) VALUES (?, ?)", (record.pattern_id, content_str))

        conn.commit()

    def get_pattern_by_key(self, key: str) -> Optional[PatternRecord]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patterns WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            return None
        return PatternRecord.from_dict(dict(row))

    def delete_record(self, record_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        deleted = False

        for table in ["workflows", "task_outcomes", "semantic_knowledge", "patterns"]:
            id_col = "workflow_id" if table == "workflows" else (
                "outcome_id" if table == "task_outcomes" else (
                    "knowledge_id" if table == "semantic_knowledge" else "pattern_id"
                )
            )
            cursor.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (record_id,))
            if cursor.rowcount > 0:
                deleted = True
            
            if self._fts_supported:
                fts_table = "workflows_fts" if table == "workflows" else (
                    "outcomes_fts" if table == "task_outcomes" else (
                        "semantic_fts" if table == "semantic_knowledge" else "patterns_fts"
                    )
                )
                cursor.execute(f"DELETE FROM {fts_table} WHERE {id_col} = ?", (record_id,))

        conn.commit()
        return deleted

    def search_hybrid(
        self,
        query_vector: Optional[List[float]],
        query_text: str,
        limit: int,
        record_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not record_types:
            record_types = ["workflow", "outcome", "semantic", "pattern"]

        results: List[Dict[str, Any]] = []
        conn = self._get_connection()
        cursor = conn.cursor()

        fts_hits: Dict[str, Tuple[float, Dict[str, Any]]] = {}

        for rtype in record_types:
            table_name = "workflows" if rtype == "workflow" else (
                "task_outcomes" if rtype == "outcome" else (
                    "semantic_knowledge" if rtype == "semantic" else "patterns"
                )
            )
            id_col = "workflow_id" if rtype == "workflow" else (
                "outcome_id" if rtype == "outcome" else (
                    "knowledge_id" if rtype == "semantic" else "pattern_id"
                )
            )
            fts_table = "workflows_fts" if rtype == "workflow" else (
                "outcomes_fts" if rtype == "outcome" else (
                    "semantic_fts" if rtype == "semantic" else "patterns_fts"
                )
            )

            matched_ids: List[Tuple[str, float]] = []

            # 1. Lexical Search
            if self._fts_supported and query_text.strip():
                try:
                    sanitized_query = query_text.replace('"', '').replace("'", "")
                    cursor.execute(f"""
                        SELECT {id_col}, rank 
                        FROM {fts_table} 
                        WHERE content MATCH ? 
                        ORDER BY rank 
                        LIMIT ?
                    """, (f"{sanitized_query}*", limit * 2))
                    matched_ids = [(row[id_col], -row["rank"]) for row in cursor.fetchall()]
                except sqlite3.OperationalError as e:
                    logger.warning(f"FTS query failed: {e}")
                    matched_ids = []

            if not matched_ids and query_text.strip():
                # LIKE fallback
                content_col = "name" if rtype == "workflow" else (
                    "report" if rtype == "outcome" else (
                        "content" if rtype == "semantic" else "key"
                    )
                )
                like_pattern = f"%{query_text}%"
                cursor.execute(f"""
                    SELECT {id_col} 
                    FROM {table_name} 
                    WHERE {content_col} LIKE ? 
                    LIMIT ?
                """, (like_pattern, limit * 2))
                matched_ids = [(row[id_col], 1.0) for row in cursor.fetchall()]

            if not query_text.strip():
                cursor.execute(f"SELECT {id_col} FROM {table_name} LIMIT ?", (limit * 2,))
                matched_ids = [(row[id_col], 0.0) for row in cursor.fetchall()]

            if not matched_ids:
                continue

            # Load matching rows
            ids_placeholder = ",".join(["?"] * len(matched_ids))
            id_to_score = {mid: score for mid, score in matched_ids}

            cursor.execute(f"""
                SELECT * FROM {table_name} 
                WHERE {id_col} IN ({ids_placeholder})
            """, tuple(id_to_score.keys()))

            for row in cursor.fetchall():
                record_dict = dict(row)
                record_dict["record_type"] = rtype
                
                # Deserialize JSON columns
                for col in ["steps", "report", "tags", "value", "vector", "metadata"]:
                    if col in record_dict and record_dict[col] is not None:
                        record_dict[col] = json.loads(record_dict[col])

                score = id_to_score[record_dict[id_col]]
                fts_hits[record_dict[id_col]] = (score, record_dict)

        # 2. Vector Cosine Similarity
        scored_results: List[Tuple[float, Dict[str, Any]]] = []
        for mid, (fts_score, record) in fts_hits.items():
            vector = record.get("vector")
            vector_score = 0.0
            
            if query_vector is not None and vector is not None:
                vector_score = self._cosine_similarity(query_vector, vector)
                
            normalized_fts = math.tanh(fts_score) if fts_score > 0 else 0.0
            combined_score = 0.7 * vector_score + 0.3 * normalized_fts
            scored_results.append((combined_score, record))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:limit]]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)
