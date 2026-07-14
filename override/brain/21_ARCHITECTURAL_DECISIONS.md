# Architectural Decisions

This document is append-only. Never delete history. Supersede decisions with new entries.

## ADR-0001 — Override is a local-first Agentic Operating Layer, not an OS replacement

Date: 2026-07-13

Status: Accepted

Decision: Override runs above host operating systems and owns cognition, context, planning, execution coordination, verification, and memory. The host OS owns kernel, drivers, filesystems, networking, and hardware management.

Reason: This preserves portability, safety, and practical deliverability.

Alternatives: Build an operating system or desktop environment. Rejected because it conflicts with product scope and would dilute the cognitive-runtime mission.

Impact: Architecture must use providers and PAL instead of replacing OS responsibilities.

## ADR-0002 — Product Bible has highest product authority

Date: 2026-07-13

Status: Accepted

Decision: `00_PRODUCT_BIBLE.md` is the primary finished-product source. Architecture and implementation must align with it.

Reason: Multiple AI tools need one stable product north star.

Alternatives: Let current implementation drive architecture. Rejected because it risks preserving prototype limitations.

Impact: Conflicts resolve in favor of product constitution unless a later ADR changes it.

## ADR-0003 — Current State is the only frequently changing status document

Date: 2026-07-13

Status: Accepted

Decision: `23_CURRENT_STATE.md` owns live operational state. Other documents should not duplicate implementation status.

Reason: Multiple live status documents caused contradictions.

Alternatives: Keep status in many documents. Rejected because it creates drift.

Impact: Future status updates belong in `23_CURRENT_STATE.md`.
