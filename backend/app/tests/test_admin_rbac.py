from httpx import AsyncClient

from app.db.session import SessionFactory
from app.modules.users.models import UserRole
from app.tests.helpers import API, PASSWORD, create_post, email_for, signup


async def make_admin(client: AsyncClient, username: str = "boss") -> dict:  # type: ignore[type-arg]
    from sqlalchemy import update

    from app.modules.users.models import User

    user = await signup(client, username)
    async with SessionFactory() as session:
        await session.execute(
            update(User).where(User.username == username).values(role=UserRole.ADMIN.value)
        )
        await session.commit()
    return user


async def test_admin_routes_reject_guests_and_normal_users(client: AsyncClient) -> None:
    guest = await client.get(f"{API}/admin/users")
    await signup(client, "alice")
    normal = await client.get(f"{API}/admin/users")
    stats = await client.get(f"{API}/admin/stats")

    assert guest.status_code == 401
    assert normal.status_code == 403 and normal.json()["error"]["code"] == "FORBIDDEN"
    assert stats.status_code == 403


async def test_admin_lists_users_and_stats(client: AsyncClient) -> None:
    await make_admin(client)

    users = await client.get(f"{API}/admin/users")
    stats = await client.get(f"{API}/admin/stats")

    assert users.status_code == 200 and users.json()["items"][0]["username"] == "boss"
    assert stats.json()["users"] == 1


async def test_admin_can_ban_user_which_logs_them_out(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    victim = await make_client()
    victim_data = await signup(victim, "victim")
    await make_admin(client)

    banned = await client.patch(f"{API}/admin/users/{victim_data['id']}", json={"is_active": False})

    assert banned.status_code == 200 and banned.json()["is_active"] is False
    assert (await victim.get(f"{API}/users/me")).status_code == 401
    login = await victim.post(f"{API}/auth/login", json={"email": email_for("victim"), "password": PASSWORD})
    assert login.status_code == 403 and login.json()["error"]["code"] == "ACCOUNT_DISABLED"


async def test_admin_cannot_modify_self_and_input_is_strict(client: AsyncClient) -> None:
    admin = await make_admin(client)

    own = await client.patch(f"{API}/admin/users/{admin['id']}", json={"role": "user"})
    assert own.status_code == 403 and own.json()["error"]["code"] == "SELF_MODIFY"


async def test_admin_can_delete_any_post_but_users_cannot_escalate(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    mallory = await make_client()
    me = await signup(mallory, "mallory")
    post = await create_post(mallory)
    await make_admin(client)

    escalate = await mallory.patch(f"{API}/admin/users/{me['id']}", json={"role": "admin"})
    removed = await client.delete(f"{API}/admin/posts/{post['id']}")

    assert escalate.status_code == 403
    assert removed.status_code == 204
    assert (await client.get(f"{API}/posts/{post['id']}")).status_code == 404


async def test_admin_can_remove_post_through_normal_endpoint(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    author = await make_client()
    await signup(author, "writer")
    post = await create_post(author)
    await make_admin(client)

    assert (await client.delete(f"{API}/posts/{post['id']}")).status_code == 204
    # ...but admins still cannot edit other people's words.
    other = await create_post(author, "mine")
    assert (await client.patch(f"{API}/posts/{other['id']}", json={"content": "x"})).status_code == 403
