import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    """One JSON object per line: easy to ship to Loki/ELK/CloudWatch and to grep."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        extra_fields = getattr(record, "fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str, json_logs: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # We log requests ourselves (with request id and duration).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
