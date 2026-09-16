from __future__ import annotations

import tomllib
import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import unicodedata
from typing import Any

_MAX_EXACT_INT = 2 ** 53

class SpecError(Exception):
        """Any problem with reading, validating or canonicalizing a spec."""

def _normalize_path(raw: str, *, where: str) -> str:
    """Normalize a path from the spec into a stable relative POSIX key."""
    if not raw:
        raise SpecError(f"{where}: path is empty")

    if "\\" in raw:
        raise SpecError(f"{where}: backslash in path {raw!r}")

    if re.match(r"^[A-Za-z]:", raw):
        raise SpecError(f"{where}: {raw!r} drive letter in path")

    if raw.startswith("/"):
        raise SpecError(f"{where}: absolute path {raw!r}; paths are relative to the spec")

    parts = PurePosixPath(raw).parts
    result: list[str] = []

    for part in parts:
        if part == ".":
            continue

        if part == "..":
            if not result:
                raise SpecError(f"{where}: path {raw!r} escapes the spec directory")

            result.pop()
            continue

        result.append(part)

    if not result:
        raise SpecError(f"{where}: path {raw!r} does not name a file")

    return "/".join(result)

def _canon_value(value: Any, *, where: str) -> Any:
    """Bring a spec value to a canonical form before serialization."""
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        if abs(value) > _MAX_EXACT_INT:
            raise SpecError(f"{where}: integer {value} is too large to hash without precision loss")
        return float(value)

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise SpecError(f"{where}: float {value} is not a finite number")
        if value == 0.0:
            return 0.0
        return value

    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)

    if isinstance(value, (list, tuple)):
        return [
            _canon_value(item, where=f"{where}[{index}]")
            for index, item in enumerate(value)
        ]

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SpecError(f"{where}: key {key!r} is not a string")
            canon_key = unicodedata.normalize("NFC", key)
            if canon_key in result:
                raise SpecError(f"{where}: duplicate key {canon_key!r} after normalization")
            result[canon_key] = _canon_value(item, where=f"{where}.{canon_key}")
        return result

    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    
    raise SpecError(f"{where}: unsupported value type {type(value).__name__}")

def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_payload(spec: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    """Build the deterministic structure that gets hashed."""
    return {
        "_format": "gate-spec-v1",
        "spec": _canon_value(spec, where="spec"),
        "files": { path: _hash_bytes(content) for path, content in files.items()},
    }

def ruler_hash(payload: dict[str, Any]) -> str:
    return _hash_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))

def load_spec(path: str | Path) -> dict[str, Any]:
    """Read and parse a spec file from disk."""
    try:
        with open(path, "rb") as f:
            spec = tomllib.load(f)
    except OSError as e:
        raise SpecError(f"cannot read {path}: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise SpecError(f"invalid TOML in {path}: {e}") from e
        
    if "dataset" not in spec:
        raise SpecError(f"missing [dataset] section in {path}")

    if not isinstance(spec["dataset"], dict):
        raise SpecError(f"[dataset] must be a section in {path}")

    if "path" not in spec["dataset"]:
        raise SpecError(f"missing [dataset].path in {path}")

    if "metrics" not in spec:
        raise SpecError(f"missing [metrics] section in {path}")

    if not isinstance(spec["metrics"], dict):
        raise SpecError(f"[metrics] must be a section in {path}")

    if not spec["metrics"]:
        raise SpecError(f"empty [metrics] section in {path}")

    if not isinstance(spec["dataset"]["path"], str):
        raise SpecError(f"[dataset].path must be a string in {path}")

    spec["dataset"]["path"] = _normalize_path(spec["dataset"]["path"], where="dataset.path")

    for name, metric in spec["metrics"].items():
        if not isinstance(metric, dict):
            raise SpecError(f"[metrics].{name} must be a section in {path}")

        if "impl" not in metric:
            raise SpecError(f"missing [metrics].{name}.impl in {path}")

        if not isinstance(metric["impl"], str):
            raise SpecError(f"[metrics].{name}.impl must be a string in {path}")

        metric["impl"] = _normalize_path(metric["impl"], where=f"metrics.{name}.impl")

        if "extra_files" not in metric:
            continue

        if not isinstance(metric["extra_files"], list):
            raise SpecError(f"[metrics].{name}.extra_files must be a list in {path}")

        for value in metric["extra_files"]:
            if not isinstance(value, str):
                raise SpecError(f"[metrics].{name}.extra_files must be a list of strings in {path}")

        metric["extra_files"] = [
            _normalize_path(value, where=f"metrics.{name}.extra_files")
            for value in metric["extra_files"]
        ]

    return spec

def collect_files(spec: dict[str, Any], base_dir: Path) -> dict[str, bytes]:
    """Read every file the spec names, keyed by its NFC-normalized path.

    The file is read through the path exactly as the spec spells it, since on
    disk a name is bytes and an NFC path will not find a file stored in NFD.
    The key is only an identity label inside the payload, so it is normalized
    to match the NFC form the spec half of the payload is canonicalized to.
    """
    result: dict[str, bytes] = {}
    path_str = spec["dataset"]["path"]
    full_path = base_dir / path_str

    try:
        result[unicodedata.normalize("NFC", path_str)] = full_path.read_bytes()
    except OSError as e:
        raise SpecError(f"cannot read {path_str}: {e}") from e

    for _, metric in spec["metrics"].items():
        impl_path = metric["impl"]
        full_impl_path = base_dir / impl_path

        try:
            result[unicodedata.normalize("NFC", impl_path)] = full_impl_path.read_bytes()
        except OSError as e:
            raise SpecError(f"cannot read {impl_path}: {e}") from e

        if "extra_files" in metric:
            for extra_path in metric["extra_files"]:
                full_extra_path = base_dir / extra_path

                try:
                    result[unicodedata.normalize("NFC", extra_path)] = full_extra_path.read_bytes()
                except OSError as e:
                    raise SpecError(f"cannot read {extra_path}: {e}") from e

    return result

def compute_ruler(spec_path: Path) -> tuple[str, dict[str, Any], dict[str, bytes]]:
    """Load, hash and return the ruler for a spec: (hash, spec, files)."""
    base_dir = spec_path.parent
    spec = load_spec(spec_path)
    files = collect_files(spec, base_dir)
    payload = canonical_payload(spec, files)
    digest = ruler_hash(payload)

    return digest, spec, files


