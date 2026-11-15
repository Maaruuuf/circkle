"""Seed development data: 10 users (the first one is an admin) with 1 post each.

    python -m scripts.seed              # from the backend/ folder, venv active

Safe to run twice: users that already exist are skipped (and get no extra post).
Refuses to run in production. All seed users share one DEV-ONLY password.
"""

import asyncio
import os
import sys
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db import registry  # noqa: F401
from app.db.session import SessionFactory, engine
from app.modules.posts.models import Post
from app.modules.users.models import Follow, User, UserRole

SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "Circkle#Dev2026")

SEED_USERS: list[tuple[str, str, str, str]] = [
    # username, display name, bio, first post
    ("ada", "Ada Lovelace", "First programmer. Poetical science.", "Hello Circkle! Writing the first post of the first loop."),
    ("grace", "Grace Hopper", "Compilers & nanoseconds.", "It is often easier to ask for forgiveness than permission. Ship it, then fix it."),
    ("linus", "Linus T.", "Kernel tinkerer.", "Talk is cheap. Show me the code."),
    ("margaret", "Margaret Hamilton", "Software engineering since before it had a name.", "Testing the flight software one more time. Then once more."),
    ("alan", "Alan Turing", "Can machines think?", "Spent the morning on a puzzle. The puzzle won. Back at it tomorrow."),
    ("tim", "Tim Berners-Lee", "Links between things.", "A web is only as good as its links. Share something worth linking to."),
    ("radia", "Radia Perlman", "Packets and spanning trees.", "Good protocols fail gracefully. So do good people."),
    ("ken", "Ken Thompson", "Small tools that do one thing.", "Deleted 400 lines today. Best commit of the week."),
    ("barbara", "Barbara Liskov", "Abstractions that keep promises.", "If it looks like a duck but needs batteries, you probably have the wrong abstraction."),
    ("dennis", "Dennis Ritchie", "C and Unix.", "printf(\"hello, circkle\\n\"); some things never get old."),
]


async def seed() -> None:
    settings = get_settings()
    if settings.environment == "production":
        print("Refusing to seed a production database.")
        sys.exit(1)

    password_hash = hash_password(SEED_PASSWORD)  # one hash is fine: same dev password
    created_ids: list[uuid.UUID] = []
    all_ids: list[uuid.UUID] = []

    async with SessionFactory() as session:
        for index, (username, display_name, bio, post_text) in enumerate(SEED_USERS):
            email = f"{username}@example.com"
            existing = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing is not None:
                all_ids.append(existing.id)
                continue
            user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                display_name=display_name,
                bio=bio,
                password_hash=password_hash,
                is_email_verified=True,
                role=UserRole.ADMIN.value if index == 0 else UserRole.USER.value,
            )
            session.add(user)
            await session.flush()
            session.add(Post(id=uuid.uuid4(), author_id=user.id, content=post_text))
            created_ids.append(user.id)
            all_ids.append(user.id)

        # Everyone follows the next 3 users in the list, so feeds are not empty.
        if created_ids:
            for position, follower_id in enumerate(all_ids):
                for offset in (1, 2, 3):
                    followee_id = all_ids[(position + offset) % len(all_ids)]
                    already = (
                        await session.execute(
                            select(Follow).where(
                                Follow.follower_id == follower_id,
                                Follow.followee_id == followee_id,
                            )
                        )
                    ).scalar_one_or_none()
                    if already is None:
                        session.add(Follow(follower_id=follower_id, followee_id=followee_id))
        await session.commit()

    await engine.dispose()
    print(f"Seeded {len(created_ids)} new user(s) with 1 post each ({len(SEED_USERS)} total users).")
    print(f"Login with e.g. ada@example.com / {SEED_PASSWORD}  (ada is the admin)")


if __name__ == "__main__":
    asyncio.run(seed())
