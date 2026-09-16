"""Read and write the oathgate lock file."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from oathgate.spec import SpecError, compute_ruler

LOCK_VERSION = 1
LOCK_NAME = "oathgate.lock"

def write_lock(
    lock_path: Path,
    *,
    digest: str,
    spec_name: str,
    metric: str,
    operator: str,
    value: float,
    note: str | None = None,
    history: list[dict[str, Any]] | None = None,
    now: datetime | None = None
    ) -> dict[str, Any]:
    """Write the lock file atomically and return the structure written."""
    if history is None: 
        history = []
    frozen_at = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()

    for entry in history:
        entry.setdefault("superseded_at", frozen_at)

    lock: dict[str, Any] = {
        "version": LOCK_VERSION,
        "ruler_hash": digest,
        "frozen_at": frozen_at,
        "spec_path": spec_name,
        "predictions": [
            {"metric": metric, "operator": operator, "value": value},
        ],
        "history": history,
    }

    if note:
        lock["predictions"][0]["note"] = note

    text = json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp_path = lock_path.with_suffix(lock_path.suffix + ".tmp")

    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, lock_path)
    except OSError as e:
        raise SpecError(f"cannot write {lock_path}: {e}") from e
    finally:
        # A successful os.replace has already moved it away; missing_ok covers that.
        tmp_path.unlink(missing_ok=True)

    return lock

def read_lock(lock_path: Path) -> dict[str, Any]:
    """Read and validate a lock file."""
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except OSError as e:
        raise SpecError(f"cannot read {lock_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise SpecError(f"invalid JSON in {lock_path}: {e}") from e

    if not isinstance(lock, dict):
        raise SpecError(f"{lock_path} does not contain an object")

    expected = lock.get("ruler_hash")
    if not isinstance(expected, str):
        raise SpecError(f"{lock_path}: ruler_hash is missing or not a string")

    if "history" in lock and not isinstance(lock["history"], list):
        raise SpecError(f"{lock_path}: history is not a list")

    return lock

def verify(spec_path: Path, lock_path: Path) -> tuple[bool, str, str, dict[str, bytes]]:
    """Compare the current ruler against the lock: (ok, expected, actual, files)."""
    lock = read_lock(lock_path)
    expected = lock["ruler_hash"]
    digest, _, files = compute_ruler(spec_path)

    return digest == expected, expected, digest, files