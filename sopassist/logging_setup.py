"""Structured JSON logs with a per-request correlation id (contextvar)."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_STD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": round(time.time(), 3), "level": record.levelname, "logger": record.name,
               "msg": record.getMessage(), "request_id": request_id_var.get()}
        out.update({k: v for k, v in record.__dict__.items() if k not in _STD})
        return json.dumps(out, default=str)


def setup_logging(level: str = "INFO") -> None:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
