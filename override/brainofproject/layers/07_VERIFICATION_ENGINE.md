# Layer 07 — Verification Engine

## Purpose

Verifies executed actions and plans against expected post-conditions and outcomes.

---

## Owns

- Post-execution verification logic (outcome checks)
- Parsing of step/plan expected post-conditions
- Deterministic verification rules (file existence, process tracking)
- Non-deterministic verification rules (mock or VLM layout audits)
- Suggesting recovery recipes and retries on verification failure

---

## Never Owns

- Direct action execution (owned by Layer 06)
- Plan generation and decomposition (owned by Layer 05)
- Raw environmental signal collection (owned by Layer 01)
- Storing or consolidating long-term episodic memories (owned by Layer 04)

---

## Inputs

- ExecutionResult from Layer 06 Execution Engine
- Host state updates (via Environment and Perception Engines)

---

## Outputs

- VerificationReport

---

## Called By

- Runtime Foundation

---

## Calls

- Environment Engine
- Perception Engine

---

## Publishes

- `verification.started`
- `verification.passed`
- `verification.failed`
- `verification.retry_suggested`
- `verification.user_confirmation_required`

---

## Subscribes

- `execution.task_completed`
- `execution.task_failed`

---

## Performance Requirements

- Real-time outcome validation immediately post-execution
- Timeout handling for long-running verification checks
- Minimum latency on deterministic file/process existence queries

---

## Success Criteria

- Accurately reports whether execution plans successfully achieved target states.
- Recommends actionable recovery steps when verification fails.
