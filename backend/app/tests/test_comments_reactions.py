from httpx import AsyncClient

from app.tests.helpers import API, create_post, signup


async def test_comment_create_list_and_count(client: AsyncClient) -> None:
    await signup(client, "alice")
    post = await create_post(client)

    created = await client.post(f"{API}/posts/{post['id']}/comments", json={"content": " nice! "})
    listing = await client.get(f"{API}/posts/{post['id']}/comments")

    assert created.status_code == 201 and created.json()["content"] == "nice!"
    assert [c["author"]["username"] for c in listing.json()["items"]] == ["alice"]
    assert (await client.get(f"{API}/posts/{post['id']}")).json()["comment_count"] == 1


async def test_comment_validation_and_auth(client: AsyncClient) -> None:
    await signup(client, "alice")
    post = await create_post(client)
    url = f"{API}/posts/{post['id']}/comments"

    assert (await client.post(url, json={"content": "  "})).status_code == 422
    assert (await client.post(url, json={"content": "x" * 1001})).status_code == 422
    client.cookies.clear()
    assert (await client.post(url, json={"content": "hi"})).status_code == 401


async def test_comment_on_missing_post_is_404(client: AsyncClient) -> None:
    await signup(client, "alice")

    response = await client.post(
        f"{API}/posts/00000000-0000-4000-8000-000000000000/comments", json={"content": "hi"}
    )

    assert response.status_code == 404


async def test_comment_order_and_pagination(client: AsyncClient) -> None:
    await signup(client, "alice")
    post = await create_post(client)
    for number in range(5):
        await client.post(f"{API}/posts/{post['id']}/comments", json={"content": f"c{number}"})
    url = f"{API}/posts/{post['id']}/comments"

    first = (await client.get(url, params={"limit": 2})).json()
    second = (await client.get(url, params={"limit": 2, "cursor": first["next_cursor"]})).json()
    newest_first = (await client.get(url, params={"order": "desc", "limit": 2})).json()

    assert [c["content"] for c in first["items"]] == ["c0", "c1"]
    assert [c["content"] for c in second["items"]] == ["c2", "c3"]
    assert [c["content"] for c in newest_first["items"]] == ["c4", "c3"]


async def test_comment_delete_permissions(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    bob, carol = await make_client(), await make_client()
    await signup(client, "alice")  # owns the post
    await signup(bob, "bob")
    await signup(carol, "carol")
    post = await create_post(client)
    url = f"{API}/posts/{post['id']}/comments"
    by_bob = (await bob.post(url, json={"content": "bob says hi"})).json()
    by_bob_2 = (await bob.post(url, json={"content": "bob again"})).json()

    assert (await carol.delete(f"{API}/comments/{by_bob['id']}")).status_code == 403  # stranger
    assert (await bob.delete(f"{API}/comments/{by_bob['id']}")).status_code == 204  # author
    assert (await client.delete(f"{API}/comments/{by_bob_2['id']}")).status_code == 204  # post owner
    assert (await client.delete(f"{API}/comments/{by_bob_2['id']}")).status_code == 404


async def test_reaction_set_change_remove(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    bob = await make_client()
    await signup(client, "alice")
    await signup(bob, "bob")
    post = await create_post(client)
    url = f"{API}/posts/{post['id']}/reaction"

    liked = await client.put(url, json={"type": "like"})
    switched = await client.put(url, json={"type": "love"})
    other = await bob.put(url, json={"type": "love"})

    assert liked.json()["reaction_count"] == 1 and liked.json()["my_reaction"] == "like"
    assert switched.json()["reaction_count"] == 1  # still one reaction per user
    assert switched.json()["by_type"] == {"love": 1}
    assert other.json()["by_type"] == {"love": 2}

    removed = await client.delete(url)
    assert removed.json()["reaction_count"] == 1 and removed.json()["my_reaction"] is None
    assert (await client.get(f"{API}/posts/{post['id']}")).json()["my_reaction"] is None
    assert (await bob.get(f"{API}/posts/{post['id']}")).json()["my_reaction"] == "love"


async def test_reaction_validation_and_auth(client: AsyncClient) -> None:
    await signup(client, "alice")
    post = await create_post(client)
    url = f"{API}/posts/{post['id']}/reaction"

    assert (await client.put(url, json={"type": "angry"})).status_code == 422
    assert (await client.put(url, json={})).status_code == 422
    client.cookies.clear()
    assert (await client.put(url, json={"type": "like"})).status_code == 401
