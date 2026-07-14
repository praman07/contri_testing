# Reasoning Engine

The Reasoning Engine turns context, goals, memory, and constraints into decisions and explanations.

## Inputs

Relevant world model slice, active goal, user instruction, memory, provider capabilities, permissions, current risks, verification history, and UI context.

## Outputs

Reasoning result, confidence, assumptions, uncertainty, recommended plan intent, required information, required approvals, risk assessment, and explanation.

## Decision making

Reasoning evaluates what the user is trying to accomplish, what context matters, what actions are possible, what is risky, what should be asked, and what should be done next.

## Planning interface

Reasoning does not execute. It produces structured facts and recommendations for the Planner.

## Confidence and explainability

Confidence must be grounded in evidence. Low confidence leads to questions or observation, not blind action. Explanations should be concise and linked to observed facts.
