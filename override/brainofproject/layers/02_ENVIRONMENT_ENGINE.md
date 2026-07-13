# Layer 02 — Environment Engine

## Purpose
Maintain the current live state of the host environment.

## Owns
- Running applications
- Window hierarchy
- Active window
- Monitor layout
- Clipboard state
- Connected devices
- Network status
- Battery status

## Never Owns
- OCR
- Planning
- Memory
- AI inference

## Inputs
ObservationFrame

## Outputs
EnvironmentSnapshot

## Called By
Context Engine

## Calls
Platform Abstraction Layer

## Publishes
- EnvironmentUpdated
- WindowFocused
- ApplicationStarted
- ApplicationClosed

## Subscribes
- Observation events

## Performance Requirements
Real-time state updates with minimal polling.

## Success Criteria
Maintains an accurate representation of the host environment.