# Override — Project Rules

**Document ID:** RULE-0001  
**Status:** Approved  
**Authority:** Level 1  
**Owner:** Founding Architect

---

# Purpose

This document defines the permanent rules that govern every contribution to Override.

Every human and every AI working on Override must follow these rules.

If another document conflicts with these rules, this document takes precedence unless explicitly replaced by an approved architectural decision.

---

# Core Philosophy

Always optimize for:

- Simplicity
- Correctness
- Maintainability
- Performance
- Security
- Extensibility
- Understandability

Never optimize for writing more code.

---

# Architecture Rules

## DO

- Understand before changing.
- Design before implementing.
- Keep modules independent.
- Give every module one clear responsibility.
- Prefer composition over unnecessary inheritance.
- Prefer deterministic behavior over guessing.
- Prefer reusable abstractions over duplicated logic.
- Keep dependencies minimal.
- Challenge existing assumptions before extending architecture.
- Build systems that can survive technology changes.

## DON'T

- Do not tightly couple modules.
- Do not let implementation dictate architecture.
- Do not build features without understanding the surrounding system.
- Do not create unnecessary abstractions.
- Do not solve problems that do not yet exist.
- Do not add complexity without measurable value.

---

# Development Rules

## DO

- Read relevant context before starting work.
- Explain important design decisions.
- Keep changes focused.
- Update documentation when architecture changes.
- Keep commits logically grouped.
- Remove dead code instead of hiding it.
- Review your own work before finishing.

## DON'T

- Do not generate placeholder code.
- Do not leave TODOs without justification.
- Do not duplicate existing functionality.
- Do not silently change behavior.
- Do not ignore architectural inconsistencies.

---

# AI Rules

Every AI session must:

1. Understand the task.
2. Load only the necessary project context.
3. Analyze dependencies.
4. Consider trade-offs.
5. Explain major decisions.
6. Implement only after the design is clear.
7. Perform a self-review.
8. Stop if architectural conflicts are discovered.

An AI should admit uncertainty rather than invent answers.

---

# Documentation Rules

Documentation exists to reduce confusion.

Every document must answer one primary question.

Avoid duplicated information.

If information already exists elsewhere, reference it instead of copying it.

Documentation should evolve with the architecture.

It should never become the architecture.

---

# Coding Rules

Write code that another engineer can understand six months later.

Prefer readability over cleverness.

Every file should have a clear purpose.

Every function should have a single responsibility.

Every public interface should be documented.

Delete unnecessary code.

Avoid premature optimization.

---

# Security Rules

Assume all external input is untrusted.

Validate everything.

Never expose secrets.

Prefer local-first execution.

Request user confirmation before destructive actions.

Keep permissions explicit.

Never collect data that is not required.

---

# Performance Rules

Measure before optimizing.

Avoid unnecessary background work.

Minimize memory usage.

Prefer event-driven systems over polling where appropriate.

Keep startup fast.

Keep idle resource usage low.

---

# Override-Specific Rules

Override is a Cognitive Runtime.

It is NOT:

- an operating system
- a kernel
- a device driver framework
- a chatbot
- a browser automation script

Override exists to:

- observe
- understand
- reason
- plan
- execute
- verify
- learn

Every new feature should support one or more of these responsibilities.

If it does not, question whether it belongs in Override.

---

# Decision Rule

When two possible solutions exist:

Choose the one that is:

- simpler
- easier to maintain
- easier to understand
- easier to test
- more modular
- more future-proof

Even if it requires writing less code.

---

# Final Principle

Every change should make Override easier to understand, easier to extend, and more reliable than it was before.