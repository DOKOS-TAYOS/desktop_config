from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any


_DEFAULT_LEVEL_NAME = "INFO"
_HANDLER_MARKER = "_sunsetup_handler"


def _coerce_level(level_name: str | None) -> int:
    normalized = (
        level_name or os.getenv("SUNSETUP_LOG_LEVEL", _DEFAULT_LEVEL_NAME)
    ).upper()
    return getattr(logging, normalized, logging.INFO)


def env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = value if len(value) <= 120 else f"{value[:117]}..."
        if any(character.isspace() for character in text) or any(
            character in text for character in ('"', "=")
        ):
            return json.dumps(text)
        return text
    if value is None:
        return "null"
    if isinstance(value, dict):
        return f"<dict len={len(value)}>"
    if isinstance(value, (list, tuple, set)):
        return f"<{type(value).__name__} len={len(value)}>"
    return json.dumps(str(value))


def build_event_message(event: str, **fields: Any) -> str:
    parts = [f"event={_format_value(event)}"]
    for key in sorted(fields):
        value = fields[key]
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")
    return " ".join(parts)


def setup_logging(
    *, force: bool = False, level_name: str | None = None
) -> logging.Logger:
    root_logger = logging.getLogger()
    if force:
        for handler in list(root_logger.handlers):
            if getattr(handler, _HANDLER_MARKER, False):
                root_logger.removeHandler(handler)

    level = _coerce_level(level_name)
    existing_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if getattr(handler, _HANDLER_MARKER, False)
        ),
        None,
    )
    if existing_handler is None:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler = logging.StreamHandler(sys.stdout)
        setattr(handler, _HANDLER_MARKER, True)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        root_logger.addHandler(handler)
    else:
        existing_handler.setLevel(level)

    root_logger.setLevel(level)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, build_event_message(event, **fields))


@dataclass(frozen=True, slots=True)
class BoundLogger:
    logger: logging.Logger
    context_fields: dict[str, Any]

    def bind(self, **fields: Any) -> "BoundLogger":
        return BoundLogger(self.logger, {**self.context_fields, **fields})

    def event(self, level: int, event: str, **fields: Any) -> None:
        log_event(self.logger, level, event, **{**self.context_fields, **fields})

    def debug(self, event: str, **fields: Any) -> None:
        self.event(logging.DEBUG, event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self.event(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.event(logging.WARNING, event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.event(logging.ERROR, event, **fields)

    def exception(self, event: str, **fields: Any) -> None:
        self.logger.exception(
            build_event_message(event, **{**self.context_fields, **fields})
        )


def bind_context(logger: logging.Logger, **fields: Any) -> BoundLogger:
    return BoundLogger(
        logger, {key: value for key, value in fields.items() if value is not None}
    )
