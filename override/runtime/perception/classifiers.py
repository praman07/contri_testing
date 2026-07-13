"""
Application category classifier for the Perception Engine (Layer 03).

Maps known application names and window class names to a small set of
standardized categories that higher-layer engines can reason about without
knowing every application by name.

No OS calls are made here — all input comes from event payloads produced by
the Environment Engine (Layer 02).
"""
from typing import Dict

# --- Category keyword maps -----------------------------------------------
# Keys are lowercased fragments matched against window title or exe name.
# Ordering matters: first match wins.

_TITLE_RULES: Dict[str, str] = {
    # Browsers
    "chrome": "browser",
    "firefox": "browser",
    "edge": "browser",
    "safari": "browser",
    "opera": "browser",
    "brave": "browser",
    "arc": "browser",

    # IDEs / Editors
    "visual studio code": "ide",
    "vscode": "ide",
    "pycharm": "ide",
    "intellij": "ide",
    "webstorm": "ide",
    "rider": "ide",
    "clion": "ide",
    "android studio": "ide",
    "xcode": "ide",
    "sublime": "ide",
    "vim": "ide",
    "neovim": "ide",
    "emacs": "ide",
    "cursor": "ide",
    "notepad++": "ide",

    # Terminals
    "terminal": "terminal",
    "powershell": "terminal",
    "cmd": "terminal",
    "command prompt": "terminal",
    "bash": "terminal",
    "wsl": "terminal",
    "konsole": "terminal",
    "iterm": "terminal",
    "alacritty": "terminal",
    "windows terminal": "terminal",
    "git bash": "terminal",

    # Communications
    "slack": "comms",
    "discord": "comms",
    "teams": "comms",
    "zoom": "comms",
    "meet": "comms",
    "telegram": "comms",
    "whatsapp": "comms",
    "signal": "comms",
    "outlook": "comms",
    "thunderbird": "comms",

    # Office / Documents
    "word": "office",
    "excel": "office",
    "powerpoint": "office",
    "libreoffice": "office",
    "google docs": "office",
    "google sheets": "office",
    "google slides": "office",
    "notion": "office",
    "obsidian": "office",

    # Media
    "spotify": "media",
    "vlc": "media",
    "youtube": "media",
    "netflix": "media",
    "prime video": "media",
    "plex": "media",
    "mpv": "media",
}

_CLASS_RULES: Dict[str, str] = {
    "chrome_widgetwin": "browser",
    "mozillawindowclass": "browser",
    "aura_window": "browser",
    "vscode_mainfrmde": "ide",
    "consolewindowclass": "terminal",
    "mintty": "terminal",
}


def classify_app(window_title: str, window_class: str, exe_name: str) -> str:
    """
    Returns a standardized application category string from window metadata.

    Args:
        window_title: The visible window title string.
        window_class: The OS window class name.
        exe_name: The process executable name (e.g. 'chrome.exe').

    Returns:
        One of: 'browser', 'ide', 'terminal', 'comms', 'office', 'media', 'unknown'.
    """
    title_lower = (window_title or "").lower()
    class_lower = (window_class or "").lower()
    exe_lower = (exe_name or "").lower().replace(".exe", "")

    # 1. Match by title
    for fragment, category in _TITLE_RULES.items():
        if fragment in title_lower:
            return category

    # 2. Match by window class
    for fragment, category in _CLASS_RULES.items():
        if fragment in class_lower:
            return category

    # 3. Match by exe name
    for fragment, category in _TITLE_RULES.items():
        if fragment in exe_lower:
            return category

    return "unknown"
