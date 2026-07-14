# Brain Index

This index defines document ownership, authority, conflict resolution, and update cadence for the Override Brain.

## Authority hierarchy

1. Product constitution: `00_PRODUCT_BIBLE.md`, `01_PRODUCT_PHILOSOPHY.md`, `02_FINAL_VISION.md`.
2. Experience constitution: `03_USER_EXPERIENCE.md`, `04_INTERACTION_PHILOSOPHY.md`, `05_UI_PHILOSOPHY.md`.
3. Architecture constitution: `10_SYSTEM_ARCHITECTURE.md` through `18_EXECUTION_AND_VERIFICATION.md`.
4. Engineering governance: `20_ENGINEERING_GUIDELINES.md`, `21_ARCHITECTURAL_DECISIONS.md`, `22_MILESTONES.md`.
5. Operational truth: `23_CURRENT_STATE.md`.
6. Definitions: `24_GLOSSARY.md`.

If lower-authority documents conflict with higher-authority documents, the higher-authority document wins. If implementation conflicts with the Brain, implementation is treated as incomplete until an ADR intentionally changes the Brain.

## Document ownership

| File | Owns | Update cadence |
|---|---|---|
| `README.md` | How to use the Brain | Rare |
| `BRAIN_INDEX.md` | Table of contents, authority, conflict rules | Rare |
| `00_PRODUCT_BIBLE.md` | Finished product as users experience it | Almost never |
| `01_PRODUCT_PHILOSOPHY.md` | Why Override exists and what it must never become | Almost never |
| `02_FINAL_VISION.md` | Five-year and ten-year destination | Rare |
| `03_USER_EXPERIENCE.md` | Concrete usage moments and journeys | Rare |
| `04_INTERACTION_PHILOSOPHY.md` | Voice, silence, permission, Chief Engineer behavior | Rare |
| `05_UI_PHILOSOPHY.md` | Task-adaptive UI and anti-dashboard rules | Rare |
| `10_SYSTEM_ARCHITECTURE.md` | High-level subsystem map | Rare |
| `11_RUNTIME_ARCHITECTURE.md` | Lifecycle, DI, events, modules, recovery | Occasional |
| `12_WORLD_MODEL.md` | Entities, relationships, persistence, context evolution | Occasional |
| `13_WORKSPACE_INTELLIGENCE.md` | Apps, projects, repos, tabs, docs, services, sessions | Occasional |
| `14_AGENT_ORCHESTRATION.md` | Planner, specialized agents, delegation, approval, recovery | Occasional |
| `15_PROVIDER_SYSTEM.md` | Provider abstraction, capabilities, permissions | Occasional |
| `16_REASONING_ENGINE.md` | Reasoning inputs, outputs, decisions, confidence | Occasional |
| `17_MEMORY_AND_KNOWLEDGE.md` | Episodic, semantic, procedural memory and knowledge | Occasional |
| `18_EXECUTION_AND_VERIFICATION.md` | Action lifecycle, verification, rollback, retry, safety | Occasional |
| `20_ENGINEERING_GUIDELINES.md` | Engineering rules and definitions of done/frozen | Occasional |
| `21_ARCHITECTURAL_DECISIONS.md` | ADR history | Append-only |
| `22_MILESTONES.md` | Roadmap and acceptance criteria | Regular |
| `23_CURRENT_STATE.md` | Current milestone, blockers, repository status | Frequent |
| `24_GLOSSARY.md` | Canonical definitions | Occasional |

## Conflict resolution

1. Identify the owning document for the topic.
2. Check product constitution before architecture.
3. Check architecture before current implementation.
4. If a real change is needed, add an ADR before updating dependent documents.
5. Do not silently change product intent to fit existing code.
