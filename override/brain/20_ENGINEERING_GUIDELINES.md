# Engineering Guidelines

Engineering must preserve product intent, architectural clarity, and user trust.

## Principles

Understand before changing. Design before implementing. Keep modules independent. Prefer deterministic behavior. Avoid unnecessary abstraction. Verify before declaring completion.

## Coding rules

Use clear ownership, small interfaces, explicit errors, tests for behavior, and documentation for public contracts. Do not leave empty stubs or unresolved work markers.

## Testing philosophy

Tests must prove contracts, lifecycle, integration, provider safety, verification, memory persistence, and recovery. Mock tests are useful but cannot replace real provider validation.

## Definition of Done

A change is done when it is implemented, tested, documented, reviewed against the Brain, and verified against acceptance criteria.

## Definition of Frozen

A subsystem is frozen only when its public contracts, lifecycle, tests, failure modes, documentation, and integration are stable. “Implemented” does not mean frozen.

## Documentation rules

Every document owns one question. Avoid duplication. Update the owning document. Add ADRs for durable architectural choices.

## Review process

Review product alignment, architecture boundaries, safety, privacy, tests, documentation, and user experience impact.
