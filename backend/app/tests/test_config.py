from app.core.config import Settings


def test_settings_load_database_url_from_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.environment == "development"