import os
import json
import sqlite3
import math
import uuid
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("Override.Memory.SAL")

class IStorageAbstractionLayer(ABC):
    """
    Storage Abstraction Layer interface.
    Decouples database operations (SQL, Vector indexing, CRUD) from the core MemoryEngine.
    """

    @abstractmethod
    def initialize_schema(self) -> None:
        """Applies database migrations, indexes, and schema definitions."""
        pass

    @abstractmethod
    def insert_record(self, memory_type: str, record: Dict[str, Any]) -> None:
        """Inserts a memory record into the database."""
        pass

    @abstractmethod
    def search_hybrid(
        self, 
        query_vector: Optional[List[float]], 
        query_text: str, 
        limit: int,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a technology-agnostic hybrid search matching text tokens and vector values.
        """
        pass

    @abstractmethod
    def delete_record(self, record_id: str) -> bool:
        """Deletes a record matching the ID from all memory tables."""
        pass

    @abstractmethod
    def get_unconsolidated_records(self, limit: int) -> List[Dict[str, Any]]:
        """Fetches episodic records that have not been consolidated yet."""
        pass

    @abstractmethod
    def mark_records_consolidated(self, record_ids: List[str]) -> None:
        """Flags specified records as consolidated."""
        pass


class SQLiteSAL(IStorageAbstractionLayer):
    """
    Concrete SQLite implementation of IStorageAbstractionLayer.
    Encapsulates all SQL syntax and implements flat-vector indexing using Python-based Cosine Similarity.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._fts_supported = True

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, timeout=10.0)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.error(f"Error closing SQLite database connection: {e}")
            finally:
                self._conn = None

    def initialize_schema(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Core tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                salience REAL DEFAULT 1.0,
                vector TEXT,
                metadata TEXT,
                tags TEXT,
                consolidated INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                memory_id TEXT PRIMARY KEY,
                fact TEXT NOT NULL,
                entity TEXT,
                relationship TEXT,
                confidence REAL DEFAULT 1.0,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedural_memories (
                memory_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                steps TEXT NOT NULL,
                success_rate REAL DEFAULT 1.0,
                timestamp TEXT NOT NULL,
                vector TEXT,
                metadata TEXT
            )
        """)

        # 2. Add indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_memories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodic_consolidated ON episodic_memories(consolidated)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_semantic_timestamp ON semantic_memories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedural_timestamp ON procedural_memories(timestamp)")

        # 3. Create FTS5 Virtual Tables
        try:
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(memory_id UNINDEXED, content)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(memory_id UNINDEXED, content)")
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS procedural_fts USING fts5(memory_id UNINDEXED, content)")
            self._fts_supported = True
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 is not supported by current SQLite build. Falling back to SQL filtering. Error: {e}")
            self._fts_supported = False

        conn.commit()

    def insert_record(self, memory_type: str, record: Dict[str, Any]) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        # Ensure vector/metadata/tags are serialized properly
        vector_str = json.dumps(record.get("vector")) if record.get("vector") is not None else None
        metadata_str = json.dumps(record.get("metadata")) if record.get("metadata") is not None else None

        if memory_type == "episodic":
            tags_str = json.dumps(record.get("tags", []))
            cursor.execute("""
                INSERT INTO episodic_memories (memory_id, content, timestamp, salience, vector, metadata, tags, consolidated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["memory_id"],
                record["content"],
                record["timestamp"],
                record.get("salience", 1.0),
                vector_str,
                metadata_str,
                tags_str,
                record.get("consolidated", 0)
            ))
            
            if self._fts_supported:
                cursor.execute("""
                    INSERT INTO episodic_fts (memory_id, content) VALUES (?, ?)
                """, (record["memory_id"], record["content"]))

        elif memory_type == "semantic":
            cursor.execute("""
                INSERT INTO semantic_memories (memory_id, fact, entity, relationship, confidence, timestamp, vector, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["memory_id"],
                record["content"],
                record.get("entity", ""),
                record.get("relationship", ""),
                record.get("confidence", 1.0),
                record["timestamp"],
                vector_str,
                metadata_str
            ))
            
            if self._fts_supported:
                cursor.execute("""
                    INSERT INTO semantic_fts (memory_id, content) VALUES (?, ?)
                """, (record["memory_id"], record["content"]))

        elif memory_type == "procedural":
            steps_str = json.dumps(record.get("steps", []))
            cursor.execute("""
                INSERT INTO procedural_memories (memory_id, description, steps, success_rate, timestamp, vector, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record["memory_id"],
                record["content"],
                steps_str,
                record.get("success_rate", 1.0),
                record["timestamp"],
                vector_str,
                metadata_str
            ))
            
            if self._fts_supported:
                cursor.execute("""
                    INSERT INTO procedural_fts (memory_id, content) VALUES (?, ?)
                """, (record["memory_id"], record["content"]))
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

        conn.commit()

    def search_hybrid(
        self, 
        query_vector: Optional[List[float]], 
        query_text: str, 
        limit: int,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not memory_types:
            memory_types = ["episodic", "semantic", "procedural"]

        results: List[Dict[str, Any]] = []
        conn = self._get_connection()
        cursor = conn.cursor()

        # Step 1: Lexical query (FTS5 or standard LIKE fallbacks)
        fts_hits: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # memory_id -> (score, record)
        
        # Build list of memory items matched by keyword
        for mtype in memory_types:
            table_name = f"{mtype}_memories"
            content_col = "content" if mtype == "episodic" else ("fact" if mtype == "semantic" else "description")
            
            matched_ids: List[Tuple[str, float]] = []
            
            if self._fts_supported and query_text.strip():
                # FTS5 search
                fts_table = f"{mtype}_fts"
                try:
                    # Escape query_text slightly or search exactly
                    sanitized_query = query_text.replace('"', '').replace("'", "")
                    cursor.execute(f"""
                        SELECT memory_id, rank 
                        FROM {fts_table} 
                        WHERE content MATCH ? 
                        ORDER BY rank 
                        LIMIT ?
                    """, (f"{sanitized_query}*", limit * 2))
                    matched_ids = [(row["memory_id"], -row["rank"]) for row in cursor.fetchall()]
                except sqlite3.OperationalError as e:
                    logger.warning(f"FTS query failed, falling back to LIKE: {e}")
                    matched_ids = []

            # Fallback to standard LIKE filtering if FTS not supported or returned nothing
            if not matched_ids and query_text.strip():
                like_pattern = f"%{query_text}%"
                cursor.execute(f"""
                    SELECT memory_id 
                    FROM {table_name} 
                    WHERE {content_col} LIKE ? 
                    LIMIT ?
                """, (like_pattern, limit * 2))
                matched_ids = [(row["memory_id"], 1.0) for row in cursor.fetchall()]

            # If no query text was provided, match all items
            if not query_text.strip():
                cursor.execute(f"SELECT memory_id FROM {table_name} LIMIT ?", (limit * 2,))
                matched_ids = [(row["memory_id"], 0.0) for row in cursor.fetchall()]

            if not matched_ids:
                continue

            # Load actual records
            ids_placeholder = ",".join(["?"] * len(matched_ids))
            id_to_score = {mid: score for mid, score in matched_ids}
            
            cursor.execute(f"""
                SELECT * FROM {table_name} 
                WHERE memory_id IN ({ids_placeholder})
            """, tuple(id_to_score.keys()))
            
            for row in cursor.fetchall():
                record = self._row_to_dict(mtype, row)
                score = id_to_score[record["memory_id"]]
                fts_hits[record["memory_id"]] = (score, record)

        # Step 2: Compute vector similarity
        scored_results: List[Tuple[float, Dict[str, Any]]] = []
        
        for mid, (fts_score, record) in fts_hits.items():
            vector = record.get("vector")
            vector_score = 0.0
            
            if query_vector is not None and vector is not None:
                vector_score = self._cosine_similarity(query_vector, vector)
            
            # Reciprocal Rank Fusion / Weighted combining
            # Simple combined score: 0.7 * VectorSimilarity + 0.3 * NormalizedLexicalScore
            # Lexical score is normalized roughly using sigmoid or flat scale
            normalized_fts = math.tanh(fts_score) if fts_score > 0 else 0.0
            combined_score = 0.7 * vector_score + 0.3 * normalized_fts
            scored_results.append((combined_score, record))

        # Sort and limit
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_results[:limit]]

    def delete_record(self, record_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        deleted = False

        for table in ["episodic", "semantic", "procedural"]:
            cursor.execute(f"DELETE FROM {table}_memories WHERE memory_id = ?", (record_id,))
            if cursor.rowcount > 0:
                deleted = True
            if self._fts_supported:
                cursor.execute(f"DELETE FROM {table}_fts WHERE memory_id = ?", (record_id,))

        conn.commit()
        return deleted

    def get_unconsolidated_records(self, limit: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM episodic_memories 
            WHERE consolidated = 0 
            ORDER BY timestamp ASC 
            LIMIT ?
        """, (limit,))
        return [self._row_to_dict("episodic", row) for row in cursor.fetchall()]

    def mark_records_consolidated(self, record_ids: List[str]) -> None:
        if not record_ids:
            return
        conn = self._get_connection()
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(record_ids))
        cursor.execute(f"""
            UPDATE episodic_memories 
            SET consolidated = 1 
            WHERE memory_id IN ({placeholders})
        """, tuple(record_ids))
        conn.commit()

    def _row_to_dict(self, memory_type: str, row: sqlite3.Row) -> Dict[str, Any]:
        record = dict(row)
        record["memory_type"] = memory_type
        
        # Deserialize fields
        if "vector" in record and record["vector"] is not None:
            record["vector"] = json.loads(record["vector"])
        if "metadata" in record and record["metadata"] is not None:
            record["metadata"] = json.loads(record["metadata"])
        if "tags" in record and record["tags"] is not None:
            record["tags"] = json.loads(record["tags"])
        if "steps" in record and record["steps"] is not None:
            record["steps"] = json.loads(record["steps"])

        # Normalize content key based on type
        if memory_type == "semantic":
            record["content"] = record.get("fact", "")
        elif memory_type == "procedural":
            record["content"] = record.get("description", "")

        return record

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)
