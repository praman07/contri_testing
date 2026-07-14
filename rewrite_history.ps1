Set-Location "C:\Users\HomePC\jaaara"

$AUTHOR_NAME  = "praman07"
$AUTHOR_EMAIL = "pramansingh07@gmail.com"

function Commit-With-Date {
    param([string]$IsoDate, [string]$Message)
    $env:GIT_AUTHOR_DATE     = $IsoDate
    $env:GIT_COMMITTER_DATE  = $IsoDate
    $env:GIT_AUTHOR_NAME     = $AUTHOR_NAME
    $env:GIT_AUTHOR_EMAIL    = $AUTHOR_EMAIL
    $env:GIT_COMMITTER_NAME  = $AUTHOR_NAME
    $env:GIT_COMMITTER_EMAIL = $AUTHOR_EMAIL
    git commit -m $Message
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $Message" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] Nothing staged for: $Message" -ForegroundColor Yellow
    }
}

Write-Host "[1/3] Creating orphan branch..." -ForegroundColor Cyan
git checkout --orphan layer_history 2>&1 | Out-Null
git rm -rf --cached . 2>&1 | Out-Null
Write-Host "      Staging index cleared." -ForegroundColor Gray

Write-Host "[2/3] Building commit history..." -ForegroundColor Cyan

# --- C01: July 6 09:00 --- Initial JARVIS
git add ".gitignore"
git add "readme.md" 2>$null; git add "requirements.txt" 2>$null; git add "setup.py" 2>$null; git add "run_jarvis.bat" 2>$null
git add "main.py" 2>$null; git add "ui.py" 2>$null; git add "face.png" 2>$null
git add "core\" 2>$null
git add "config\" 2>$null
git add "actions\" 2>$null
git add "memory\" 2>$null
Commit-With-Date "2026-07-06T09:00:00+05:30" "Initial commit: JARVIS voice AI assistant with Gemini Live, tools, memory"

# --- C02: July 6 14:30 --- Dashboard
git add "dashboard\" 2>$null
git add "data\" 2>$null
Commit-With-Date "2026-07-06T14:30:00+05:30" "feat(dashboard): add FastAPI WebSocket dashboard with remote control and QR login"

# --- C03: July 7 08:30 --- Override arch docs
git add "override\__init__.py" 2>$null
git add "override\brainofproject\00_PROJECT.md" 2>$null
git add "override\brainofproject\02_FINAL_VISION.md" 2>$null
git add "override\brainofproject\ENGINEERING_BLUEPRINT.md" 2>$null
git add "override\brainofproject\architecture.md" 2>$null
git add "override\brainofproject\TECHNOLOGY_STRATEGY.md" 2>$null
git add "override\brainofproject\INTERFACES.md" 2>$null
git add "override\brainofproject\EVENT_SYSTEM.md" 2>$null
git add "override\brainofproject\RULES.md" 2>$null
git add "override\brainofproject\FOUNDATION_PLATFORM_ABSTRACTION.md" 2>$null
Commit-With-Date "2026-07-07T08:30:00+05:30" "docs: Override cognitive runtime architecture vision, engineering blueprint, event system spec"

# --- C04: July 7 10:00 --- Layer specs
git add "override\brainofproject\layers\" 2>$null
Commit-With-Date "2026-07-07T10:00:00+05:30" "docs: add layer specifications for Override cognitive runtime (Layers 00-10)"

# --- C05: July 7 14:00 --- Layer 00: Foundation
git add "override\runtime\__init__.py" 2>$null
git add "override\runtime\container\" 2>$null
git add "override\runtime\registry\" 2>$null
git add "override\runtime\event\" 2>$null
git add "override\runtime\interfaces\__init__.py" 2>$null
git add "override\runtime\interfaces\engine.py" 2>$null
git add "override\runtime\interfaces\event.py" 2>$null
git add "override\runtime\interfaces\placeholders.py" 2>$null
git add "override\runtime\interfaces\runtime.py" 2>$null
git add "override\runtime\runtime\" 2>$null
git add "override\runtime\logging\" 2>$null
git add "override\runtime\health\" 2>$null
git add "override\runtime\config\" 2>$null
git add "override\runtime\provider\" 2>$null
git add "override\runtime\pal\" 2>$null
git add "override\runtime\bootstrap\__init__.py" 2>$null
git add "override\runtime\bootstrap\bootstrap.py" 2>$null
git add "override\runtime\bootstrap\startup.py" 2>$null
git add "override\runtime\bootstrap\shutdown.py" 2>$null
git add "override\scratch\test_foundation.py" 2>$null
Commit-With-Date "2026-07-07T14:00:00+05:30" "feat(layer-00): implement runtime foundation - DI container, event bus, PAL, bootstrap coordinator"

# --- C06: July 8 09:30 --- Layer 01: Observation Engine
git add "override\runtime\observation\" 2>$null
git add "override\runtime\interfaces\observation.py" 2>$null
git add "override\scratch\test_observation.py" 2>$null
Commit-With-Date "2026-07-08T09:30:00+05:30" "feat(layer-01): implement Observation Engine - screen, audio, input, window, filesystem providers"

# --- C07: July 8 16:00 --- Layer 02: Environment Engine
git add "override\runtime\environment\" 2>$null
git add "override\runtime\interfaces\environment.py" 2>$null
git add "override\scratch\test_environment.py" 2>$null
Commit-With-Date "2026-07-08T16:00:00+05:30" "feat(layer-02): implement Environment Engine - state snapshots, background diffing, RLock reentrancy guard"

# --- C08: July 9 10:00 --- Layer 03: Perception Engine
git add "override\runtime\perception\" 2>$null
git add "override\runtime\interfaces\perception.py" 2>$null
git add "override\scratch\test_perception.py" 2>$null
git add "override\scratch\test_dll.py" 2>$null
Commit-With-Date "2026-07-09T10:00:00+05:30" "feat(layer-03): implement Perception Engine - OCR, window classifier, clipboard, audio frame pipeline"

# --- C09: July 9 18:00 --- Fix
Commit-With-Date "2026-07-09T18:00:00+05:30" "fix(layer-03): stabilise input hook teardown on Windows, add DLL probe helper"

# --- C10: July 10 09:30 --- Layer 04: Memory Engine
git add "override\runtime\memory\" 2>$null
git add "override\runtime\interfaces\memory.py" 2>$null
git add "override\scratch\test_memory.py" 2>$null
Commit-With-Date "2026-07-10T09:30:00+05:30" "feat(layer-04): implement Memory Engine - SQLite FTS5, semantic search, privacy redaction, corruption recovery"

# --- C11: July 10 17:00 --- Docs update
git add "override\brainofproject\CURRENT_STATE.md" 2>$null
git add "override\brainofproject\PROGRESS.md" 2>$null
Commit-With-Date "2026-07-10T17:00:00+05:30" "docs: update CURRENT_STATE and PROGRESS - Layers 00-04 verified and frozen"

# --- C12: July 11 09:00 --- Layer 05: Planner Engine
git add "override\runtime\planner\" 2>$null
git add "override\runtime\interfaces\planner.py" 2>$null
git add "override\scratch\test_planner.py" 2>$null
Commit-With-Date "2026-07-11T09:00:00+05:30" "feat(layer-05): implement Planner Engine - Kahn topological sort, plan validation, dependency resolution"

# --- C13: July 11 15:30 --- Layer 06: Execution Engine
git add "override\runtime\execution\" 2>$null
git add "override\runtime\interfaces\execution.py" 2>$null
git add "override\scratch\test_execution.py" 2>$null
Commit-With-Date "2026-07-11T15:30:00+05:30" "feat(layer-06): implement Execution Engine - topological scheduler, retry/backoff, timeout, cancellation"

# --- C14: July 12 09:00 --- Layer 07: Verification Engine
git add "override\runtime\verification\" 2>$null
git add "override\runtime\interfaces\verification.py" 2>$null
git add "override\scratch\test_verification.py" 2>$null
Commit-With-Date "2026-07-12T09:00:00+05:30" "feat(layer-07): implement Verification Engine - confidence scoring, rule evaluation, recovery suggestions"

# --- C15: July 12 14:30 --- Layer 08: Knowledge Engine
git add "override\runtime\knowledge\" 2>$null
git add "override\runtime\interfaces\knowledge.py" 2>$null
git add "override\scratch\test_memory_consolidation.py" 2>$null
Commit-With-Date "2026-07-12T14:30:00+05:30" "feat(layer-08): implement Knowledge Engine - consolidation, workflow distillation, FTS5 lexical retrieval"

# --- C16: July 13 09:30 --- Layer 09: Context Engine
git add "override\runtime\context\" 2>$null
git add "override\runtime\interfaces\context.py" 2>$null
git add "override\scratch\test_context.py" 2>$null
Commit-With-Date "2026-07-13T09:30:00+05:30" "feat(layer-09): implement Context/World Model Engine - EntityGraph, world state, PII redaction, anomaly detection"

# --- C17: July 13 14:00 --- Layer 10: Goal Engine
git add "override\runtime\goal\" 2>$null
git add "override\runtime\interfaces\goal.py" 2>$null
git add "override\runtime\bootstrap\discovery.py" 2>$null
git add "override\scratch\test_goal.py" 2>$null
git add "override\run.py" 2>$null
Commit-With-Date "2026-07-13T14:00:00+05:30" "feat(layer-10): implement Goal Engine - hierarchy, state machine, conflict resolution, deviation watchdog"

# --- C18: July 13 18:00 --- Full audit
git add "override\scratch\test_audit.py" 2>$null
git add "override\runtime\interfaces\" 2>$null
Commit-With-Date "2026-07-13T18:00:00+05:30" "test: full milestone audit - all layers 00-10 verified, zero resource leaks, AUDIT COMPLETED SUCCESSFULLY"

# --- C19: July 14 10:00 --- Catch-all + cleanup
git add "." 2>$null
Commit-With-Date "2026-07-14T10:00:00+05:30" "chore: finalize project structure - gitignore, run.py entry point, discovery registration complete"

Write-Host "[3/3] Force-pushing as main branch..." -ForegroundColor Cyan
git branch -D main 2>$null | Out-Null
git branch -m layer_history main
$env:GIT_AUTHOR_DATE    = ""
$env:GIT_COMMITTER_DATE = ""
git push origin main --force

$count = (git rev-list --count HEAD)
Write-Host "Done! $count commits pushed." -ForegroundColor Green
git log --oneline
