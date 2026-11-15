from httpx import AsyncClient

from app.tests.helpers import API, create_post, make_png, signup


async def test_update_profile(client: AsyncClient) -> None:
    await signup(client, "alice")

    response = await client.patch(
        f"{API}/users/me", json={"display_name": "  Alice A. ", "bio": "hello there"}
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Alice A."
    assert response.json()["bio"] == "hello there"


async def test_update_profile_rejects_forbidden_fields(client: AsyncClient) -> None:
    await signup(client, "alice")

    for payload in ({"role": "admin"}, {"username": "bob"}, {"email": "x@example.com"}, {"display_name": ""}):
        response = await client.patch(f"{API}/users/me", json=payload)
        assert response.status_code == 422, payload


async def test_update_profile_requires_login(client: AsyncClient) -> None:
    assert (await client.patch(f"{API}/users/me", json={"bio": "x"})).status_code == 401


async def test_public_profile_counts_and_flags(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    bob = await make_client()
    await signup(client, "alice")
    await signup(bob, "bob")
    await create_post(client, "first")
    await bob.post(f"{API}/users/alice/follow")

    as_bob = (await bob.get(f"{API}/users/alice")).json()
    as_alice = (await client.get(f"{API}/users/alice")).json()
    as_guest = (await (await make_client()).get(f"{API}/users/alice")).json()

    assert as_bob["followers_count"] == 1 and as_bob["posts_count"] == 1
    assert as_bob["is_following"] is True and as_bob["is_me"] is False
    assert as_alice["is_me"] is True and as_alice["is_following"] is False
    assert as_guest["is_following"] is False
    assert "email" not in as_guest  # public profile never exposes the email


async def test_unknown_profile_is_404(client: AsyncClient) -> None:
    response = await client.get(f"{API}/users/nobody")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


async def test_follow_unfollow_is_idempotent_and_updates_counts(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    bob = await make_client()
    await signup(client, "alice")
    await signup(bob, "bob")

    assert (await bob.post(f"{API}/users/alice/follow")).status_code == 204
    assert (await bob.post(f"{API}/users/alice/follow")).status_code == 204
    assert (await client.get(f"{API}/users/alice")).json()["followers_count"] == 1
    followers = (await client.get(f"{API}/users/alice/followers")).json()
    following = (await bob.get(f"{API}/users/bob/following")).json()
    assert [u["username"] for u in followers["items"]] == ["bob"]
    assert [u["username"] for u in following["items"]] == ["alice"]

    assert (await bob.delete(f"{API}/users/alice/follow")).status_code == 204
    assert (await bob.delete(f"{API}/users/alice/follow")).status_code == 204
    assert (await client.get(f"{API}/users/alice")).json()["followers_count"] == 0


async def test_cannot_follow_yourself(client: AsyncClient) -> None:
    await signup(client, "alice")

    response = await client.post(f"{API}/users/alice/follow")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CANNOT_FOLLOW_SELF"


async def test_follow_requires_login_and_existing_user(client: AsyncClient) -> None:
    assert (await client.post(f"{API}/users/alice/follow")).status_code == 401
    await signup(client, "alice")
    assert (await client.post(f"{API}/users/ghost/follow")).status_code == 404


async def test_search_users_by_prefix_and_escapes_wildcards(client: AsyncClient) -> None:
    await signup(client, "alice")

    found = await client.get(f"{API}/users/search", params={"q": "ali"})
    wildcard = await client.get(f"{API}/users/search", params={"q": "%%"})
    too_short = await client.get(f"{API}/users/search", params={"q": "a"})

    assert [u["username"] for u in found.json()] == ["alice"]
    assert wildcard.json() == []  # % is literal, not "match everything"
    assert too_short.status_code == 422


async def test_avatar_upload_sets_avatar_url(client: AsyncClient) -> None:
    await signup(client, "alice")

    response = await client.post(
        f"{API}/users/me/avatar", files={"file": ("me.png", make_png(300, 200), "image/png")}
    )

    assert response.status_code == 200
    assert response.json()["avatar_url"].startswith("/media/")
    served = await client.get(response.json()["avatar_url"])
    assert served.status_code == 200 and served.headers["content-type"] == "image/webp"


async def test_profile_cache_is_invalidated_on_change(client: AsyncClient) -> None:
    await signup(client, "alice")
    assert (await client.get(f"{API}/users/alice")).json()["bio"] is None  # warms the cache

    await client.patch(f"{API}/users/me", json={"bio": "fresh bio"})

    assert (await client.get(f"{API}/users/alice")).json()["bio"] == "fresh bio"
