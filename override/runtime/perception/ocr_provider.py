"""
OCR provider stub for the Perception Engine (Layer 03).

Provides a safe, importable OCR interface that either:
  - Uses pytesseract when available on the host system
  - Returns an empty string gracefully when pytesseract is not installed

This keeps the Perception Engine operational on any machine without a hard
dependency on Tesseract. OCR is an enhancement, not a requirement.
"""
import logging
from typing import Optional

logger = logging.getLogger("Override.Perception.OCR")

_TESSERACT_AVAILABLE: Optional[bool] = None


def _check_tesseract() -> bool:
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        return _TESSERACT_AVAILABLE
    try:
        import pytesseract  # type: ignore
        pytesseract.get_tesseract_version()
        _TESSERACT_AVAILABLE = True
        logger.info("Tesseract OCR engine detected and available.")
    except Exception:
        _TESSERACT_AVAILABLE = False
        logger.info("Tesseract OCR engine not available — OCR will be skipped.")
    return _TESSERACT_AVAILABLE


def extract_text_from_bytes(image_bytes: bytes) -> str:
    """
    Attempt to perform OCR on raw image bytes.
    Returns extracted text, or an empty string if OCR is unavailable or fails.

    Args:
        image_bytes: Raw image data (PNG or JPEG bytes).

    Returns:
        Extracted text string, empty if OCR is unavailable or failed.
    """
    if not _check_tesseract():
        return ""
    if not image_bytes:
        return ""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        import io
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return (text or "").strip()
    except Exception as e:
        logger.debug(f"OCR extraction failed: {e}")
        return ""
