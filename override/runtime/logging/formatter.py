import json
import logging
from datetime import datetime, timezone

class ConsoleLogFormatter(logging.Formatter):
    """Clean, human-readable logging formatter for terminal output."""

    COLOR_CODES = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[1;31m" # Bold Red
    }
    RESET_CODE = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        level_color = self.COLOR_CODES.get(record.levelno, "")
        
        # Apply color code for console visualization if ANSI terminal output supports it
        level_label = f"{level_color}[{record.levelname}]{self.RESET_CODE}"
        message = record.getMessage()
        
        # Format stack trace if present
        exc_text = ""
        if record.exc_info:
            exc_text = f"\n{self.formatException(record.exc_info)}"
            
        return f"{timestamp} {level_label} [{record.name}] {message}{exc_text}"


class JsonLogFormatter(logging.Formatter):
    """Structured JSON formatter for telemetry, debugging, and audit logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)
