# Repository Map

## 1. Purpose
- **Why this document exists**: This document serves as the structural and dependency baseline for migrating the reference implementation of **J.A.R.V.I.S. (Mark-XLVII)** into the **Override Cognitive Runtime**. It acts as a guide to identify architectural components, map their functional logic, and trace dependency vectors.
- **Scope**: Covers the entire current codebase including core files (`main.py`, `ui.py`), secondary packages (`actions/`, `core/`, `memory/`, `dashboard/`), configurations, assets, and third-party dependencies.
- **Rules**:
  1. **Never Invent**: Every file, dependency, execution flow, or capability mapped must exist in the current source code.
  2. **Map Reality Only**: Do not document hypothetical features or planned elements unless marked as part of the future target architecture.
  3. **Provide Path Verifiability**: All file references must point to active file paths using verified workspace paths.

---

## 2. Repository Overview
- **Current Repository**: J.A.R.V.I.S. (Mark-XLVII) reference codebase. A voice-first desktop agent operating via Gemini Live WebSocket API, PyQt6 UI, local system tools, and a local LAN control dashboard.
- **Entry Point**: [main.py](file:///C:/Users/HomePC/jaaara/main.py)
- **Overall Architecture**:
  - **Front End Layer**: PyQt6-based HUD overlay canvas [ui.py](file:///C:/Users/HomePC/jaaara/ui.py). Communicates with backend threads via thread-safe Qt signals and callbacks.
  - **Orchestration Layer**: Multithreaded daemon engine in [main.py](file:///C:/Users/HomePC/jaaara/main.py) managing asynchronous input/output pipelines, WebSocket connections, audio callbacks (`sounddevice`), and system monitoring.
  - **Cognitive Layer**: Remote Gemini 2.5 Flash Native Audio WebSocket API. Direct low-latency speech-to-speech and visual perception processing.
  - **Execution Layer**: Local Python modules under `actions/` executing desktop controls, browser controls, file manipulations, and program launching.
  - **Remote Control Layer**: Local FastAPI HTTP/WS server under `dashboard/` enabling secondary phone mic streaming, UI controls, and encrypted key authentications.
- **High-Level Folder Tree**:
```
jaaara/
├── main.py
├── ui.py
├── requirements.txt
├── actions/
│   ├── browser_control.py
│   ├── code_helper.py
│   ├── computer_control.py
│   ├── computer_settings.py
│   ├── desktop.py
│   ├── dev_agent.py
│   ├── file_controller.py
│   ├── file_processor.py
│   ├── flight_finder.py
│   ├── game_updater.py
│   ├── open_app.py
│   ├── reminder.py
│   ├── screen_processor.py
│   ├── send_message.py
│   ├── system_monitor.py
│   ├── weather_report.py
│   ├── web_search.py
│   └── youtube_video.py
├── config/
│   ├── api_keys.json
│   └── certs/
├── core/
│   ├── llm_client.py
│   ├── prompt.txt
│   ├── installer.py
│   ├── stt.py
│   └── tts.py
├── dashboard/
│   ├── server.py
│   └── static/
├── memory/
│   ├── memory_manager.py
│   └── long_term.json
└── override/
    └── brainofproject/
```

---

## 3. Startup Flow
- **Application Startup Sequence**:
  1. Entry point execution starts in [main.py](file:///C:/Users/HomePC/jaaara/main.py#L1152) within the `main()` function.
  2. Stdout/Stderr streams are reconfigured to UTF-8 to prevent encoding crashes on Windows console environments.
  3. PyQt6 application runtime environment starts, initializing the `JarvisUI` frame with [ui.py](file:///C:/Users/HomePC/jaaara/ui.py).
  4. A background daemon thread named `runner` is spawned via `threading.Thread` targeting the `runner` function.
  5. The `runner` function calls `ui.wait_for_api_key()` to block until a valid Gemini API key is supplied in the config file.
  6. The `JarvisLive` manager instance is instantiated, configuring UI events (like `on_text_command` and `on_remote_clicked`).
  7. Async main loop is started with `asyncio.run(jarvis.run())` inside the background thread.
  8. The Qt event loop is executed via `sys.exit(ui.app.exec())` on the primary thread.
- **Initialization Order**:
  1. Operating System stream config & resource path binding (`get_base_dir()` / `get_assets_dir()`).
  2. UI canvas construction & rendering thread.
  3. JSON configuration parser loading API keys and LLM settings.
  4. Local Dashboard server instanced via FastAPI thread (if uvicorn dependencies exist).
  5. Audio stream queues (`audio_in_queue`, `out_queue`) setup.
  6. Persistent Gemini Live WebSocket Connection established.
  7. Mic Input (`sounddevice` input) and Speaker Output (`sounddevice` output) streams opened.
  8. Periodic monitoring routines (SystemMonitor metric task) and Morning Briefing trigger scheduled.
- **Runtime Lifecycle**:
  - **Active State**: System continuously captures audio at 16kHz, sends chunks to Gemini Live WebSocket, receives 24kHz audio outputs, feeds the speaker queue, and executes functions returned via functional tool calls.
  - **Tool Execution State**: The async loop yields execution to blocking system handlers in `loop.run_in_executor` threads, then returns outcomes back through the WebSocket.
  - **Error/Recovery State**: In case of network loss, WebSocket handler triggers a 3-second exponential backoff loop while updating the UI indicator to 'CONNECTING'.
  - **Shutdown State**: On `shutdown_jarvis` trigger, system plays goodbye message, initiates a 1-second daemon timer thread, and executes a hard `os._exit(0)` signal.

---

## 4. Folder Map

### actions/
- **Purpose**: Folder storing discrete local agent automation modules (tools).
- **Responsibilities**: Executing deterministic keyboard/mouse inputs, controlling OS parameters, processing local files, orchestrating browser instances, querying external flight/weather data, and updating system software platforms.
- **Important Files**:
  - [browser_control.py](file:///C:/Users/HomePC/jaaara/actions/browser_control.py)
  - [dev_agent.py](file:///C:/Users/HomePC/jaaara/actions/dev_agent.py)
  - [screen_processor.py](file:///C:/Users/HomePC/jaaara/actions/screen_processor.py)
  - [system_monitor.py](file:///C:/Users/HomePC/jaaara/actions/system_monitor.py)
- **Dependencies**: `pyautogui`, `playwright`, `sounddevice`, `psutil`, `opencv-python`, `mss`, `comtypes`, `pywinauto`.
- **Current Quality**: **Medium-Low**. Individual actions contain rich utility logic, but lack sandboxing, structured exception logging, unified interfaces, or async compatibility (relying heavily on sync blocking calls inside generic thread executors).
- **Recommendation**: **REFACTOR** (Preserve tool automation logic but wrap them within a typed, sandboxed execution framework).

### config/
- **Purpose**: Configuration files and keys storage.
- **Responsibilities**: Reading credentials for API access, resolving TLS certificate files for the dashboard server.
- **Important Files**:
  - `api_keys.json`
- **Dependencies**: Native Python json module.
- **Current Quality**: **Medium**. Simple JSON storage. Lacks encryption or secure vault integration.
- **Recommendation**: **REPLACE** (Implement a secure config vault system with key derivation/env override mechanisms).

### core/
- **Purpose**: Internal helper models, prompts, and utilities.
- **Responsibilities**: Local LLM interactions (Ollama/OpenAI compat interfaces), prompt construction, and package checks.
- **Important Files**:
  - [llm_client.py](file:///C:/Users/HomePC/jaaara/core/llm_client.py)
  - [prompt.txt](file:///C:/Users/HomePC/jaaara/core/prompt.txt)
- **Dependencies**: `google-genai`, `requests`.
- **Current Quality**: **Medium-High**. The local LLM client is well-architected (includes prompt warmups and stream splitting). The directory contains obsolete scripts (`stt.py`, `tts.py`) that are not used by the main voice runtime.
- **Recommendation**: **REFACTOR** (Keep `llm_client.py` and modularize `prompt.txt`. Delete dead `stt.py`/`tts.py` modules).

### dashboard/
- **Purpose**: Remote interface dashboard server.
- **Responsibilities**: Serving LAN administrative control interface, managing session auth keys, streaming remote log data over WebSockets, receiving mobile audio capture inputs.
- **Important Files**:
  - [server.py](file:///C:/Users/HomePC/jaaara/dashboard/server.py)
- **Dependencies**: `fastapi`, `uvicorn`, `cryptography`, `python-multipart`.
- **Current Quality**: **Low**. Strong functional relay tool but exposes serious local LAN security flaws (single-pass key derivation, lack of HTTPS enforceability out-of-the-box, direct command execute endpoint permissions).
- **Recommendation**: **REPLACE** (Rebuild within a secure service architecture using standard JWT/OAuth scopes, strict CORS, and hardened WebSocket frame handling).

### memory/
- **Purpose**: Persistent context memory system.
- **Responsibilities**: Reading and writing personal user facts, optimizing file storage size limits.
- **Important Files**:
  - [memory_manager.py](file:///C:/Users/HomePC/jaaara/memory/memory_manager.py)
  - `long_term.json`
- **Dependencies**: Native Python thread locks.
- **Current Quality**: **Medium-Low**. Functional for a prototype, but limited to a static size ceiling (2,200 character JSON file) and prone to silent data deletion.
- **Recommendation**: **REFACTOR** (Transition from flat-file JSON truncation to a SQLite/relational local schema with priority indexes).

### override/
- **Purpose**: Override runtime configuration, plans, and blueprints.
- **Responsibilities**: Storing project specifications, interface contracts, progress states, and blueprints.
- **Important Files**:
  - [00_PROJECT.md](file:///C:/Users/HomePC/jaaara/override/brainofproject/00_PROJECT.md)
  - [CURRENT_STATE.md](file:///C:/Users/HomePC/jaaara/override/brainofproject/CURRENT_STATE.md)
  - [ENGINEERING_BLUEPRINT.md](file:///C:/Users/HomePC/jaaara/override/brainofproject/ENGINEERING_BLUEPRINT.md)
- **Dependencies**: None.
- **Current Quality**: **High**. Structured specification system.
- **Recommendation**: **KEEP** (Continue adding specifications).

---

## 5. File Map

### main.py
- **Current Path**: [main.py](file:///C:/Users/HomePC/jaaara/main.py)
- **Purpose**: Core application manager, startup hub, and Gemini Live WebSocket orchestrator.
- **Responsibilities**: Creating queues, managing WebSocket tasks, handling audio loops, scheduling system checks, and routing tool calls.
- **Used By**: Executable entry point.
- **Dependencies**: `google-genai`, `sounddevice`, `ui.py`, `memory_manager.py`, and all modules in `actions/`.
- **Recommendation**: **REPLACE** (Deconstruct into separate modular packages: event loop, connection manager, voice engine, and tool registry).
- **Future Override Location**: `override/runtime/core/`

### ui.py
- **Current Path**: [ui.py](file:///C:/Users/HomePC/jaaara/ui.py)
- **Purpose**: Graphical HUD display interface.
- **Responsibilities**: Providing canvas rendering overlays, showing CPU/RAM graphs, printing live log diagnostics, capturing keybind shortcuts, and playing visual state animations (listening, speaking, thinking).
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (via tool dispatch)
- **Dependencies**: `PyQt6`.
- **Recommendation**: **REPLACE** (Rebuild as an Electron + React application as mandated by Override tech strategy).
- **Future Override Location**: `override/ui/`

### actions/browser_control.py
- **Current Path**: [actions/browser_control.py](file:///C:/Users/HomePC/jaaara/actions/browser_control.py)
- **Purpose**: Browser automation client.
- **Responsibilities**: Instantiating persistent profiles, navigating tabs, clicking page targets, filling inputs, returning text/URLs, and snapping browser frames.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (via tool dispatch)
- **Dependencies**: `playwright`.
- **Recommendation**: **REFACTOR** (Decouple automation functions from blocking synchronous logic and package as an execution provider).
- **Future Override Location**: `override/execution/providers/browser/`

### actions/dev_agent.py
- **Current Path**: [actions/dev_agent.py](file:///C:/Users/HomePC/jaaara/actions/dev_agent.py)
- **Purpose**: Autonomous workspace project creator and debugger.
- **Responsibilities**: Generating multi-file project specifications, writing local files, invoking dependency installs, running project code, parsing tracebacks, and applying code fixes iteratively.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (via tool dispatch)
- **Dependencies**: `google-genai` (standard clients), `subprocess`.
- **Recommendation**: **REFACTOR** (Sandbox code execution using Docker or containerized runners to prevent direct host commands).
- **Future Override Location**: `override/execution/providers/sandbox/`

### dashboard/server.py
- **Current Path**: [dashboard/server.py](file:///C:/Users/HomePC/jaaara/dashboard/server.py)
- **Purpose**: Administrative LAN connection API and websocket server.
- **Responsibilities**: Relaying audio stream packages from mobile connections, handling file uploads, verifying PIN credentials, and serving web assets.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (as a concurrent task)
- **Dependencies**: `fastapi`, `uvicorn`, `cryptography`.
- **Recommendation**: **REPLACE** (Expose dashboard functions via a secure microservice layer utilizing strict token auth).
- **Future Override Location**: `override/runtime/services/dashboard/`

### memory/memory_manager.py
- **Current Path**: [memory/memory_manager.py](file:///C:/Users/HomePC/jaaara/memory/memory_manager.py)
- **Purpose**: Long term cognitive memory manager.
- **Responsibilities**: Updating memory structures, writing changes, formatting text segments for model system prompt context.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py)
- **Dependencies**: Native Python modules.
- **Recommendation**: **REFACTOR** (Migrate from JSON file to SQLite database file with category tables and transaction isolation).
- **Future Override Location**: `override/cognition/memory/`

### core/llm_client.py
- **Current Path**: [core/llm_client.py](file:///C:/Users/HomePC/jaaara/core/llm_client.py)
- **Purpose**: Local and standard OpenAI/Ollama client interface.
- **Responsibilities**: Calling text generators, warming up model context keys, formatting prompt messages, and parsing stream boundaries.
- **Used By**: [actions/code_helper.py](file:///C:/Users/HomePC/jaaara/actions/code_helper.py), [actions/dev_agent.py](file:///C:/Users/HomePC/jaaara/actions/dev_agent.py)
- **Dependencies**: `requests`.
- **Recommendation**: **KEEP** (Move to LLM client wrappers within the Override planner module).
- **Future Override Location**: `override/cognition/models/`

### core/prompt.txt
- **Current Path**: [core/prompt.txt](file:///C:/Users/HomePC/jaaara/core/prompt.txt)
- **Purpose**: Primary system instruction text.
- **Responsibilities**: Informing the agent persona, tool priorities, and language constraints.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (via `_load_system_prompt()`)
- **Dependencies**: None.
- **Recommendation**: **REFACTOR** (Convert system instructions into structured, composable configuration segments).
- **Future Override Location**: `override/cognition/prompts/`

### actions/screen_processor.py
- **Current Path**: [actions/screen_processor.py](file:///C:/Users/HomePC/jaaara/actions/screen_processor.py)
- **Purpose**: Real-time visual observer thread.
- **Responsibilities**: Executing screen captures, resizing image buffers, transmitting chunks, and running secondary vision API connections.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (as tool run/independent thread)
- **Dependencies**: `mss`, `opencv-python`, `pillow`, `google-genai`.
- **Recommendation**: **REFACTOR** (Integrate into the new Observation System and fix the connection setup sync bug).
- **Future Override Location**: `override/cognition/perception/`

### actions/system_monitor.py
- **Current Path**: [actions/system_monitor.py](file:///C:/Users/HomePC/jaaara/actions/system_monitor.py)
- **Purpose**: Background hardware stats monitor.
- **Responsibilities**: Tracking CPU load, memory space, heat sensors, and triggering alert events on crossing critical lines.
- **Used By**: [main.py](file:///C:/Users/HomePC/jaaara/main.py) (async monitor loop)
- **Dependencies**: `psutil`.
- **Recommendation**: **KEEP** (Migrate verbatim into system monitoring daemon).
- **Future Override Location**: `override/runtime/services/monitor/`

---

## 6. Capability Map

| Capability | Current Module | Future Override Module | Decision | Priority |
|---|---|---|---|---|
| **Voice** | [main.py](file:///C:/Users/HomePC/jaaara/main.py#L750-L860) | `override/runtime/services/audio/` | **REFACTOR** (Port PCM loops to new async loop) | **HIGH** |
| **Browser Automation** | [actions/browser_control.py](file:///C:/Users/HomePC/jaaara/actions/browser_control.py) | `override/execution/providers/browser/` | **REFACTOR** (Make async and decouple config) | **HIGH** |
| **Desktop Automation** | [actions/computer_control.py](file:///C:/Users/HomePC/jaaara/actions/computer_control.py) | `override/execution/providers/desktop/` | **REFACTOR** (Wrap with execution limits) | **HIGH** |
| **Vision** | [actions/screen_processor.py](file:///C:/Users/HomePC/jaaara/actions/screen_processor.py) | `override/cognition/perception/` | **REFACTOR** (Fix races, sync visual streams) | **MEDIUM** |
| **Memory** | [memory/memory_manager.py](file:///C:/Users/HomePC/jaaara/memory/memory_manager.py) | `override/cognition/memory/` | **REFACTOR** (Migrate from JSON to SQLite database) | **MEDIUM** |
| **Tool Calling** | [main.py](file:///C:/Users/HomePC/jaaara/main.py#L607-L743) | `override/cognition/planner/` | **REPLACE** (Move to declarative plans) | **HIGH** |
| **Dashboard** | [dashboard/server.py](file:///C:/Users/HomePC/jaaara/dashboard/server.py) | `override/runtime/services/dashboard/` | **REPLACE** (Harden credentials and auth token) | **LOW** |
| **Settings** | [main.py](file:///C:/Users/HomePC/jaaara/main.py#L68) | `override/runtime/core/config/` | **REPLACE** (Integrate system configurations) | **MEDIUM** |
| **Logging** | [ui.py](file:///C:/Users/HomePC/jaaara/ui.py#L765) | `override/runtime/services/logger/` | **REPLACE** (Output to SQLite + log stdout) | **MEDIUM** |

---

## 7. Dependency Graph

### Folder Dependency Graph
```
        [ main.py ] 
       /     │     \
      ▼      ▼      ▼
 [ui.py] [core/] [memory/]
   │      │        │
   │      ▼        │
   └─► [actions/] ◄┘
         │
         ▼
     [dashboard/]
```

### Module Dependency Graph
```
[ main.py ] ───► [ ui.py ]
   │
   ├─► [ memory_manager.py ] ───► memory/long_term.json
   │
   ├─► [ llm_client.py ]
   │
   ├─► [ dashboard/server.py ] ───► dashboard/static/
   │
   └─► [ actions/ ]
         ├─► browser_control.py ───► playwright
         ├─► screen_processor.py ───► mss, cv2, google-genai
         ├─► dev_agent.py ───► subprocess, llm_client.py
         └─► system_monitor.py ───► psutil
```

### Startup Dependency Graph
```
1. main.py (Entry) ──► Reconfigure Encoding (stdout/stderr)
                          │
                          ▼
2. JarvisUI (ui.py) ──► PyQt6 QApplication Init
                          │
                          ▼
3. runner Thread ─────► wait_for_api_key() (api_keys.json check)
                          │
                          ▼
4. JarvisLive Init ───► Load memory/long_term.json & config
                          │
                          ▼
5. asyncio.run() ─────► client.aio.live.connect() (Gemini Socket)
                          │
                          ├─► _send_realtime() (PCM Input)
                          ├─► _listen_audio() (Mic hardware)
                          ├─► _receive_audio() (Gemini read)
                          ├─► _play_audio() (Speaker queue)
                          └─► server.py (FastAPI background start)
```

---

## 8. Current Architecture Problems
- **Tight Coupling**: `main.py` is tightly coupled to `ui.py` (passing ui callbacks directly) and all action scripts, making it impossible to run the agent in a headless console configuration.
- **God Files**: `main.py` (1,167 lines) and `ui.py` (1,916 lines) are monoliths that mix configuration management, network sockets, thread executors, file reading, UI animation loops, and raw tool logic.
- **Duplicate Logic**: Two distinct Gemini API clients are imported and instantiated (the primary Live WebSocket client uses the newer `google-genai` SDK in `main.py`, while `dev_agent.py` and `screen_processor.py` instantiate separate legacy client configs).
- **Blocking Operations**: Multiple action modules execute synchronous file writing or OS calls that block the main executor pools.
- **Security Risks**: No protection wrapper or shell validation around terminal runs inside `code_helper.py` or `dev_agent.py`. The admin web server exposes direct execution capabilities with minimal local auth.
- **Performance Risks**: Dual WebSocket connection streams (Main Voice Session + Screen Processor Session) running concurrently compete for network buffers, causing audio packet loss and transcription stutters.
- **Maintainability Issues**: Adding or altering a single tool function signature requires modifying declarations in three places in `main.py` and updating arguments in target files.

---

## 9. Migration Map

| Current Module | Future Override Module | Decision | Priority |
|---|---|---|---|
| **main.py** | `override/runtime/core/` | **SPLIT** (Distribute into Event Loop, Connection, Config, and Tool Routing packages) | **HIGH** |
| **ui.py** | `override/ui/` | **REBUILD** (Migrate from PyQt6 to React/Electron frontend client) | **HIGH** |
| **memory_manager.py** | `override/cognition/memory/` | **REFACTOR** (Convert static JSON parser to SQLite data tables) | **MEDIUM** |
| **dashboard/server.py** | `override/runtime/services/dashboard/` | **REBUILD** (Re-implement API using JWT keys and standard SSL config) | **LOW** |
| **dev_agent.py** | `override/execution/providers/sandbox/` | **REFACTOR** (Integrate subprocess runs into isolated Docker containers) | **HIGH** |
| **browser_control.py** | `override/execution/providers/browser/` | **REFACTOR** (Adapt playwright parameters to fit generic Execution Engine API) | **MEDIUM** |
| **screen_processor.py** | `override/cognition/perception/` | **REFACTOR** (Fix ready flag race issues and audio conflicts) | **MEDIUM** |

---

## 10. Migration Order

### Stage 1: Core Decoupling
- Extract all API key validation, directory builders, and prompt loaders out of `main.py` into `override/runtime/core/config.py`.
- Isolate the Qt interface calls in `main.py` by converting direct UI updates to an abstract observer event system.
- Build the initial typed `override/runtime/core/events.py` bus to route input and output packages.

### Stage 2: Cognition and Tool Partitioning
- Decouple target tool configurations from `main.py`. Build a dynamic `override/runtime/core/registry.py` engine to register and invoke tools.
- Refactor local LLM helper client (`llm_client.py`) into the cognition directory to warm and handle planning tasks.
- Restructure the JSON memory manager to utilize relational storage.

### Stage 3: Execution Sandboxing
- Implement sandbox managers around the dev agent and terminal helper modules.
- Refactor Playwright browser parameters and pyautogui mouse drivers to align with the core Execution Engine API.
- Port the SystemMonitor class to background tracking services.

### Stage 4: Subsystem Migration and Replacement
- Replace PyQt6 dashboard HUD with the Electron frame application, connecting via secure WebSockets.
- Hard-kill legacy `main.py` loops, changing the main execution entry points to the new Override module structure.
- Clean up obsolete files, tests, and duplicate libraries.

---

## 11. Modules To Preserve
- **browser_control.py**: Contains highly detailed selectors and navigators for Chrome, Edge, and Safari configurations. It provides proven cross-platform browser logic that works without modification.
- **game_updater.py**: Represents a complete Steam/Epic Games local library management integration. Provides specific system update behaviors that do not require architectural replacement.
- **file_processor.py**: Implements extensive media converter and file reader support (covering PDFs, CSVs, Word files, Audio codecs). Re-writing this would represent significant wasted developer effort.

---

## 12. Modules To Refactor
- **dev_agent.py**:
  - *Why*: Executing arbitrary shell scripts directly on the root user shell risks severe platform degradation or malware vectors.
  - *Target Architecture*: Run commands in isolated Docker containers, capturing stdout/stderr safely.
  - *Estimated Effort*: **Medium (3 days)**.
- **screen_processor.py**:
  - *Why*: Visual pipeline thread creates a race condition on setup (ready flags set before WebSocket connects) and can stream conflicting audio streams.
  - *Target Architecture*: Connect through a single event manager, capturing frames and passing them directly to the main perception client.
  - *Estimated Effort*: **Low (1 day)**.
- **memory_manager.py**:
  - *Why*: JSON limit truncation discards critical user history logs.
  - *Target Architecture*: SQLite storage indexer allowing semantic classification.
  - *Estimated Effort*: **Medium (2 days)**.

---

## 13. Modules To Replace
- **ui.py**:
  - *Reason*: PyQt6 is difficult to scale for premium glassmorphism layouts, responsive layouts, or native animations.
  - *Replacement Strategy*: Electron desktop wrapper serving a React browser instance with Tailwind CSS support.
  - *Risks*: Higher system resource footprint (memory use increases).
- **dashboard/server.py**:
  - *Reason*: PIN authentication method lacks cryptographic salts, rate limits, or SSL encryption.
  - *Replacement Strategy*: FastAPI endpoint rebuild with JWT tokens, OAuth permission structures, and custom SSL cert configs.
  - *Risks*: Requires client app reconfiguration and secure key storage.
- **Tool Routing Logic in main.py**:
  - *Reason*: God-method routing makes additions highly complex and error-prone.
  - *Replacement Strategy*: Implement an abstract Registry handler allowing declarative registration of tools.
  - *Risks*: Minor routing latency overhead.

---

## 14. Modules To Remove
- **os._exit calls**:
  - *Reason*: Hard kills bypass resource flushes, leaving orphan sockets and browser processes.
  - *Impact*: Minor resource leaks on exit. Clean cancellation handlers must be installed.
  - *Dependencies*: Affected by WebSocket reconnection state.
- **stt.py and tts.py**:
  - *Reason*: Leftover dead code. Gemini Live handles voice inputs and output modulations natively.
  - *Impact*: Zero system impact.
  - *Dependencies*: None.
- **google-generativeai legacy package**:
  - *Reason*: Redundant SDK usage. Consolidating to `google-genai` reduces system package size and maintenance drag.
  - *Impact*: Requires clean import updates in dev_agent and screen_processor.
  - *Dependencies*: dev_agent, screen_processor.

---

## 15. Technical Debt

| Debt | Description | Impact | Recommended Fix | Priority |
|---|---|---|---|---|
| **Hard Exit Calls** | Uses `os._exit(0)` to force application termination. | Leaves background browser windows and file buffers locked. | Rebuild exit signals using standard async cancel triggers. | **HIGH** |
| **Shared Executor Exhaustion** | Synchronous actions run inside default ThreadPoolExecutor without dedicated pools. | voice network loops freeze or stutter when running files. | Bind separate worker threads for audio and execution tools. | **HIGH** |
| **Redundant API Clients** | Mixed imports of `genai` and legacy SDK frameworks. | Bloats source dependencies and results in duplicate model connection steps. | Remove legacy package and use the modern API SDK exclusively. | **MEDIUM** |
| **Memory Floor Erasure** | JSON writer silently deletes old database properties. | System loses key facts about user identity or projects. | Move storage to a SQLite DB with index parameters. | **MEDIUM** |

---

## 16. Risks
- **Migration Risks**: Refactoring the massive `main.py` script into smaller modules risks breaking timing sequences in the Gemini Live audio packet transmission stream.
- **Security Risks**: Insecure command executions in code agents represent a potential root system access vector if the LLM plan is hijacked.
- **Performance Risks**: Transitioning from a native PyQt6 GUI thread to a Chromium-based Electron runtime increases memory requirements from ~100MB to ~300-400MB.
- **Compatibility Risks**: Porting comtypes and win32 modules to core Override packages risks breaking portability on macOS and Linux systems.

---

## 17. Repository Health

- **Architecture Score**: **4 / 10** (Highly monolithic, tight connection couplings, direct side-effects in logic files).
- **Maintainability**: **5 / 10** (Extending features requires manually modifying multiple file targets).
- **Security**: **2 / 10** (Unsandboxed executions, plaintext dashboard tokens, weak key derivation).
- **Performance**: **6 / 10** (Fast, but prone to execution stutters and resource leaks).
- **Scalability**: **3 / 10** (Cannot easily separate UI from Core backend execution).
- **Documentation**: **5 / 10** (Functional schemas, but missing system architectures or debug run docs).
- **Overall Health**: **Yellow (Draft Stage)**. Good baseline framework, but requires clean separation of concerns and security refactoring before production.

---

## 18. Final Engineering Summary
- **Strongest Part**: The Playwright automation (`browser_control.py`) and hardware update scripts (`game_updater.py`) are highly detailed, stable, and work reliably.
- **Weakest Part**: Monolithic orchestration and direct terminal execution code blocks.
- **Biggest Architectural Bottleneck**: Synchronous blocking actions sharing default asyncio execution pools, causing voice stutters.
- **Biggest Opportunity**: Transitioning to a clean React/Electron UI framework while isolating execution routines behind abstract, sandboxed APIs.
- **Recommended Next Step**: Refactor `main.py` configuration parameters and extract tool routing logic out of the core asyncio connection handler loop.

---

## 19. Ownership Map

| Module | Owner |
|---|---|
| **Voice** | Input System |
| **Browser** | Execution |
| **Memory** | Memory Engine |
| **Planner** | Planner |
| **Verification** | Verification |
| **UI** | Frontend |
| **Runtime** | Runtime Foundation |
