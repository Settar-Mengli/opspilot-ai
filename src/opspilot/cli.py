import argparse

from opspilot.pipeline.run_daily_ops import run_daily_ops


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpsPilot AI local operations command center")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run daily operations triage pipeline")
    run_parser.add_argument("--input", required=True, help="Path to input JSON fixture")
    run_parser.add_argument("--output", required=True, help="Path to output directory")
    run_parser.add_argument("--date", required=True, help="Run date in YYYY-MM-DD format")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        outputs = run_daily_ops(args.input, args.output, args.date)
        print("OpsPilot AI run completed.")
        for name, path in outputs.items():
            print(f"{name}: {path}")


if __name__ == "__main__":
    main()
