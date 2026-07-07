# Override — System Architecture

## Purpose

This document defines the technical architecture of Override.

Unlike PROJECT.md and VISION.md, this document is implementation-oriented.

It answers:

- What already exists?
- What will be reused?
- What will be rewritten?
- What new systems will be built?
- How does everything connect together?

This document is the blueprint for engineering work.

---

# Current Foundation

Override is currently built on top of the existing JARVIS repository.

JARVIS is treated as a **reference implementation and initial codebase**, not the final architecture.

The goal is to evolve this repository into Override through incremental refactoring rather than rewriting everything at once.

---

# Current Working Components

The following capabilities already exist inside the repository and should be preserved until better replacements exist.

## Voice

Status: ✅ Working

Capabilities

- Speech recognition
- Audio streaming
- Wake interactions
- Voice conversations

Future

Will remain but become one input source into the Override planner.

---

## Desktop Automation

Status: ✅ Working

Capabilities

- Mouse movement
- Keyboard input
- Window interaction
- Application launching

Future

Will become the Execution Engine.

---

## Browser Automation

Status: ✅ Working

Capabilities

- Open browser
- Search
- Scroll
- Click
- Navigate

Future

Will become one execution provider.

---

## Vision

Status: ✅ Basic

Capabilities

- Screen capture
- Vision model support

Future

Will evolve into the Perception System.

---

## Tool Calling

Status: ✅ Working

Future

Will be integrated into the Planner instead of being directly exposed.

---

## Conversation

Status: ✅ Working

Future

Will become one interface to the cognitive runtime.

---

# Systems To Keep

Current modules worth keeping.

- Voice pipeline
- Browser automation
- Desktop automation
- Audio streaming
- Threading model
- Tool execution framework

These should be refactored rather than rewritten.

---

# Systems To Replace

The following architecture should gradually disappear.

- Direct LLM → Tool execution
- Monolithic control flow
- Prompt-driven execution
- Tight coupling between voice and actions

These will be replaced by modular cognition.

---

# New Systems To Build

Override introduces completely new subsystems.

These currently DO NOT exist.

## Observation Engine

Collects information.

Does not understand it.

---

## Perception Engine

Converts observations into structured knowledge.

---

## Context Engine

Maintains current world state.

---

## Planner

Converts goals into executable plans.

---

## Reasoning Engine

Analyzes situations.

Produces decisions.

---

## Verification Engine

Confirms actions actually succeeded.

---

## Memory Engine

Stores long-term knowledge.

---

## Goal Engine

Tracks long-running user goals.

Example

User wants to become a backend engineer.

Override remembers this for months.

If the user spends three hours watching YouTube unrelated to their goal, Override can detect the deviation and remind them.

---

## Behavior Engine

Identifies recurring habits.

Examples

- procrastination
- repeated failures
- productive routines
- workflow optimizations

This is an advisory system.

It never overrides user control.

---

# Overall Architecture

```
                    User

                      │

              Voice / UI / Chat

                      │

             Observation Engine

                      │

             Perception Engine

                      │

              Context Engine

                      │

             Reasoning Engine

                      │

                  Planner

                      │

          ┌───────────┼───────────┐

          ▼           ▼           ▼

 Desktop      Browser      External Tools

 Automation   Automation

          └───────────┼───────────┘

                      ▼

             Verification Engine

                      ▼

               Memory Engine
```

---

# Migration Strategy

Phase 1

Keep existing JARVIS working.

Do not break functionality.

Phase 2

Replace one subsystem at a time.

Phase 3

Move logic into modular services.

Phase 4

Remove obsolete JARVIS code.

Phase 5

Override becomes independent.

---

# Engineering Rule

Working code should not be rewritten simply because it can be.

A subsystem should only be replaced if:

- architecture improves
- maintainability improves
- performance improves
- scalability improves
- security improves

Otherwise evolve the existing implementation.