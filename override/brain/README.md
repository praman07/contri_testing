# Override Brain

The Override Brain is the permanent, vendor-independent knowledge base for building Override: a local-first Agentic Operating Layer that runs on top of Windows, macOS, Linux, and future host environments.

It exists so any capable AI system or human engineer can read the same documents and converge on the same product vision, architecture, engineering standards, UI philosophy, and roadmap without depending on a particular model vendor, IDE, or implementation era.

## How every AI should use this Brain

1. Read `BRAIN_INDEX.md` first.
2. Read the product documents before architecture documents.
3. Read architecture documents before engineering or milestone documents.
4. Treat `00_PRODUCT_BIBLE.md`, `01_PRODUCT_PHILOSOPHY.md`, and `02_FINAL_VISION.md` as product constitution documents.
5. Treat `23_CURRENT_STATE.md` as the only frequently changing operational status document.
6. If documents conflict, follow the authority hierarchy in `BRAIN_INDEX.md` and record the resolution in `21_ARCHITECTURAL_DECISIONS.md`.

## Reading order

1. `00_PRODUCT_BIBLE.md`
2. `01_PRODUCT_PHILOSOPHY.md`
3. `02_FINAL_VISION.md`
4. `03_USER_EXPERIENCE.md`
5. `04_INTERACTION_PHILOSOPHY.md`
6. `05_UI_PHILOSOPHY.md`
7. `10_SYSTEM_ARCHITECTURE.md` through `18_EXECUTION_AND_VERIFICATION.md`
8. `20_ENGINEERING_GUIDELINES.md`
9. `21_ARCHITECTURAL_DECISIONS.md`
10. `22_MILESTONES.md`
11. `23_CURRENT_STATE.md`
12. `24_GLOSSARY.md`

## Immutable vs evolving files

Nearly immutable: product bible, philosophy, final vision, interaction philosophy, UI philosophy, system architecture, glossary terms. These change only through explicit architectural decision records.

Evolving: runtime architecture, provider system, reasoning, memory, execution, milestones, current state, and ADR log. `23_CURRENT_STATE.md` changes most often.

## Maintenance rules

- Every document owns one primary question.
- Do not duplicate large sections; reference the owning document.
- Separate product intent, architecture, engineering process, and implementation status.
- Never let implementation convenience redefine the product.
- Every change must move Override closer to the final product vision.
