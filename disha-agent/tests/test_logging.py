"""Structured JSON logging tests — JSON lines, secret redaction."""
from __future__ import annotations

import json
import logging

from app.logging_config import REDACTED, JsonFormatter, sanitize


def _format(msg: str = "hello", **extra) -> dict:
    record = logging.LogRecord("disha.test", logging.INFO, __file__, 1, msg, (), None)
    for k, v in extra.items():
        setattr(record, k, v)
    return json.loads(JsonFormatter().format(record))


def test_log_line_is_json():
    payload = _format(user_id="u1")
    assert payload["level"] == "INFO"
    assert payload["logger"] == "disha.test"
    assert payload["message"] == "hello"
    assert payload["user_id"] == "u1"
    assert "timestamp" in payload


def test_sensitive_keys_redacted():
    payload = _format(
        authorization="Bearer abc.def.ghi",
        api_key="sk-123",
        supabase_jwt_secret="shh",
        password="hunter2",
        user_id="u1",
    )
    assert payload["authorization"] == REDACTED
    assert payload["api_key"] == REDACTED
    assert payload["supabase_jwt_secret"] == REDACTED
    assert payload["password"] == REDACTED
    assert payload["user_id"] == "u1"
    dumped = json.dumps(payload)
    assert "abc.def.ghi" not in dumped
    assert "sk-123" not in dumped
    assert "shh" not in dumped


def test_nested_secrets_redacted():
    payload = _format(request={"headers": {"authorization": "Bearer t0k3n"}})
    assert payload["request"]["headers"]["authorization"] == REDACTED
    assert "t0k3n" not in json.dumps(payload)


def test_sanitize_leaves_safe_values():
    data = {"user_id": "u1", "thread_id": "t1", "items": [{"price_inr": 100}]}
    assert sanitize(data) == data