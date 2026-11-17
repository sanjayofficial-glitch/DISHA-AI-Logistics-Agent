"""Structured JSON logging for DISHA.

Every log line is a single JSON object. Sensitive keys (bearer tokens, API
keys, authorization headers, JWT secrets, passwords) are redacted before
anything is written, so tokens and keys never reach the logs.

Usage:
    from .logging_config import configure_logging, get_logger
    configure_logging()
    logger = get_logger(__name__)
    logger.info("user_login", extra={"user_id": user_id})  # never extra={"token": ...}
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from typing import Any

# Any extra field whose name contains one of these markers is redacted.
_SENSITIVE_MARKERS = (
    "token",
    "authorization",
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "jwt",
    "cookie",
    "credential",
    "private_key",
)

REDACTED = "***REDACTED***"

# Standard LogRecord attributes — anything else is an "extra" field.
_STANDARD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(marker in k for marker in _SENSITIVE_MARKERS)


def sanitize(value: Any) -> Any:
    """Recursively redact sensitive keys from dicts/lists before logging."""
    if isinstance(value, dict):
        return {
            k: (REDACTED if _is_sensitive_key(str(k)) else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    """Format each log record as one single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Structured "extra" fields (everything not a standard LogRecord attr).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(sanitize(payload), default=str)


def configure_logging(level: str | None = None) -> None:
    """Install the JSON formatter on the root logger (idempotent)."""
    from .config import settings  # local import: avoids an import cycle

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel((level or settings.log_level).upper())
    # Keep noisy HTTP clients at warnings; they must never log request data.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)