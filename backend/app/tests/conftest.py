import os

# Must run before the app is imported. Tests never connect to a real database.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)