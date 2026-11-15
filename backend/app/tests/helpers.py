import io
import re
from typing import Any

from httpx import AsyncClient, Response
from PIL import Image

from app.core.email import OUTBOX

PASSWORD = "correct-horse-battery"
API = "/api/v1"


def email_for(username: str) -> str:
    return f"{username}@example.com"


async def signup(client: AsyncClient, username: str = "alice", password: str = PASSWORD) -> dict[str, Any]:
    """Register + log in. The client's cookie jar now holds the session."""
    registered = await client.post(
        f"{API}/auth/register",
        json={"email": email_for(username), "username": username, "password": password},
    )
    assert registered.status_code == 201, registered.text
    logged_in = await client.post(
        f"{API}/auth/login", json={"email": email_for(username), "password": password}
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()


def cookie_value(response: Response, name: str) -> str | None:
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            return header.split(";", 1)[0].split("=", 1)[1]
    return None


def token_from_outbox(index: int = -1) -> str:
    """Pull the ?token=... value out of the latest captured email."""
    match = re.search(r"token=([A-Za-z0-9_\-]+)", OUTBOX[index].body)
    assert match, OUTBOX[index].body
    return match.group(1)


def make_png(width: int = 64, height: int = 48, color: str = "red") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


async def create_post(client: AsyncClient, content: str = "hello world", **extra: Any) -> dict[str, Any]:
    response = await client.post(f"{API}/posts", json={"content": content, **extra})
    assert response.status_code == 201, response.text
    return response.json()
