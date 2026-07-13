# Layer 08 — Memory Consolidation & Knowledge Engine

## 1. Purpose

The Memory Consolidation & Knowledge Engine represents the long-term cognitive persistence layer of Override. 
While early layers focus on immediate environmental capture and execution contexts, Layer 08 acts as the repository of consolidated experiences:
* Validating and logging plan outcomes.
* Distilling successful action plans into reusable workflows.
* Extracting general semantic knowledge from repeated executions.
* Learning patterns and failure rates of execution behaviors.
* Providing semantic querying capabilities to higher-level planners and reasoning engines.

---

## 2. Subsystem Boundaries & Ownership

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COGNITIVE SUBSYSTEMS                            │
│                                                                        │
│   ┌───────────────────┐    ┌──────────────────┐    ┌───────────────┐   │
│   │ Verification Engine│    │ Reasoning Engine │    │  Goal Engine  │   │
│   │     (Layer 07)    │    │    (Layer 09)    │    │    (Layer 10) │   │
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
│                             │ Layer 08 — Knowledge Engine              │
│                             ▼                                          │
│                    ┌──────────────────┐                                │
│                    │  KnowledgeEngine  │                                │
│                    └────────┬─────────┘                                │
│                             │                                          │
│                             ▼                                          │
│               ┌───────────────────────────┐                            │
│               │ Storage Abstraction (SAL) │                            │
│               └─────────────┬─────────────┘                            │
│                             │                                          │
│                       ┌─────┴─────┐                                    │
│                       ▼           ▼                                    │
│               SQLite DB     FTS5 Virtual                               │
│            (knowledge.db)     Tables                                   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1. Responsibilities
* **Durable Consolidation**: Subscribe to verification outcomes (`verification.passed`/`verification.failed`) to persist task results.
* **Workflow Distillation**: Auto-extract successful plan steps into reusable workflows.
* **Pattern Learning**: Accumulate success/failure metrics to identify fragile steps or common errors.
* **Semantic Retrieval**: Respond to search requests using lexical search with hybrid vector fallback.
* **Compaction**: Periodically merge redundant records or clean up historical logs.

### 2.2. Non-responsibilities
* **Real-time Observation**: Layer 08 does not subscribe to OCR or raw input streams.
* **Planning / Execution**: Layer 08 does not create execution plans or trigger actions.
* **Reasoning / Validation**: Layer 08 does not decide whether a plan succeeded; it relies purely on Layer 07 reports.

---

## 3. Storage Schema & Models

Layer 08 uses a decoupled storage backend (`IKnowledgeStore` / `SQLiteKnowledgeStore`) pointing to `data/knowledge.db`.

### 3.1. Tables

#### Workflows (`workflows`)
Stores reusable task sequences:
* `workflow_id` (TEXT, Primary Key)
* `name` (TEXT, Index)
* `steps` (TEXT, JSON representation of steps)
* `frequency` (INTEGER, count of times used)
* `timestamp` (TEXT)

#### Task Outcomes (`task_outcomes`)
Tracks the outcomes of past plan executions:
* `outcome_id` (TEXT, Primary Key)
* `plan_id` (TEXT, Index)
* `correlation_id` (TEXT)
* `success` (INTEGER, Boolean flag)
* `report` (TEXT, JSON representation of findings)
* `timestamp` (TEXT)

#### Semantic Knowledge (`semantic_knowledge`)
Holds facts, user preferences, and configurations:
* `knowledge_id` (TEXT, Primary Key)
* `topic` (TEXT, Index)
* `content` (TEXT)
* `tags` (TEXT, JSON list of tags)
* `timestamp` (TEXT)

#### Patterns (`patterns`)
Contains learned execution heuristics and performance counters:
* `pattern_id` (TEXT, Primary Key)
* `key` (TEXT, Unique index)
* `value` (TEXT, JSON representation of stats)
* `timestamp` (TEXT)

---

## 4. Published & Subscribed Events

### 4.1. Subscriptions
* `verification.passed`: Receives details of a successfully verified plan.
* `verification.failed`: Receives details of a failed verification report.
* `memory.store_requested`: Manual request to store workflows, outcomes, or knowledge.
* `memory.retrieve_requested`: Query request for semantic knowledge retrieval.
* `runtime.shutdown` / `system.shutdown`: Wires clean shutdown of storage resources.

### 4.2. Publications
* `memory.record_stored`: Published when a record is successfully saved.
* `memory.record_updated`: Published when an existing record is mutated.
* `memory.record_deleted`: Published when a record is forgotten.
* `memory.query_completed`: Published with search hits matching a retrieval request.
* `memory.compaction_completed`: Published when compaction merges or cleans up records.
