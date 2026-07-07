# Layer 04 — Memory Engine

## 1. Purpose
The Memory Engine provides a durable, persistent, and queryable store of the agent's experiences, knowledge, and operational patterns. It enables the cognitive runtime to learn from past execution, adapt to user behaviors, recall long-term facts, and establish historical continuity across sessions.

---

## 2. Subsystem Boundaries & Ownership

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COGNITIVE SUBSYSTEMS                            │
│                                                                        │
│   ┌───────────────────┐    ┌──────────────────┐    ┌───────────────┐   │
│   │  Context Engine   │    │  Planner Engine  │    │  Goal Engine  │   │
│   └─────────┬─────────┘    └────────┬─────────┘    └───────┬───────┘   │
└─────────────┼───────────────────────┼──────────────────────┼───────────┘
              │                       │                      │            
              ▼                       ▼                      ▼            
   ┌─────────────────────────────────────────────────────────────────┐    
   │                          IEventBus                              │    
   └──────────────────────────┬──────────────────────────────────────┘    
                              │                                           
                              ▼                                           
┌─────────────────────────────┼──────────────────────────────────────────┐
│                             │ Layer 04 — Memory Engine                 │
│                             ▼                                          │
│                    ┌──────────────────┐                                │
│                    │   MemoryEngine   │                                │
│                    └────────┬─────────┘                                │
│                             │                                          │
│                             ▼                                          │
│               ┌───────────────────────────┐                            │
│               │ Storage Abstraction (SAL) │                            │
│               └─────────────┬─────────────┘                            │
│                             │                                          │
│              ┌──────────────┴──────────────┐                           │
│              ▼                             ▼                           │
│      ┌───────────────┐             ┌───────────────┐                   │
│      │   SQLiteSAL   │             │   VectorSAL   │                   │
│      │ (Metadata/FTS)│             │  (Embeddings) │                   │
│      └───────────────┘             └───────────────┘                   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1. Responsibilities
* **Long-Term Persistence**: Store episodic, semantic, and procedural facts securely.
* **Storage Abstraction**: Encapsulate all database-specific query operations (SQL, Vector indexing, Key-Value) behind a backend-agnostic interface.
* **Semantic Retrieval**: Support hybrid queries utilizing both Full-Text Search (keyword-matching) and Vector Cosine Similarity.
* **Memory Lifecycle (Consolidation & Decay)**: Manage retention via temporal decay formulas and schedule background consolidation threads (compressing episodic fragments into consolidated semantic summaries).
* **Data Sanitization**: Screen and redact sensitive data (PII, credentials, credentials-matching patterns) before saving to disk.

### 2.2. Non-responsibilities
* **Working Context Management**: The Memory Engine does **not** track the current real-time state of the screen, active window, or execution stack. This is the exclusive responsibility of the **Context Engine**.
* **Planning & Execution**: The Memory Engine does **not** make decisions on which actions to run, nor does it generate plans. It only provides historical logs of past plans when queried.
* **Embedding Generation**: The Memory Engine does **not** calculate vector embeddings. It delegates all vectorization requests to an external, container-registered model service via the `IEmbeddingService` interface.

---

## 3. Public Interfaces & Contracts

Subsystems communicate with the Memory Engine using versioned interfaces registered in the Service Container.

### 3.1. Versioned Interface Definitions

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IEmbeddingService(ABC):
    """External dependency registered in the DI container. Memory Engine consumes this
    to retrieve vector representations of text without executing ML logic itself.
    """
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generates a dense vector representation of the given text.
        
        Returns a list of floats (e.g. 384 or 768 dimensions).
        """
        pass


class IMemoryEngine_v1(ABC):
    """Versioned public contract for Memory operations."""

    @abstractmethod
    async def store_episodic(self, content: str, metadata: Dict[str, Any], tags: List[str]) -> str:
        """Stores a trace of a runtime event, action, or user interaction."""
        pass

    @abstractmethod
    async def store_semantic(self, fact: str, entity: str, relationship: str, confidence: float) -> str:
        """Stores a general fact, user preference, or system parameter."""
        pass

    @abstractmethod
    async def store_procedural(self, description: str, steps: List[Dict[str, Any]], success_rate: float) -> str:
        """Stores successful action sequences or automation workflows."""
        pass

    @abstractmethod
    async def query(
        self, 
        query_text: str, 
        limit: int = 5, 
        memory_types: Optional[List[str]] = None, 
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Performs a technology-agnostic hybrid search (vector similarity + lexical FTS) 
        over stored memories.
        """
        pass

    @abstractmethod
    async def forget(self, memory_id: str) -> bool:
        """Explicitly deletes a specific memory item from the database (user-triggered)."""
        pass

    @abstractmethod
    async def consolidate(self) -> None:
        """Triggers background compression and summarization of episodic traces."""
        pass
```

### 3.2. Data Contracts
Memory objects returned by the engine are immutable dictionaries or structured frozen dataclasses mapping to the following schemas:

#### Memory Record Schema
```
MemoryRecord
  memory_id   : str (UUIDv4)
  memory_type : str ("episodic" | "semantic" | "procedural")
  content     : str
  timestamp   : str (ISO 8601 UTC)
  salience    : float (0.0 to 1.0)
  relevance   : float (0.0 to 1.0, calculated dynamically at query time)
  vector      : List[float] (nullable)
  metadata    : Dict[str, Any]
```

---

## 4. Storage Abstraction Layer (SAL)

To prevent coupling to any specific database technology, all data queries pass through the `IStorageAbstractionLayer`. This interface exposes capabilities (hybrid matching, CRUD) rather than database-specific queries or syntax.

```python
class IStorageAbstractionLayer(ABC):
    @abstractmethod
    def initialize_schema(self) -> None:
        """Applies migrations, index schemas, and table layouts."""
        pass

    @abstractmethod
    def insert_record(self, record: Dict[str, Any]) -> None:
        """Inserts a raw record into the underlying database."""
        pass

    @abstractmethod
    def search_hybrid(
        self, 
        query_vector: List[float], 
        query_text: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Executes a technology-agnostic hybrid search matching text tokens and vector values.
        
        No database-specific syntax (such as SQLite MATCH or PostgreSQL operators) is exposed.
        """
        pass

    @abstractmethod
    def delete_record(self, record_id: str) -> bool:
        """Deletes a record matching the ID."""
        pass

    @abstractmethod
    def get_unconsolidated_records(self, limit: int) -> List[Dict[str, Any]]:
        """Fetches old episodic records that require summarization."""
        pass
```

### Default Implementation: `SQLiteSAL`
The default storage provider is **SQLite**, leveraging:
1. **FTS5 extension** internally for keyword matching.
2. **Standard SQL tables** with indexing on metadata keys.
3. **Flat-vector indexing table** with Cosine Distance calculations executed in Python (or using `sqlite-vec` extension where available). All SQL dialect quirks are fully contained within this implementation.

---

## 5. Event Specifications

The Memory Engine interacts asynchronously using the `IEventBus`.

### 5.1. Event Subscriptions
* `perception.frame_ready` -> Analyzed for episodic logging. If a frame contains critical changes, it is queued for episodic storage.
* `context.updated` -> Used to log workspace state transitions.
* `planner.action_executed` -> Logs execution history, step parameters, and outcomes for procedural memory reinforcement.
* `system.shutdown` -> Triggers immediate write cache flush to disk.

### 5.2. Event Publications
* `memory.ingested` -> Published when a memory record is written to disk.
  * Payload: `{"memory_id": str, "memory_type": str, "timestamp": str}`
* `memory.retrieved` -> Published when a search query is answered, notifying systems of recall context.
  * Payload: `{"query": str, "returned_count": int}`
* `memory.consolidated` -> Published when background consolidation finishes.
  * Payload: `{"source_records_compressed": int, "created_summaries": int}`
* `memory.engine.started` / `memory.engine.stopped` -> Standard lifecycle events.

---

## 6. Memory Lifecycle, Retrieval, & Privacy

### 6.1. Retrieval Strategy (Query-Time Decay)
Relevance scoring is calculated **dynamically at query time**. This approach is deterministic, reversible, computationally inexpensive, and preserves the underlying raw data.

$$\text{Relevance Score} = w_v \cdot \text{VectorSimilarity} + w_f \cdot \text{FtsScore} - \lambda \cdot (T_{\text{current}} - T_{\text{memory}})$$

* $\lambda$ = Exponential time decay coefficient.
* $w_v, w_f$ = Weights adjusting the importance of semantic versus exact matches.
* By computing decay dynamically, memories are never modified or degraded on disk; their retrieval rank is adjusted on-the-fly.

### 6.2. Lifecycle and Consolidation
* **No Destructive Erasure**: Raw episodic memories are **never** aggressively deleted during normal lifecycles.
* **Semantic Consolidation**: A low-priority background thread wakes up when system load is low. It fetches unconsolidated episodic records, clusters them semantically, prompts a local model to generate summary facts, and inserts the summaries into **Semantic Memory**. The source episodic records are marked as `consolidated=True` to exclude them from default queries while keeping them queryable for historical audits.

### 6.3. Layered Privacy & Data Security (Defense-in-Depth)
The Memory Engine enforces a layered privacy layout to ensure local-first security:
1. **First-Stage Filtering (Upstream)**: The Perception Engine and Context Engine scan input streams and redact obvious secrets, credentials, or exclude logging when security-sensitive applications are active (e.g. password managers).
2. **Second-Stage Validation (In-Engine)**: Before writing to persistence, the Memory Engine runs regex validation sweeps over content strings to redact credit cards, SSNs, and common API key patterns.
3. **Database Security**: Database files are stored inside user profile spaces with OS-level file permissions restricted to the execution user context.

---

## 7. Integration Architecture

* **Context Engine**: Context periodically queries `IMemoryEngine` to retrieve related historical facts matching the current application and active task. These facts are added to the active working context.
* **Planner Engine**: Before generating an execution plan, the Planner queries procedural memory to recall past sequences that resolved similar goals successfully.
* **Verification Engine**: The outcome of action runs is written to procedural memory, increasing the success rating of the sequence if it succeeded, or flagging failure to decrease salience.

---

## 8. Failure Handling & Resiliency

* **Database Corruption**: If the SQLite file becomes corrupt, the engine backs up the corrupt file to `<app_data>/corrupt_memory_<timestamp>.db` and automatically initializes a fresh database schema to ensure the runtime remains operational.
* **Embedding Service Downtime**: If the `IEmbeddingService` is unavailable or throws errors, the Memory Engine falls back automatically to keyword-only (FTS5) searching, logging a warning but continuing to resolve queries.
* **Lock Timeouts**: Writes utilize a memory queue with retry limits. If the database file is locked (e.g. during manual exports), writes queue up to a maximum of 1,000 records before raising a non-blocking `StorageBusyException`.
* **Out of Disk Space**: If write operations fail due to disk space limits, the engine suspends ingestion, publishes `memory.ingestion_suspended`, and runs in read-only mode to prevent crash-loops.

---

## 9. Testing Strategy & Acceptance Criteria

### 9.1. Testing Protocols
* **Storage Swappability Tests**: Assert that a mock SAL can replace `SQLiteSAL` with zero code modifications inside `MemoryEngine`.
* **Privacy Redaction Unit Tests**: Run inputs containing credentials and verify that the data saved in the mock database contains redaction markers.
* **Concurrency and Thread Safety Tests**: Publish 100 concurrent `perception.frame_ready` events from multiple threads and verify that the database handles writes without locking conflicts or data corruption.
* **Leak Detection**: Validate that the background consolidation thread exits cleanly and releases all file locks on shutdown.

### 9.2. Acceptance Criteria
* **No Direct imports**: Memory must never import Planner, Context, or Goal modules. All interactions occur via interfaces or Event Bus.
* **Memory Limits**: Memory footprint of the idle engine must remain under 30MB.
* **Latency Limits**: Query operations over 10,000 records must complete in less than 20ms.
* **Model Agnostic**: Can run without an active LLM by substituting fallback keyword indexing.
* **Unchanged Foundation**: No existing code in `override/runtime/` is modified.
