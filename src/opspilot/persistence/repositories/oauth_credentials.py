"""OAuth credential repository (Fernet ciphertext in bytea)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.crypto import decrypt_token, encrypt_token
from opspilot.persistence.models import OAuthCredentialRow


def upsert_encrypted_refresh(
    session: Session,
    *,
    provider: str,
    account_email: str,
    scopes: str,
    refresh_token_plaintext: str,
) -> int:
    """Store Fernet-encrypted refresh token. Never logs plaintext."""
    ciphertext = encrypt_token(refresh_token_plaintext)
    now = datetime.now(UTC)
    stmt = pg_insert(OAuthCredentialRow).values(
        provider=provider,
        account_email=account_email,
        scopes=scopes,
        refresh_token_enc=ciphertext,
        created_at=now,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_oauth_credentials_provider_email",
        set_={
            "scopes": stmt.excluded.scopes,
            "refresh_token_enc": stmt.excluded.refresh_token_enc,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.scalars(
        select(OAuthCredentialRow).where(
            OAuthCredentialRow.provider == provider,
            OAuthCredentialRow.account_email == account_email,
        )
    ).one()
    return int(row.id)


def get_decrypted_refresh(
    session: Session,
    *,
    provider: str,
    account_email: str | None = None,
) -> tuple[str, str] | None:
    """Return (account_email, refresh_token) or None. Never logs token."""
    stmt = select(OAuthCredentialRow).where(OAuthCredentialRow.provider == provider)
    if account_email is not None:
        stmt = stmt.where(OAuthCredentialRow.account_email == account_email)
    row = session.scalars(stmt.order_by(OAuthCredentialRow.updated_at.desc())).first()
    if row is None:
        return None
    return row.account_email, decrypt_token(bytes(row.refresh_token_enc))


def is_connected(session: Session, *, provider: str = "google") -> bool:
    """True when a credential row exists and grants required Gmail+Calendar scopes."""
    from opspilot.integrations.google_oauth import has_required_scopes

    stmt = select(OAuthCredentialRow).where(OAuthCredentialRow.provider == provider)
    row = session.scalars(stmt.order_by(OAuthCredentialRow.updated_at.desc())).first()
    if row is None:
        return False
    return has_required_scopes(row.scopes)
