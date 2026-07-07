# Override

**Document ID:** PROJ-0001  
**Status:** Approved  
**Authority:** Level 1 (Highest)  
**Last Updated:** 2026-07-04  
**Owner:** Founding Architect

---

# Purpose

This document defines the identity of Override.

It answers one question only:

> **What is Override?**

Every future engineering, architecture, design, research, and implementation decision must align with this document.

If another document conflicts with this one, this document takes precedence unless an approved Architectural Decision Record (ADR) explicitly replaces part of it.

---

# What is Override?

Override is a **local-first cognitive runtime** that enables a computer to understand, reason about, and execute tasks within a user's digital environment.

Override is not designed to replace the operating system.

Instead, it runs on top of an existing operating system and continuously builds an understanding of the user's current digital workspace.

Its purpose is not simply to respond to prompts.

Its purpose is to perceive context, understand goals, plan actions, execute them safely, verify results, and continuously improve its understanding over time.

Override is designed to become a persistent cognitive layer between the user and the computer.

---

# What Override Is NOT

Override is **not**:

- A chatbot.
- A voice assistant.
- A Jarvis clone.
- A Cursor clone.
- A Copilot clone.
- A browser automation script.
- An operating system.
- A desktop environment.
- A framework for LLM wrappers.
- A collection of AI prompts.

These may become components or capabilities, but they do not define the project.

---

# The Problem

Today's AI systems generally work like this:

User → Prompt → AI → Response

They have little or no understanding of:

- the current desktop
- running applications
- user goals
- ongoing workflows
- previous actions
- verification of results
- long-term context

Most assistants disappear after answering a prompt.

Most automation tools execute instructions without understanding why.

Most desktop agents operate only within predefined workflows.

This creates systems that are reactive instead of intelligent.

---

# Why Override Exists

Override exists to bridge the gap between human intention and computer execution.

Instead of requiring users to constantly translate intentions into precise commands, Override should gradually understand:

- what the user is trying to accomplish
- what currently exists on the screen
- what applications are active
- what has already been completed
- what still remains
- whether an action succeeded or failed

Its goal is to reduce friction between thinking and doing while keeping the human in complete control.

---

# Core Idea

Override continuously maintains an internal understanding of the user's digital environment.

Rather than processing isolated prompts, it reasons over an evolving context.

That context includes:

- the current desktop
- open applications
- active tasks
- user goals
- previous interactions
- available tools
- execution history

Every decision should be made using this context instead of a single prompt.

---

# Fundamental Principles

Override is built around the following principles:

1. Local-first whenever practical.
2. Human remains in control.
3. Understand before acting.
4. Plan before executing.
5. Verify every important action.
6. Learn from previous interactions.
7. Build reusable knowledge.
8. Prefer deterministic execution over guessing.
9. Separate cognition from execution.
10. Architecture before implementation.

---

# Scope

Override is responsible for:

- understanding digital environments
- reasoning about goals
- planning actions
- coordinating tools
- executing approved actions
- verifying outcomes
- maintaining long-term context
- learning user workflows

Override is **not** responsible for:

- replacing Windows, Linux, or macOS
- managing hardware
- replacing device drivers
- replacing the kernel
- implementing filesystems
- implementing networking stacks

Those responsibilities remain with the host operating system.

---

# Relationship with the Operating System

The operating system manages the computer.

Override manages cognition.

```
User
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━
      Override
━━━━━━━━━━━━━━━━━━━━━━
        │
        ▼
Windows / Linux / macOS
        │
        ▼
Hardware
```

Override consumes operating system capabilities through stable APIs.

It does not own them.

---

# Long-Term Goal

The long-term goal of Override is to become a continuously running cognitive runtime capable of:

- observing
- understanding
- reasoning
- planning
- executing
- verifying
- remembering
- improving

across arbitrary software and workflows.

Its architecture should remain independent of any specific AI model, operating system, or user interface technology.

Models, frameworks, and implementation details may change.

The architectural philosophy should remain stable.

---

# Success Definition

Override succeeds when users no longer think about controlling software.

Instead, they describe outcomes, and Override safely coordinates the necessary actions while keeping the user informed and in control.

Success is measured not by the number of supported commands, but by the quality of understanding, planning, execution, and verification.

---

# Non-Goals

Override will not:

- silently perform irreversible actions
- replace human judgement
- require cloud connectivity for core functionality
- lock users into a single AI provider
- tightly couple itself to one framework or language
- prioritize convenience over transparency

---

# Guiding Statement

**Override is a local-first cognitive runtime that understands digital environments, reasons about user goals, safely executes actions, verifies outcomes, and continuously builds context while running on top of existing operating systems.**