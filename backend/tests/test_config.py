import pytest
from pydantic import ValidationError

from app.config import Settings

REQUIRED_SETTINGS = ("DATABASE_URL", "JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES")


def test_every_setting_is_required(monkeypatch):
    for name in REQUIRED_SETTINGS:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    message = str(error.value)
    for field in ("database_url", "jwt_secret", "jwt_algorithm", "jwt_expire_minutes"):
        assert field in message


def test_missing_one_setting_is_enough_to_stop_the_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "any-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.delenv("JWT_EXPIRE_MINUTES", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "jwt_expire_minutes" in str(error.value)


def test_env_values_are_read_into_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "any-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@localhost:5432/db"
    assert settings.jwt_secret == "any-secret"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 60


def test_numeric_setting_is_converted_from_text(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "any-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")

    settings = Settings(_env_file=None)

    assert settings.jwt_expire_minutes == 60
    assert isinstance(settings.jwt_expire_minutes, int)
