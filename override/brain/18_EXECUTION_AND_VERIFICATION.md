# Execution and Verification

Execution turns approved plans into provider actions. Verification determines whether outcomes actually happened.

## Execution lifecycle

Plan approved, permissions checked, provider selected, preflight run, action executed, output captured, verification run, memory updated, user informed.

## Human approval

Approval is part of execution, not a UI afterthought. Sensitive steps must pause until the user approves.

## Verification

Verification uses provider outputs, filesystem state, process state, UI state, tests, screenshots, logs, and user confirmation when necessary.

## Retry and rollback

Retries are allowed only when safe and bounded. Rollback is required when a provider can reverse changes. If rollback is impossible, the plan must say so before execution.

## Failure handling

Failures produce a diagnosis, evidence, impact, safe next options, and whether user input is required.

## Safety checks

Execution must check risk, permissions, active context, credentials, irreversible side effects, and external impact before acting.
