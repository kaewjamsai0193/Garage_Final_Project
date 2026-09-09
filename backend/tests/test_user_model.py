import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def test_can_insert_and_read_user(db_session):
    db_session.add(
        User(
            username="somchai",
            password_hash="x",
            full_name="สมชาย ใจดี",
            role="admin",
        )
    )
    db_session.flush()

    user = db_session.scalar(select(User).where(User.username == "somchai"))
    assert user.full_name == "สมชาย ใจดี"
    assert user.role == "admin"
    assert user.is_active is True
    assert user.created_at is not None


def test_username_must_be_unique(db_session):
    db_session.add(User(username="somchai", password_hash="x", full_name="ก", role="admin"))
    db_session.flush()

    db_session.add(User(username="somchai", password_hash="y", full_name="ข", role="employee"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_role_must_be_one_of_three(db_session):
    db_session.add(User(username="ubie", password_hash="x", full_name="ค", role="owner"))
    with pytest.raises(IntegrityError):
        db_session.flush()
