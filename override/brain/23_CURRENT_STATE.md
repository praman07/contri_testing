# Current State

This is the only frequently changing Brain document.

## Current milestone

Brain Constitution and documentation reorganization.

## Current architecture status

The repository contains valuable legacy JARVIS capabilities and an emerging Override runtime. The new Brain defines the intended long-term product and architecture. Existing code must be evaluated against this Brain before being treated as production architecture.

## Repository status

Existing documentation remains in `override/brainofproject/` for historical continuity. The canonical reorganized Brain lives in `override/brain/`.

## Known issues

- Previous Brain documents contained overlapping current-state claims.
- Reasoning, Behavior, UI philosophy, workspace intelligence, provider bridge, safety/privacy, and ADR ownership were underdefined.
- Existing implementation maturity must not be inferred from old “frozen” claims without verification.

## Blockers

- Provider bridge is not yet defined in implementation.
- Persistent world model and workspace intelligence require engineering design and acceptance tests.
- Current implementation must be reconciled with canonical Brain documents.

## Next engineering step

Use Milestone 1 and Milestone 2 to validate runtime foundation and real workspace observation before expanding autonomous behavior.
