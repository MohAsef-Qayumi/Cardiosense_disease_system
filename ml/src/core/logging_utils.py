"""Logging configuration helpers for CardioSense."""

import logging
from contextvars import ContextVar

from src.core.settings import Settings

REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach the active request id to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_CTX.get()
        return True


def configure_logging(settings: Settings) -> None:
    """Configure process-wide logging once."""
    root_logger = logging.getLogger()
    if getattr(root_logger, "_cardiosense_configured", False):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)
    root_logger._cardiosense_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
