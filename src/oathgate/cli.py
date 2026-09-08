"""oathgate — freeze the measurement ruler before you run the eval."""

from __future__ import annotations
import argparse
from pathlib import Path

from oathgate.spec import canonical_payload, collect_files, load_spec, ruler_hash

def main() -> None:
    parser = argparse.ArgumentParser(prog="oathgate")
    subparser = parser.add_subparsers(dest="command", required=True)

    freeze = subparser.add_parser("freeze", help="Compute the ruler hash")
    freeze.add_argument("--spec", default="oathgate.toml", help="Path to the spec file")

    args = parser.parse_args()

    if args.command == "freeze":
        spec_path = Path(args.spec)
        base_dir = spec_path.parent

        spec = load_spec(spec_path)
        files = collect_files(spec, base_dir)
        payload = canonical_payload(spec, files)
        print(ruler_hash(payload))


