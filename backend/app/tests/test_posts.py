import uuid

from httpx import AsyncClient

from app.tests.helpers import API, create_post, make_png, signup


async def test_create_text_post(client: AsyncClient) -> None:
    await signup(client, "alice")

    post = await create_post(client, "  hello circkle  ")

    assert post["content"] == "hello circkle"
    assert post["author"]["username"] == "alice"
    assert post["image_url"] is None
    assert post["reaction_count"] == 0 and post["comment_count"] == 0


async def test_create_post_validation(client: AsyncClient) -> None:
    await signup(client, "alice")

    empty = await client.post(f"{API}/posts", json={})
    blank = await client.post(f"{API}/posts", json={"content": "   "})
    too_long = await client.post(f"{API}/posts", json={"content": "x" * 2001})
    extra = await client.post(f"{API}/posts", json={"content": "hi", "author_id": str(uuid.uuid4())})

    assert empty.status_code == 400 and empty.json()["error"]["code"] == "EMPTY_POST"
    assert blank.status_code == 400
    assert too_long.status_code == 422
    assert extra.status_code == 422


async def test_create_post_requires_login(client: AsyncClient) -> None:
    assert (await client.post(f"{API}/posts", json={"content": "hi"})).status_code == 401


async def test_post_with_image(client: AsyncClient) -> None:
    await signup(client, "alice")
    upload = await client.post(
        f"{API}/media/images", files={"file": ("a.png", make_png(), "image/png")}
    )
    assert upload.status_code == 201

    post = await create_post(client, "look at this", media_id=upload.json()["id"])

    assert post["image_url"] == upload.json()["url"]
    image_only = await create_post(client, None, media_id=upload.json()["id"])  # type: ignore[arg-type]
    assert image_only["content"] is None


async def test_cannot_attach_someone_elses_image(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    mallory = await make_client()
    await signup(client, "alice")
    await signup(mallory, "mallory")
    upload = await client.post(f"{API}/media/images", files={"file": ("a.png", make_png(), "image/png")})

    response = await mallory.post(
        f"{API}/posts", json={"content": "stolen", "media_id": upload.json()["id"]}
    )

    assert response.status_code == 400 and response.json()["error"]["code"] == "INVALID_MEDIA"


async def test_get_post_is_public(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    await signup(client, "alice")
    post = await create_post(client)

    guest = await make_client()

    assert (await guest.get(f"{API}/posts/{post['id']}")).status_code == 200
    missing = await guest.get(f"{API}/posts/{uuid.uuid4()}")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "POST_NOT_FOUND"
    assert (await guest.get(f"{API}/posts/not-a-uuid")).status_code == 422


async def test_only_author_can_edit(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    mallory = await make_client()
    await signup(client, "alice")
    await signup(mallory, "mallory")
    post = await create_post(client, "original")

    forbidden = await mallory.patch(f"{API}/posts/{post['id']}", json={"content": "hacked"})
    allowed = await client.patch(f"{API}/posts/{post['id']}", json={"content": "edited"})

    assert forbidden.status_code == 403
    assert allowed.status_code == 200 and allowed.json()["content"] == "edited"


async def test_only_author_can_delete(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    mallory = await make_client()
    await signup(client, "alice")
    await signup(mallory, "mallory")
    post = await create_post(client)

    assert (await mallory.delete(f"{API}/posts/{post['id']}")).status_code == 403
    assert (await client.delete(f"{API}/posts/{post['id']}")).status_code == 204
    assert (await client.get(f"{API}/posts/{post['id']}")).status_code == 404


async def test_feed_shows_followed_users_and_own_posts_only(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    bob, carol = await make_client(), await make_client()
    await signup(client, "alice")
    await signup(bob, "bob")
    await signup(carol, "carol")
    await create_post(client, "from alice")
    await create_post(bob, "from bob")
    await create_post(carol, "from carol")

    before = (await client.get(f"{API}/posts/feed")).json()["items"]
    await client.post(f"{API}/users/bob/follow")
    after = (await client.get(f"{API}/posts/feed")).json()["items"]

    assert [p["content"] for p in before] == ["from alice"]
    assert [p["content"] for p in after] == ["from bob", "from alice"]  # newest first, no carol


async def test_feed_requires_login(client: AsyncClient) -> None:
    assert (await client.get(f"{API}/posts/feed")).status_code == 401


async def test_cursor_pagination_has_no_gaps_or_duplicates(client: AsyncClient) -> None:
    await signup(client, "alice")
    for number in range(7):
        await create_post(client, f"post {number}")

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params = {"limit": 3, **({"cursor": cursor} if cursor else {})}
        page = (await client.get(f"{API}/posts/explore", params=params)).json()
        seen.extend(p["content"] for p in page["items"])
        pages += 1
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert pages == 3
    assert seen == [f"post {n}" for n in range(6, -1, -1)]


async def test_invalid_cursor_and_limit(client: AsyncClient) -> None:
    bad_cursor = await client.get(f"{API}/posts/explore", params={"cursor": "garbage"})
    big_limit = await client.get(f"{API}/posts/explore", params={"limit": 500})

    assert bad_cursor.status_code == 400 and bad_cursor.json()["error"]["code"] == "INVALID_CURSOR"
    assert big_limit.status_code == 422


async def test_explore_and_user_posts_filter_by_image(client: AsyncClient) -> None:
    await signup(client, "alice")
    upload = await client.post(f"{API}/media/images", files={"file": ("a.png", make_png(), "image/png")})
    await create_post(client, "text only")
    await create_post(client, "with image", media_id=upload.json()["id"])

    with_image = (await client.get(f"{API}/posts/explore", params={"has_image": "true"})).json()
    without = (await client.get(f"{API}/users/alice/posts", params={"has_image": "false"})).json()

    assert [p["content"] for p in with_image["items"]] == ["with image"]
    assert [p["content"] for p in without["items"]] == ["text only"]


async def test_deactivated_authors_posts_are_hidden(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    guest = await make_client()
    await signup(client, "alice")
    await create_post(client)
    assert len((await guest.get(f"{API}/posts/explore")).json()["items"]) == 1

    await client.post(f"{API}/auth/deactivate", json={"password": "correct-horse-battery"})

    assert (await guest.get(f"{API}/posts/explore")).json()["items"] == []
