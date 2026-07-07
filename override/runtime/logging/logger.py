import logging
from typing import Optional
from override.runtime.config.schema import LoggingConfig
from override.runtime.logging.sinks import create_console_sink, create_file_sink

class LoggingService:
    """
    Initializes and controls Override's structured logging configuration.
    Registers sinks and exposes the logging subsystem.
    """

    def __init__(self, config: LoggingConfig):
        self._level = getattr(logging, config.level.upper(), logging.INFO)
        self._file_path = config.file_path
        self._max_bytes = config.max_bytes
        self._backup_count = config.backup_count
        self._root_logger: Optional[logging.Logger] = None

    def initialize(self) -> None:
        """Configures the root Logger and attaches the console and file sinks."""
        self._root_logger = logging.getLogger("Override")
        self._root_logger.setLevel(self._level)
        self._root_logger.propagate = False  # Avoid duplicating messages in root log

        # Clear and close any existing handlers to prevent duplicates and resource leaks on restart
        if self._root_logger.handlers:
            for handler in list(self._root_logger.handlers):
                try:
                    handler.close()
                except Exception:
                    pass
                self._root_logger.removeHandler(handler)

        # Attach console output sink
        self._root_logger.addHandler(create_console_sink())

        # Attach structured JSON file output sink
        try:
            file_sink = create_file_sink(
                file_path=self._file_path,
                max_bytes=self._max_bytes,
                backup_count=self._backup_count
            )
            self._root_logger.addHandler(file_sink)
        except Exception as e:
            # Fallback to standard error log if folder writing fails
            sys_err_logger = logging.getLogger("Override.Bootstrap")
            sys_err_logger.error(f"Failed to create file log sink: {e}")

    def get_logger(self, name: str) -> logging.Logger:
        """Returns a configured sub-logger prefixed with the Override namespace."""
        # Ensure name falls under the Override namespace hierarchy
        logger_name = f"Override.{name}" if not name.startswith("Override") else name
        return logging.getLogger(logger_name)
