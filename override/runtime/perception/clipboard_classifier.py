"""
Clipboard content type classifier for the Perception Engine (Layer 03).

Classifies clipboard text payloads into semantic types so that higher layers
can reason about what the user has copied without inspecting raw text content.

No OS calls — all input is the clipboard payload dict from Environment events.
"""
import re
from typing import Dict, Any


# Regex patterns for fast heuristic classification
_URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)

# Very rough code heuristics — presence of common keywords or symbols
_CODE_INDICATORS = frozenset([
    "def ", "class ", "import ", "from ", "function ", "const ", "let ", "var ",
    "return ", "if (", "if(", "for (", "for(", "while(", "while (", "=>", "->",
    "public ", "private ", "void ", "int ", "string ", "bool ", "#include", "namespace",
    "SELECT ", "INSERT ", "UPDATE ", "DELETE ", "FROM ", "WHERE ",
    "<!DOCTYPE", "<html", "<?php",
])


def classify_clipboard(clipboard_payload: Dict[str, Any]) -> str:
    """
    Classifies clipboard content into a semantic type string.

    Args:
        clipboard_payload: The clipboard_state dict from an EnvironmentSnapshot,
                           containing at minimum 'type', 'length', and optionally 'text'.

    Returns:
        One of: 'url', 'code', 'plain_text', 'empty'.
    """
    clip_type = clipboard_payload.get("type", "empty")
    if clip_type == "empty" or clipboard_payload.get("length", 0) == 0:
        return "empty"

    # We may receive the raw text if the perception layer is given access to it
    text = clipboard_payload.get("text", "")
    if not text:
        # Without raw text we can only confirm it is non-empty text
        return "plain_text"

    stripped = text.strip()

    if _URL_PATTERN.match(stripped):
        return "url"

    # Check for code indicators
    for indicator in _CODE_INDICATORS:
        if indicator in stripped:
            return "code"

    return "plain_text"
