# Override Product Bible

Override is a local-first Agentic Operating Layer: a cognitive layer that runs above the host operating system and helps the user understand, plan, execute, verify, remember, and improve work across the entire digital workspace.

This document describes the finished product as users should experience it. It is not architecture and not implementation.

## What Override is

Override is a persistent digital work partner. It observes the current workspace, understands active work, remembers previous sessions, reasons over goals, coordinates tools, asks permission before meaningful actions, executes through controlled providers, verifies results, and learns from outcomes.

Override turns a computer from a command-driven tool into a context-aware collaborator while preserving human control.

## What Override is not

Override is not a chatbot, not a voice assistant, not a Jarvis clone, not a Cursor clone, not a Copilot clone, not a browser automation script, not a desktop environment, not an operating system, not a prompt wrapper, and not a decorative AI HUD.

## Complete user journey

The user installs Override locally. On first boot, Override asks what it may observe, what it may remember, which providers are allowed, and which actions require confirmation. It creates a private local profile and begins building a workspace model.

During daily work, Override stays mostly silent. It watches active windows, projects, browser tabs, documents, terminal output, meetings, goals, and recent history. It speaks only when it can add value: to prevent mistakes, propose a next step, recall useful context, request approval, or summarize progress.

When the user gives a goal, Override turns the goal into a plan, chooses providers, asks for missing inputs, requests permission for sensitive steps, executes approved actions, verifies outcomes, and records what happened.

When the user returns after time away, Override reconstructs the work state: what was open, what was being attempted, what changed, what remains, and what it recommends next.

## Daily usage

A user can say or type:

- “Be my assistant.” Override watches the focused workspace and suggests only useful next actions.
- “Continue yesterday's backend task.” Override restores the project context, last commits, open issues, failing checks, and next likely step.
- “Apply to FDE roles in Germany.” Override asks for a resume if it does not have one, finds appropriate roles, tailors application materials per role, asks before submitting anything, and logs outcomes.
- “Research this topic.” Override builds a research workspace with sources, claims, contradictions, notes, and next questions.
- “Generate a diagram of this architecture.” Override creates a diagram from the current workspace model and lets the user revise it.

## Workspace understanding

Override understands more than prompts. It understands the active window, running apps, browser tabs, open documents, git repositories, services, Docker containers, terminals, meetings, files, goals, plans, and relationships between them.

## Long-term memory

Override remembers user preferences, recurring workflows, successful strategies, recurring mistakes, goals, projects, and past decisions. Memory is local-first, transparent, searchable, editable, and forgettable.

## Session recall

A session is not just a chat log. It is the state of work: active goal, project, files touched, commands run, browser research, meetings, decisions, unfinished plans, and verification results. Override can summarize and resume sessions.

## Dynamic workspaces

The UI reshapes around the task. Coding shows files, tests, diffs, logs, dependencies, and next steps. Research shows sources, claims, notes, and open questions. Career work shows roles, requirements, resume versions, applications, and approvals. Meetings show agenda, participants, notes, decisions, and follow-ups.

## Coding workflow

Override acts like a Chief Engineer: understands the repository, reads relevant files, proposes a plan, asks before risky changes, edits through providers, runs checks, explains trade-offs, and verifies results.

## Research workflow

Override gathers sources, separates facts from claims, highlights uncertainty, cites evidence, remembers conclusions, and produces summaries or diagrams when useful.

## Learning workflow

Override tracks goals, weak areas, study materials, practice sessions, and progress. It suggests study actions when context indicates drift, but never shames or nags.

## Job application workflow

Override can find roles, compare fit, tailor resumes and cover letters, fill applications, handle logins with explicit user approval, track submissions, and prepare follow-ups. It never fabricates credentials, lies on applications, or submits without approval.

## Meeting workflow

Override can prepare agendas, summarize previous context, capture notes with permission, identify decisions, assign follow-ups, and connect meeting outcomes to goals and projects.

## Diagram generation

Override can generate architecture diagrams, process maps, timelines, entity graphs, and decision diagrams from workspace context. Diagrams must explain real relationships, not decorate the UI.

## Browser and desktop automation

Override uses browser and desktop automation when native APIs are unavailable or insufficient. It chooses the safest reliable method: API, accessibility, browser automation, desktop automation, vision, keyboard, or mouse.

## Safety, trust, and human control

The user remains the final authority. Override asks before irreversible, external, financial, identity, account, security, destructive, or reputation-impacting actions. It explains what it intends to do, what it did, what failed, and what evidence supports success.

## Product principles

- Understand before acting.
- Speak only when useful.
- Every pixel earns its place.
- Prefer local-first and private-by-default behavior.
- Separate cognition from execution.
- Verify important outcomes.
- Learn without trapping the user.
- Make uncertainty visible.
- Never optimize for fake intelligence aesthetics.

## Example interactions

Good: “Sir, you are editing the auth service. The failing test is still `test_token_refresh`. I can inspect the refresh path and propose a patch.”

Good: “I found 14 FDE roles in Germany. Three match your resume strongly. I need your approval before tailoring and submitting applications.”

Bad: “I opened ten dashboards to show system intelligence.”

Bad: “I submitted the application for you without asking.”
