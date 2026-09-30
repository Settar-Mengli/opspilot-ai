"""CLI: hermetic (default) and owner-gated live evals (D-028)."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from opspilot.evals.dataset import REDTEAM_V1, TRIAGE_V1, load_redteam_cases, load_triage_cases
from opspilot.evals.live import LiveEvalError, run_live
from opspilot.evals.report import write_eval_json
from opspilot.evals.rules_baseline import MACRO_F1_FLOOR, format_hit_report, run_rules_vs_labels


def _default_hermetic_out() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("docs/evals/results") / f"hermetic-{stamp}.json"


def _default_live_out(provider: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("docs/evals/results") / f"live-{provider}-{stamp}.json"


def run_hermetic(*, out: Path | None = None) -> dict[str, Any]:
    report = run_rules_vs_labels()
    payload = {
        "mode": "hermetic",
        "created_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "triage_dataset": str(TRIAGE_V1.as_posix()),
        "redteam_dataset": str(REDTEAM_V1.as_posix()),
        "n_triage": len(load_triage_cases()),
        "n_redteam": len(load_redteam_cases()),
        "macro_f1": report["macro_f1"],
        "macro_f1_floor": MACRO_F1_FLOOR,
        "gate_passed": report["macro_f1"] >= MACRO_F1_FLOOR,
        "fields": report["fields"],
        # confusion matrices only — no prompt/body text
        "confusion": report.get("confusion", {}),
    }
    target = out or _default_hermetic_out()
    write_eval_json(target, payload)
    payload["_out"] = str(target)
    return payload


def run_live_cli(
    *,
    provider: str,
    out: Path | None = None,
    resume_from: Path | None = None,
) -> dict[str, Any]:
    """Owner-gated live path: opens a DB session and runs single-provider eval."""
    import json

    from opspilot.evals.live import failed_case_ids, merge_live_results
    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

    case_ids: set[str] | None = None
    base: dict[str, Any] | None = None
    if resume_from is not None:
        base = json.loads(resume_from.read_text(encoding="utf-8"))
        case_ids = failed_case_ids(base)
        if not case_ids:
            raise LiveEvalError(f"no failed cases to resume in {resume_from}")
        print(f"resume_from={resume_from} failed_cases={len(case_ids)}")

    engine = create_engine(get_database_url())
    factory = create_session_factory(engine)
    session = factory()
    try:
        payload = run_live(provider_name=provider, session=session, case_ids=case_ids)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    if base is not None:
        payload = merge_live_results(base, payload)

    target = out or _default_live_out(provider.strip().lower())
    write_eval_json(target, payload)
    payload["_out"] = str(target)
    return payload


def run_recompute_cli(*, source: Path, out: Path | None = None) -> dict[str, Any]:
    """Recompute live metrics from stored rows (no provider calls)."""
    import json

    from opspilot.evals.live import recompute_live_metrics

    base = json.loads(source.read_text(encoding="utf-8"))
    payload = recompute_live_metrics(base)
    target = out or source
    write_eval_json(target, payload)
    payload["_out"] = str(target)
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m opspilot.jobs.run_evals")
    p.add_argument(
        "--live",
        action="store_true",
        help="Owner-gated live leaderboard path (requires --provider). Refuses without flag.",
    )
    p.add_argument(
        "--provider",
        default=None,
        help="Single provider name for --live (Anthropic refused).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON output path (default under docs/evals/results/).",
    )
    p.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Re-run non-accepted and accepted-without-pred case ids from a prior live JSON and merge.",
    )
    p.add_argument(
        "--recompute-metrics",
        type=Path,
        default=None,
        help="Recompute validity/F1/ASR/repair from stored rows in JSON (no live provider calls).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.recompute_metrics is not None:
        if args.live or args.provider:
            print("ERROR: --recompute-metrics cannot be combined with --live/--provider", file=sys.stderr)
            return 2
        payload = run_recompute_cli(source=args.recompute_metrics, out=args.out)
        print(
            f"recomputed validity={payload['validity_pct']:.3f} "
            f"f1_accepted={payload.get('triage_macro_f1')} n={payload.get('triage_macro_f1_n')} "
            f"asr={_format_asr(payload['asr'])} wrote {payload['_out']}"
        )
        return 0
    if args.live:
        # Same dotenv load as pipeline / llm_discover CLIs (repo-root .env).
        load_dotenv()
        if not args.provider:
            print("ERROR: --live requires --provider <name>", file=sys.stderr)
            return 2
        try:
            payload = run_live_cli(provider=args.provider, out=args.out, resume_from=args.resume_from)
        except LiveEvalError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(
            f"provider={payload['provider']} validity={payload['validity_pct']:.3f} "
            f"n={payload.get('validity_n')} "
            f"f1_accepted={payload.get('triage_macro_f1')} n={payload.get('triage_macro_f1_n')} "
            f"asr={_format_asr(payload['asr'])} "
            f"blocked={payload.get('asr', {}).get('blocked_by_defenses')} "
            f"repair_pct={payload.get('repair_pct')} "
            f"rate_limit_events={payload.get('rate_limit_events')} wrote {payload['_out']}"
        )
        return 0
    if args.provider:
        print("ERROR: --provider requires --live", file=sys.stderr)
        return 2
    payload = run_hermetic(out=args.out)
    print(format_hit_report({"n": payload["n_triage"], "macro_f1": payload["macro_f1"], "fields": payload["fields"]}))
    print(f"wrote {payload['_out']} gate_passed={payload['gate_passed']}")
    return 0 if payload["gate_passed"] else 1


def _format_asr(asr: dict[str, Any]) -> str:
    rate = asr.get("rate")
    if rate is None:
        return "N/A"
    accepted = asr.get("accepted")
    successes = asr.get("successes")
    return f"{rate:.3f} ({successes}/{accepted})"


if __name__ == "__main__":
    raise SystemExit(main())
