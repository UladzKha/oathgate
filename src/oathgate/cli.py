"""oathgate — freeze the measurement ruler before you run the eval."""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

from oathgate.spec import compute_ruler

def main() -> int:
    parser = argparse.ArgumentParser(prog="oathgate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze = subparsers.add_parser("freeze", help="Compute the ruler hash")
    freeze.add_argument("--spec", default="oathgate.toml", help="Path to the spec file")

    predict = subparsers.add_parser("predict", help="Record a prediction before the run")
    predict.add_argument("--spec", default="oathgate.toml", help="Path to the spec file")
    predict.add_argument("--metric", required=True, help="Metric name from the spec")
    predict.add_argument("--note", help="Free-form note")
    predict.add_argument("--force", action="store_true", help="Overwrite an existing lock")

    group = predict.add_mutually_exclusive_group(required=True)
    group.add_argument("--at-least", type=float, metavar="VALUE")
    group.add_argument("--at-most", type=float, metavar="VALUE")

    args = parser.parse_args()

    if args.command == "freeze":
        spec_path = Path(args.spec)
        digest, _, _ = compute_ruler(spec_path)
        print(digest)

        return 0

    elif args.command == "predict":
        spec_path = Path(args.spec)
        digest, spec, _ = compute_ruler(spec_path)

        if args.metric not in spec["metrics"]:
            known = ", ".join(sorted(spec["metrics"]))
            print(f"unknown metric {args.metric!r}; spec defines: {known}", file=sys.stderr)
            return 2

        if args.at_least is not None:
            operator = ">="
            value = args.at_least
        else:
            operator = "<="
            value = args.at_most

        print(digest)
        print(f"{args.metric} {operator} {value}")

        return 0


        


