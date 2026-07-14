# Agent Orchestration

Agent Orchestration coordinates planning, specialized workers, verification, human approval, and recovery.

## Planner

The Planner converts goals and reasoning outputs into structured plans with steps, dependencies, providers, required approvals, expected outcomes, and verification requirements.

## Specialized agents

Specialized agents may handle research, coding, browser work, file work, testing, diagramming, career workflows, or meeting workflows. They operate inside permissions and report evidence.

## Delegation

Delegation happens only when a subtask has clear scope, inputs, outputs, risk level, and verification criteria.

## Coordination

The orchestrator maintains plan state, avoids duplicate work, resolves conflicts, and links all work to the active goal and world model.

## Human approval

Approval is required before sensitive actions and before any provider performs irreversible or external actions.

## Verification and recovery

Every important step has an expected outcome. Failures trigger diagnosis, retry if safe, alternate plans, or user escalation.
