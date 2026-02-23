"""Customer Success Agent package — structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar

# ---------------------------------------------------------------------------
# Correlation ID — propagated across async tasks via contextvars
# ---------------------------------------------------------------------------
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the current correlation ID (empty string if unset)."""
    return _correlation_id.get()


def set_correlation_id(cid: str | None = None) -> str:
    """Set (or generate) a correlation ID for the current async context."""
    cid = cid or uuid.uuid4().hex
    _correlation_id.set(cid)
    return cid


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------
class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        cid = get_correlation_id()
        if cid:
            payload["correlation_id"] = cid
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Bootstrap — call once at import time
# ---------------------------------------------------------------------------
def _configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers on re-import
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _JSONFormatter) for h in root.handlers):
        root.addHandler(handler)


_configure_logging()
