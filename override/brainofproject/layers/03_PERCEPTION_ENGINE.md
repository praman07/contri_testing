# Layer 03 — Perception Engine

## Purpose
Transform raw observation signals into structured, named facts about the host environment.

The Perception Engine bridges the gap between low-level sensor data (raw screenshots, audio bytes, window events) and the structured knowledge that higher-level engines (Context, Reasoning) can act upon.

---

## Owns

- Screen region text extraction (OCR) via lightweight provider
- Active window title and class interpretation
- Clipboard content classification (text type, language, format)
- Speech transcript normalization
- Application context classification (app name → known category: browser, IDE, terminal, media, etc.)
- Structured `PerceptionFrame` assembly and publication

---

## Never Owns

- Planning
- Reasoning or decision-making
- Goal tracking
- Memory writes
- AI inference beyond lightweight classification
- Direct OS API calls (all OS access delegated to PAL via Environment Engine)

---

## Inputs

- `observation.screen_captured` events → trigger OCR pipeline
- `observation.audio_captured` events → trigger transcript normalization
- `observation.window_changed` events → trigger window context classification
- `environment.updated` events → refresh application context classification
- `environment.window_focused` events → reclassify active window context

---

## Outputs

`PerceptionFrame` — an immutable structured knowledge record:

```
PerceptionFrame
  timestamp            : str (ISO 8601)
  source_event_id      : str
  active_window_title  : str
  active_window_class  : str
  active_app_category  : str   # e.g. "browser", "ide", "terminal", "media", "unknown"
  ocr_text             : str   # extracted text from screen, empty if not available
  speech_transcript    : str   # normalized speech text, empty if none
  clipboard_text_type  : str   # "code", "url", "plain_text", "empty"
  detected_entities    : List[Dict]  # structured named entities extracted
```

---

## Called By

Context Engine (Layer 04)

---

## Calls

- Event Bus (subscribe/publish only — no direct subsystem references)

---

## Publishes

- `perception.frame_ready` — carries serialized `PerceptionFrame` payload
- `perception.screen_text_extracted` — carries OCR result for a given screen region
- `perception.window_context_classified` — carries active window category and metadata
- `perception.speech_recognized` — carries normalized speech transcript
- `perception.clipboard_classified` — carries clipboard content type
- `perception.engine.started` — lifecycle fact
- `perception.engine.stopped` — lifecycle fact

---

## Subscribes

- `observation.screen_captured`
- `observation.audio_captured`
- `observation.window_changed`
- `environment.updated`
- `environment.window_focused`

---

## Performance Requirements

- Perception operations must not block the Event Bus dispatch loop.
- All classification and extraction runs in a dedicated background thread pool.
- OCR is optional and disabled by default; enabled only when a screen capture event is received and OCR capability is confirmed.
- Idle CPU: < 1% (no polling; purely event-driven).
- PerceptionFrame assembly latency: < 50 ms from event receipt to publication.

---

## Architectural Constraints

- The Perception Engine must **not** call the PAL directly.
- All environmental facts (active window, running apps) are consumed from **Event Bus events** published by the Environment Engine.
- Speech recognition is performed on normalized audio transcript payloads — the Perception Engine does **not** open audio devices.
- OCR is performed using a lightweight, local, CPU-safe library only (e.g., `pytesseract` or stub fallback). No cloud APIs.

---

## Success Criteria

Produces reliable, structured `PerceptionFrame` objects from raw observation events.
Higher-layer engines (Context Engine) receive clean, typed facts rather than raw binary signals.
