import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_required_settings_stops_the_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    message = str(error.value)
    assert "database_url" in message
    assert "jwt_secret" in message


def test_non_secret_settings_keep_their_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "any-secret")

    settings = Settings(_env_file=None)

    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 480


def test_env_values_are_read_into_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "any-secret")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@localhost:5432/db"
    assert settings.jwt_secret == "any-secret"
    assert settings.jwt_expire_minutes == 60
