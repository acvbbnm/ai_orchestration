"""Standalone CLI and opt-in argparse registration; director.py is unchanged."""
import argparse
import json
import sys

from core.analysis_mode import AnalysisError, run_analysis


def handle_analyze(args):
    try:
        findings = run_analysis(args.binary_path, args.goal, timeout=args.timeout)
    except AnalysisError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": str(exc)}},
                         ensure_ascii=False), file=sys.stderr)
        return 2 if exc.code == "INVALID_INPUT" else 1
    print(json.dumps({"findings": [item.dict() for item in findings]}, ensure_ascii=False))
    return 0


def register_analyze_subcommand(subparsers):
    """Add analyze to an existing argparse subparsers action; dispatch via func."""
    parser = subparsers.add_parser("analyze", help="Statically analyze a binary using IDA MCP")
    parser.add_argument("binary_path")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--timeout", type=float, default=300)
    parser.set_defaults(func=handle_analyze)
    return parser


def main(argv=None):
    parser = argparse.ArgumentParser(description="IDA MCP analysis")
    register_analyze_subcommand(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
