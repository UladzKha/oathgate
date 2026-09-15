"""oathgate — freeze the measurement ruler before you run the eval."""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

from oathgate.spec import SpecError, compute_ruler
from oathgate.lock import LOCK_NAME, read_lock, verify, write_lock

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

    check = subparsers.add_parser("check", help="Verify the ruler has not moved")
    check.add_argument("--spec", default="oathgate.toml", help="Path to the spec file")
    check.add_argument("--lock", default=None, help="Path to the lock file")

    args = parser.parse_args()

    try:
    
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

            lock_path = spec_path.parent / LOCK_NAME
            if lock_path.exists() and not args.force:
                print(f"{lock_path} already exists; pass --force to replace it", file=sys.stderr)
                return 2

            
            history: list[dict] = []

            if args.force and lock_path.exists():
                previous = read_lock(lock_path)
                history = previous.pop("history", [])
                history.append(previous)
            
            write_lock(
                lock_path,
                digest=digest,
                spec_name=spec_path.name,
                metric=args.metric,
                operator=operator,
                value=value,
                note=args.note,
                history=history
            )

            print(digest)
            print(f"wrote {lock_path}: {args.metric} {operator} {value}")

            return 0

        elif args.command == "check":
            spec_path = Path(args.spec)
            lock_path = Path(args.lock) if args.lock else spec_path.parent / LOCK_NAME

            ok, expected, digest, files = verify(spec_path, lock_path)

            if ok:
                print(f"ok {digest}")
                return 0

            print("ruler moved")
            print(f"    expected {expected}")
            print(f"    actual   {digest}")
            print("hashed inputs:")
            for path in sorted(files):
                print(f"   {path}")

            return 1        
    except SpecError as e:
        print(e, file=sys.stderr)
        return 2
   
    return 2