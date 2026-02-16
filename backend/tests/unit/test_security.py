"""Unit tests for the core security module (password hashing, JWT tokens)."""

from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_returns_string(self) -> None:
        hashed = get_password_hash("strongpassword123")
        assert isinstance(hashed, str)
        assert hashed != "strongpassword123"

    def test_hash_is_deterministic_in_format_not_value(self) -> None:
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        # Two hashes of the same password should differ due to random salt
        assert h1 != h2

    def test_verify_correct_password(self) -> None:
        hashed = get_password_hash("correct_horse_battery_staple")
        is_valid, _ = verify_password("correct_horse_battery_staple", hashed)
        assert is_valid is True

    def test_verify_wrong_password(self) -> None:
        hashed = get_password_hash("correct_password")
        is_valid, _ = verify_password("wrong_password", hashed)
        assert is_valid is False

    def test_verify_empty_password(self) -> None:
        hashed = get_password_hash("notempty")
        is_valid, _ = verify_password("", hashed)
        assert is_valid is False

    def test_verify_returns_updated_hash_when_needed(self) -> None:
        """verify_password returns (bool, updated_hash|None).
        If the hash scheme is current, updated_hash should be None."""
        hashed = get_password_hash("testpassword")
        is_valid, updated_hash = verify_password("testpassword", hashed)
        assert is_valid is True
        # For a freshly hashed password, no update should be needed
        assert updated_hash is None

    def test_hash_different_passwords_different_output(self) -> None:
        h1 = get_password_hash("password_one")
        h2 = get_password_hash("password_two")
        assert h1 != h2


class TestAccessToken:
    def test_create_token_returns_string(self) -> None:
        token = create_access_token(subject="user-123", expires_delta=timedelta(hours=1))
        assert isinstance(token, str)

    def test_token_contains_subject(self) -> None:
        token = create_access_token(subject="user-abc", expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-abc"

    def test_token_contains_expiration(self) -> None:
        token = create_access_token(subject="user-1", expires_delta=timedelta(minutes=30))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_token_invalid_signature_raises(self) -> None:
        token = create_access_token(subject="user-1", expires_delta=timedelta(hours=1))
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])

    def test_expired_token_raises(self) -> None:
        token = create_access_token(subject="user-1", expires_delta=timedelta(seconds=-1))
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    def test_subject_coerced_to_string(self) -> None:
        """create_access_token calls str(subject) on the input."""
        import uuid

        uid = uuid.uuid4()
        token = create_access_token(subject=uid, expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == str(uid)
