import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variables for distributed request and delegation chain tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
chain_id_ctx: ContextVar[Optional[str]] = ContextVar("chain_id", default=None)
task_id_ctx: ContextVar[Optional[str]] = ContextVar("task_id", default=None)


class JSONLogFormatter(logging.Formatter):
    """
    Structured JSON Formatter emitting machine-readable log records
    with contextual metadata (request_id, chain_id, task_id).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_ctx.get(),
            "chain_id": chain_id_ctx.get(),
            "task_id": task_id_ctx.get(),
        }

        # Include custom extra fields if attached
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["extra"] = record.extra_data

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """
    Configure root and application loggers.
    """
    logger = logging.getLogger("governance_ai")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONLogFormatter())
    else:
        standard_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        )
        handler.setFormatter(standard_formatter)

    logger.addHandler(handler)
    return logger


logger = setup_logging()
