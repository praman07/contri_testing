# Provider System

Providers are controlled bridges from cognition to external capability. They execute; they do not decide goals.

## Provider abstraction

Every provider declares capabilities, permissions, risk levels, input schema, output schema, side effects, verification hooks, and rollback support.

## Core providers

Browser provider controls pages, tabs, forms, downloads, and web evidence.

Desktop provider controls windows, keyboard, mouse, accessibility, notifications, and screen interactions.

Vision provider interprets screen, images, diagrams, and visual state.

File provider reads, writes, moves, deletes, indexes, and transforms files with approval rules.

Shell provider executes commands with sandboxing, working-directory constraints, and output capture.

Git provider inspects status, diffs, branches, commits, remotes, and history.

Docker provider inspects containers, images, compose stacks, logs, ports, and health.

Communication providers handle email, calendar, messaging, and meetings with strict approval.

## Safety and permissions

Providers are least-privilege by default. Risk determines required approval. Credentials and account sessions are never used silently. External submissions always require explicit approval.
