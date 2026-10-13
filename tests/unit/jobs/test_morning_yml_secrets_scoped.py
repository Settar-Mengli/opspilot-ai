"""morning.yml: secrets only on the two steps that need them (not job-level / uses:)."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_morning_yml_secrets_not_in_job_env_or_uses_steps() -> None:
    doc = yaml.safe_load(Path(".github/workflows/morning.yml").read_text(encoding="utf-8"))
    job = doc["jobs"]["morning"]
    job_env = job.get("env") or {}
    for key, val in job_env.items():
        text = str(val)
        assert "secrets." not in text, f"job-level env {key} references secrets: {text}"

    for step in job["steps"]:
        if "uses" in step:
            for section in ("env", "with"):
                mapping = step.get(section) or {}
                for key, val in mapping.items():
                    text = str(val)
                    assert "secrets." not in text, (
                        f"uses step {step.get('name')!r} {section}.{key} references secrets: {text}"
                    )


def test_morning_yml_secret_steps_have_expected_keys() -> None:
    doc = yaml.safe_load(Path(".github/workflows/morning.yml").read_text(encoding="utf-8"))
    steps = {s.get("name"): s for s in doc["jobs"]["morning"]["steps"]}
    db_host = steps["Print database host label"]
    assert set(db_host["env"]) == {"DATABASE_URL"}
    assert "secrets.OPSPILOT_DATABASE_URL" in str(db_host["env"]["DATABASE_URL"])

    morning = steps["Run morning job"]
    expected = {
        "DATABASE_URL",
        "TOKEN_ENCRYPTION_KEY",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    }
    assert set(morning["env"]) == expected
    for key in expected:
        assert "secrets." in str(morning["env"][key])
