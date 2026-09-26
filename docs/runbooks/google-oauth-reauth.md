# Google OAuth weekly re-auth runbook

## Purpose

Keep the operator demo Gmail/Calendar refresh token fresh under Google OAuth **Testing** mode (D-016). Tokens are commonly cited as expiring ~**7 days** after issue — **VERIFY AT DECISION TIME**.

## Rules

- Refresh token is stored **encrypted in Neon**.
- Encryption key lives in env / GHA secrets — **never** commit the key or plaintext token.
- **Never log or print** the token (raw or decrypted).
- Visitors never connect Gmail.

## Weekly operator procedure

1. Run the local app OAuth flow as the demo operator account.
2. App encrypts the new refresh token and writes ciphertext to Neon.
3. Confirm morning job can decrypt (next GHA run or local smoke).
4. If auth fails in the morning job: expect Telegram “re-auth needed”; skip sync until this procedure succeeds.

## Encryption scheme (document for implementers)

- Symmetric encryption of the refresh token at rest in Neon (algorithm and key length fixed in B4 implementation ADR/PR).
- Key rotation: generate new key → re-encrypt row under new key → update GHA/env secret → retire old key. Exact steps to be filled when B4 ships the encryptor; this runbook is the SoT location for that procedure.

## Fail-closed morning behavior (B6)

On auth/decrypt failure: do **not** sync mail; brief from existing Neon data; send Telegram alert “re-auth needed”.
