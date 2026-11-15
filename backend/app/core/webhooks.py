"""Outgoing webhooks: signed JSON events POSTed to WEBHOOK_URL.

Receivers verify authenticity by recomputing the HMAC:
    signature = HMAC_SHA256(secret, f"{timestamp}.{raw_body}")  -> header X-Circkle-Signature
and should reject timestamps older than a few minutes (replay protection).
Delivery is best-effort (no retries yet); see docs/ROADMAP.md for a queue-based design.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode() + b"." + body
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def dispatch_event(event: str, data: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.webhook_url:
        return
    body = json.dumps({"event": event, "data": data}, default=str).encode()
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Circkle-Event": event,
        "X-Circkle-Timestamp": timestamp,
        "X-Circkle-Signature": sign_payload(
            settings.webhook_secret.get_secret_value(), timestamp, body
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(settings.webhook_url, content=body, headers=headers)
        if response.status_code >= 400:
            logger.warning("webhook %s rejected with status %s", event, response.status_code)
    except httpx.HTTPError:
        logger.warning("webhook %s delivery failed", event)
