"""Fernet encryption for OAuth refresh tokens at rest (D-016 / D-027)."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionUnavailableError(RuntimeError):
    """Raised when TOKEN_ENCRYPTION_KEY is missing or invalid."""


def _fernet() -> Fernet:
    raw = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if not raw:
        raise EncryptionUnavailableError("TOKEN_ENCRYPTION_KEY is not set")
    try:
        return Fernet(raw.encode("ascii") if isinstance(raw, str) else raw)
    except (ValueError, TypeError) as exc:
        raise EncryptionUnavailableError("TOKEN_ENCRYPTION_KEY is invalid") from exc


def encrypt_token(plaintext: str) -> bytes:
    """Encrypt a refresh token to bytea-safe ciphertext. Never log plaintext."""
    if not plaintext:
        raise ValueError("plaintext token must be non-empty")
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_token(ciphertext: bytes) -> str:
    """Decrypt Fernet ciphertext to the refresh token string."""
    if not ciphertext:
        raise ValueError("ciphertext must be non-empty")
    try:
        return _fernet().decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionUnavailableError("token decrypt failed") from exc
