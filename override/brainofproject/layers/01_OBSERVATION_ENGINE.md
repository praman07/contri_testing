# Layer 01 — Observation Engine

## Purpose

Collect raw signals from the environment.

---

## Owns

- Screen capture
- Audio capture
- Camera capture
- Input events
- Window events
- Filesystem events
- Device events

---

## Never Owns

- OCR
- Object detection
- Speech recognition
- Planning
- Memory
- AI inference

---

## Inputs

Platform Abstraction Layer

---

## Outputs

ObservationFrame

---

## Called By

Runtime Foundation

---

## Calls

Platform Abstraction Layer

---

## Publishes

- ScreenCaptured
- AudioCaptured
- MouseMoved
- KeyboardInput
- WindowChanged

---

## Subscribes

- RuntimeStarted
- RuntimeStopped
- ConfigurationChanged

---

## Performance Requirements

- Event-driven where possible
- Adaptive capture
- Low idle CPU
- Independent providers

---

## Success Criteria

Produces reliable ObservationFrames for higher layers.