# Google OAuth weekly re-auth runbook

## Purpose

Keep the operator demo Gmail/Calendar refresh token fresh under Google OAuth **Testing** mode (D-016). Tokens are commonly cited as expiring ~**7 days** after issue — **VERIFY AT DECISION TIME**.

## Rules

- Refresh token is stored **encrypted in Neon** (or local Postgres during hermetic/dev).
- Encryption key lives in env / GHA secrets — **never** commit the key or plaintext token.
- **Never log or print** the token (raw or decrypted).
- Visitors never connect Gmail (`OPSPILOT_DEMO_MODE=1` blocks OAuth).

## Weekly operator procedure

1. Ensure API listens on `127.0.0.1:8000` and FE on `http://127.0.0.1:5173` (not `localhost` — A1 cookie).
2. Open Connections → **Connect Google** (or reconnect) as the Testing demo account.
3. App exchanges auth code + PKCE, Fernet-encrypts the refresh token (`TOKEN_ENCRYPTION_KEY`), writes `oauth_credentials.refresh_token_enc` (`bytea`), and sets `opspilot_operator` session cookie.
4. Click **Sync now** in the UI (do not paste cookies into curl).
5. Confirm WeekPanel and triage show synced fictional data.
6. If morning job (B6) fails auth: expect Telegram “re-auth needed”; skip sync until this procedure succeeds.

## Encryption scheme

- Algorithm: **Fernet** (`cryptography.fernet`) — AES-128-CBC + HMAC, url-safe base64 key.
- Env: `TOKEN_ENCRYPTION_KEY` = `Fernet.generate_key()` output (keep secret).
- Key rotation:
  1. Generate new key.
  2. Decrypt existing row(s) with old key; re-encrypt with new key; update DB.
  3. Update `.env` / GHA secret to the new key; retire old key.
  4. Never commit either key.

## Fail-closed morning behavior (B6)

On auth/decrypt failure: do **not** sync mail; brief from existing Neon data; send Telegram alert “re-auth needed”.
