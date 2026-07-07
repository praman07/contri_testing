import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from override.runtime.logging.formatter import ConsoleLogFormatter, JsonLogFormatter

def create_console_sink() -> logging.StreamHandler:
    """Creates a StreamHandler directed to stdout with ANSI color formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ConsoleLogFormatter())
    return handler

def create_file_sink(
    file_path: str,
    max_bytes: int = 10485760,
    backup_count: int = 5
) -> RotatingFileHandler:
    """
    Creates a thread-safe, rolling file log handler with JSON formatting.
    Ensures directory structure exists.
    """
    # Guarantee containing folder exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    handler.setFormatter(JsonLogFormatter())
    return handler
