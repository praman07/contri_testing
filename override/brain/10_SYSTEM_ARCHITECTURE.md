# System Architecture

Override is organized as a local-first cognitive runtime above the host operating system.

## Subsystems

Observation collects raw signals. Perception turns signals into structured facts. Environment tracks host state. World Model fuses context over time. Workspace Intelligence understands projects, apps, tabs, docs, services, and sessions. Memory and Knowledge preserve history. Reasoning evaluates context and goals. Planner creates actionable plans. Agent Orchestration delegates work. Providers execute approved actions. Verification checks outcomes. UI presents state, approvals, and evidence.

## Communication

Subsystems communicate through stable interfaces and events. Direct coupling is allowed only where a synchronous query interface is explicitly owned and documented.

## Ownership

Each subsystem owns exactly one category of responsibility. Observation never reasons. Reasoning never executes. Providers never decide product goals. UI never owns business logic.

## Dependencies

Product intent drives architecture. Architecture drives runtime. Runtime drives implementation. Implementation never redefines product intent without an ADR.
