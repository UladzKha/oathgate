"""oathgate — freeze the measurement ruler before you run the eval."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Only these keys describe the *ruler*: how a result is measured.
# The system under test (prompt, model, agent, temperature) is deliberately
# excluded — you are allowed to change it, that is the whole point.
RULER_KEYS = ("metrics", "thresholds", "dataset", "references")

LOCK_NAME = "oath.lock.json"


def _canonical(spec: dict) -> str:
    ruler = {k: spec[k] for k in RULER_KEYS if k in spec}
    return json.dumps(ruler, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(spec: dict) -> str:
    return hashlib.sha256(_canonical(spec).encode("utf-8")).hexdigest()


def _load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"oathgate: spec not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"oathgate: cannot parse {path}: {exc}")


def cmd_freeze(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec = _load(spec_path)

    missing = [k for k in RULER_KEYS if k not in spec]
    if missing:
        sys.exit(f"oathgate: spec is missing required keys: {', '.join(missing)}")

    if not args.predict:
        sys.exit("oathgate: refusing to freeze without a prediction (--predict)")

    lock = {
        "version": 1,
        "spec": str(spec_path),
        "ruler_sha256": _digest(spec),
        "prediction": args.predict,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    lock_path = Path(args.lock)
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"frozen  {lock['ruler_sha256'][:12]}  -> {lock_path}")
    print(f"oath    {args.predict}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lock_path = Path(args.lock)
    if not lock_path.exists():
        sys.exit(f"oathgate: no lock file ({lock_path}). Run `oathgate freeze` first.")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    spec = _load(Path(args.spec or lock["spec"]))
    current = _digest(spec)

    if current != lock["ruler_sha256"]:
        print("BLOCKED: the measurement ruler changed after the oath was taken.")
        print(f"  frozen:  {lock['ruler_sha256'][:12]}  ({lock['frozen_at']})")
        print(f"  current: {current[:12]}")
        print("  Re-freeze deliberately, or restore the spec. Do not do it silently.")
        return 1

    print(f"ok      {current[:12]}  ruler unchanged")
    print(f"oath    {lock['prediction']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oathgate",
        description="Freeze the eval scoring spec and your prediction before the run.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("freeze", help="freeze the ruler and record a prediction")
    f.add_argument("spec", help="path to the eval spec (JSON)")
    f.add_argument("--predict", required=True, help="what you expect to happen")
    f.add_argument("--lock", default=LOCK_NAME, help=f"lock file (default: {LOCK_NAME})")
    f.set_defaults(func=cmd_freeze)

    c = sub.add_parser("check", help="verify the ruler is unchanged before a run")
    c.add_argument("spec", nargs="?", help="path to the eval spec (default: from lock)")
    c.add_argument("--lock", default=LOCK_NAME, help=f"lock file (default: {LOCK_NAME})")
    c.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
