import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Any

class narsLogger:
    """A wrapper for a standard logger to allow optional console output."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level DEBUG and optionally prints to console."""
        self._logger.debug(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.DEBUG):
            print(f"[DEBUG] {msg % args if args else msg}")

    def info(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level INFO and optionally prints to console."""
        self._logger.info(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.INFO):
            print(f"[INFO] {msg % args if args else msg}")

    def warning(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level WARNING and optionally prints to console."""
        self._logger.warning(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.WARNING):
            print(f"[WARNING] {msg % args if args else msg}")

    def error(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level ERROR and optionally prints to console."""
        self._logger.error(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.ERROR):
            print(f"[ERROR] {msg % args if args else msg}")

    def critical(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level CRITICAL and optionally prints to console."""
        self._logger.critical(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.CRITICAL):
            print(f"[CRITICAL] {msg % args if args else msg}")

    def fatal(self, msg: Any, *args: Any, console: bool = False, **kwargs: Any) -> None:
        """Logs a message with level FATAL and optionally prints to console."""
        self._logger.fatal(msg, *args, **kwargs)
        if console and self._logger.isEnabledFor(logging.FATAL):
            print(f"[FATAL] {msg % args if args else msg}")

    def __getattr__(self, name: str) -> Any:
        """
        Fall back to the original logger for any other methods
        (e.g., setLevel, debug, critical).
        """
        return getattr(self._logger, name)