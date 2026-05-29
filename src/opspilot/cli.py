import argparse
import logging

from opspilot.models.schemas import OpsPilotError
from opspilot.pipeline.run_daily_ops import run_daily_ops
from opspilot.utils.logging_utils import configure_logging, log_event


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpsPilot AI local operations command center")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run daily operations triage pipeline")
    run_parser.add_argument("--input", required=True, help="Path to input JSON fixture")
    run_parser.add_argument("--output", required=True, help="Path to output directory")
    run_parser.add_argument("--date", required=True, help="Run date in YYYY-MM-DD format")

    return parser


def main() -> None:
    configure_logging()
    logger = logging.getLogger("opspilot.cli")

    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "run":
            outputs = run_daily_ops(args.input, args.output, args.date)
            print("OpsPilot AI run completed.")
            for name, path in outputs.items():
                print(f"{name}: {path}")
    except OpsPilotError as exc:
        log_event(logger, "cli_failed", error_type=type(exc).__name__, message=str(exc))
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
