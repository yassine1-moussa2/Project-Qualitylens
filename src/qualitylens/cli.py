"""Command line entry point: ``qualitylens <command>``.

Commands available today:

    qualitylens sample-data [--out data]
    qualitylens profile data/current.csv --reference data/reference.csv --parse-dates order_date

``qualitylens run --config configs/checks.yaml`` arrives with steps 3 and 4.
"""

import argparse
import json
import sys
from pathlib import Path

from qualitylens.ingest import load_table
from qualitylens.profile import profile_dataframe
from qualitylens.sample_data import write_sample_data


def cmd_sample_data(args: argparse.Namespace) -> int:
    paths = write_sample_data(args.out, n_rows=args.rows)
    for name, path in paths.items():
        print(f"{name:>9}: {path}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    reference = None
    if args.reference:
        reference = profile_dataframe(load_table(args.reference, parse_dates=args.parse_dates))

    df = load_table(args.path, parse_dates=args.parse_dates)
    profile = profile_dataframe(df, reference=reference)
    output = json.dumps(profile.to_dict(), indent=2, default=str)

    if args.out:
        Path(args.out).write_text(output + "\n")
        print(f"Profile written to {args.out}")
    else:
        print(output)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    print("`run` is not implemented yet: it arrives with quality rules (step 3) and drift (step 4).")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qualitylens", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sample-data", help="write reference/current CSVs with injected faults")
    p.add_argument("--out", default="data", help="output directory (default: data)")
    p.add_argument("--rows", type=int, default=5_000, help="rows per dataset (default: 5000)")
    p.set_defaults(func=cmd_sample_data)

    p = sub.add_parser("profile", help="print per-column statistics for a CSV/Parquet file")
    p.add_argument("path")
    p.add_argument("--reference", help="reuse this file's histogram bins for comparability")
    p.add_argument("--out", help="write the JSON profile to this file instead of stdout")
    p.add_argument("--parse-dates", nargs="*", default=None, metavar="COL", help="CSV columns to read as dates")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("run", help="run quality and drift checks (not implemented yet)")
    p.add_argument("--config", default="configs/checks.yaml")
    p.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        # Input mistakes (bad path, unknown column): a clear line, not a traceback.
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
