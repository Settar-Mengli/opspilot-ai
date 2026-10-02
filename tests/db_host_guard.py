"""Refuse non-local DATABASE_URL for hermetic pytest (D4)."""

from __future__ import annotations

from sqlalchemy.engine import make_url

# Hosts allowed for pytest / alembic round-trip (first-label or full local names).
_LOCAL_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",  # docker-compose / CI service hostname
    }
)


def is_local_database_host(url: str) -> bool:
    """True when the URL host is loopback or the local CI/docker Postgres service name."""
    host = (make_url(url).host or "").strip().lower()
    if not host:
        return False
    if host in _LOCAL_HOSTS:
        return True
    # database_host_label("127.0.0.1") → "127"; accept that label form too.
    first = host.split(".", 1)[0]
    return first == "127" and host.startswith("127.")


def assert_pytest_database_host_is_local(url: str) -> str:
    """Return the host label if local; raise RuntimeError otherwise (never print full URL)."""
    host = (make_url(url).host or "").strip()
    label = host.split(".", 1)[0] if host else "(none)"
    if not is_local_database_host(url):
        raise RuntimeError(
            f"Refusing pytest against non-local database host={label}. "
            "Set DATABASE_URL to local Docker Postgres (127.0.0.1 / localhost / postgres)."
        )
    return label
