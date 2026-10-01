"""Hermetic Fernet crypto tests (no network)."""

from __future__ import annotations

import logging

import pytest
from cryptography.fernet import Fernet

from opspilot.persistence.crypto import (
    EncryptionUnavailableError,
    decrypt_token,
    encrypt_token,
)


def test_encrypt_decrypt_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)
    plain = "refresh-token-fixture-not-real"
    cipher = encrypt_token(plain)
    assert isinstance(cipher, bytes)
    assert plain.encode() not in cipher
    assert decrypt_token(cipher) == plain


def test_missing_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    with pytest.raises(EncryptionUnavailableError):
        encrypt_token("x")


def test_wrong_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    cipher = encrypt_token("secret-token")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(EncryptionUnavailableError):
        decrypt_token(cipher)


def test_encrypt_does_not_log_plaintext(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    secret = "super-secret-refresh-xyz"
    with caplog.at_level(logging.DEBUG):
        encrypt_token(secret)
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert secret not in joined
