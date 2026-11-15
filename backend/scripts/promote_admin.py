"""Make an existing user an admin:   python -m scripts.promote_admin someone@example.com"""

import asyncio
import sys

from sqlalchemy import select

from app.db import registry  # noqa: F401
from app.db.session import SessionFactory, engine
from app.modules.users.models import User, UserRole


async def promote(email: str) -> int:
    async with SessionFactory() as session:
        user = (
            await session.execute(select(User).where(User.email == email.strip().lower()))
        ).scalar_one_or_none()
        if user is None:
            print(f"No user with email {email!r}")
            return 1
        user.role = UserRole.ADMIN.value
        await session.commit()
    await engine.dispose()
    print(f"{email} is now an admin")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m scripts.promote_admin <email>")
        sys.exit(2)
    sys.exit(asyncio.run(promote(sys.argv[1])))
