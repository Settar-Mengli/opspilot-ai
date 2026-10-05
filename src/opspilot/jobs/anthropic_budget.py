"""CLI for Anthropic prepaid ledger (show / set).

Usage::

    uv run python -m opspilot.jobs.anthropic_budget show
    uv run python -m opspilot.jobs.anthropic_budget set --tokens 100000 --usd 0.30
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation

from sqlalchemy.engine import make_url

from opspilot.config.env_load import load_repo_dotenv
from opspilot.persistence.db import (
    create_engine,
    create_session_factory,
    database_host_label,
    get_database_url,
)
from opspilot.persistence.repositories.anthropic_budget import (
    anthropic_call_counts,
    get_budget,
    set_budget,
)

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})


def _is_local_database_url(url: str) -> bool:
    host = (make_url(url).host or "").strip().lower()
    if not host:
        return False
    if host in _LOCAL_HOSTS:
        return True
    first = host.split(".", 1)[0]
    return first == "127" and host.startswith("127.")


def _print_host() -> str:
    label = database_host_label()
    print(f"database host={label}")
    return label


def cmd_show(_: argparse.Namespace) -> int:
    _print_host()
    engine = create_engine()
    try:
        factory = create_session_factory(engine)
        with factory() as session:
            row = get_budget(session)
            if row is None:
                print("remaining_tokens=(none)")
                print("remaining_usd=(none)")
            else:
                print(f"remaining_tokens={row.remaining_tokens}")
                print(f"remaining_usd={row.remaining_usd}")
            counts = anthropic_call_counts(session)
            print(f"anthropic_rows_total={counts['anthropic_rows_total']}")
            by_status = ",".join(f"{k}:{v}" for k, v in sorted(counts["by_status"].items()))
            by_task = ",".join(f"{k}:{v}" for k, v in sorted(counts["by_task"].items()))
            print(f"by_status={by_status or '(none)'}")
            print(f"by_task={by_task or '(none)'}")
            max_id = counts["max_id"]
            print(f"max_id={max_id if max_id is not None else 'none'}")
    finally:
        engine.dispose()
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    label = _print_host()
    if not _is_local_database_url(get_database_url()):
        confirm = (args.confirm_host or "").strip()
        if confirm != label:
            print(
                f"error: non-local host requires --confirm-host {label}",
                file=sys.stderr,
            )
            return 2
    try:
        tokens = int(args.tokens)
        usd = Decimal(str(args.usd))
    except (ValueError, InvalidOperation):
        print("error: invalid tokens/usd", file=sys.stderr)
        return 2
    if tokens < 0 or usd < 0:
        print("error: tokens/usd must be non-negative", file=sys.stderr)
        return 2
    engine = create_engine()
    try:
        factory = create_session_factory(engine)
        with factory() as session:
            row = set_budget(session, tokens=tokens, usd=usd)
            session.commit()
            print(f"remaining_tokens={row.remaining_tokens}")
            print(f"remaining_usd={row.remaining_usd}")
    finally:
        engine.dispose()
    return 0


def main(argv: list[str] | None = None) -> int:
    load_repo_dotenv()
    parser = argparse.ArgumentParser(prog="opspilot.jobs.anthropic_budget")
    sub = parser.add_subparsers(dest="command", required=True)

    p_show = sub.add_parser("show", help="Print ledger + anthropic llm_calls counts")
    p_show.set_defaults(func=cmd_show)

    p_set = sub.add_parser("set", help="Set remaining tokens and USD")
    p_set.add_argument("--tokens", required=True, type=int)
    p_set.add_argument("--usd", required=True)
    p_set.add_argument("--confirm-host", default=None)
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
