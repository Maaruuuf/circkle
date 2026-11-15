import io

from httpx import AsyncClient
from PIL import Image

from app.tests.helpers import API, make_png, signup


async def test_upload_reencodes_to_webp_and_serves_with_cache_headers(client: AsyncClient) -> None:
    await signup(client, "alice")

    response = await client.post(
        f"{API}/media/images", files={"file": ("../../evil name.png", make_png(100, 80), "image/png")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["url"].startswith("/media/") and data["url"].endswith(".webp")  # client filename ignored
    served = await client.get(data["url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"
    assert "immutable" in served.headers["cache-control"]
    assert Image.open(io.BytesIO(served.content)).format == "WEBP"


async def test_upload_strips_exif_metadata(client: AsyncClient) -> None:
    await signup(client, "alice")
    image = Image.new("RGB", (50, 50), "blue")
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    response = await client.post(
        f"{API}/media/images", files={"file": ("a.jpg", buffer.getvalue(), "image/jpeg")}
    )
    served = await client.get(response.json()["url"])

    assert b"SecretCameraMaker" not in served.content
    assert not Image.open(io.BytesIO(served.content)).getexif()


async def test_upload_rejects_non_images_and_wrong_formats(client: AsyncClient) -> None:
    await signup(client, "alice")
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")

    script = await client.post(f"{API}/media/images", files={"file": ("a.png", b"<script>alert(1)</script>", "image/png")})
    gif_upload = await client.post(f"{API}/media/images", files={"file": ("a.gif", gif.getvalue(), "image/gif")})

    for response in (script, gif_upload):
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "INVALID_IMAGE"


async def test_upload_rejects_oversized_files(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    await signup(client, "alice")
    monkeypatch.setattr(settings, "max_upload_mb", 1)

    response = await client.post(
        f"{API}/media/images", files={"file": ("big.png", b"0" * (1024 * 1024 + 10), "image/png")}
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_upload_requires_login(client: AsyncClient) -> None:
    response = await client.post(f"{API}/media/images", files={"file": ("a.png", make_png(), "image/png")})

    assert response.status_code == 401


async def test_media_route_blocks_path_traversal_and_unknown_files(client: AsyncClient) -> None:
    for path in ("/media/..%2F..%2Fetc%2Fpasswd", "/media/notahash.webp", "/media/" + "a" * 32 + ".webp"):
        assert (await client.get(path)).status_code == 404
