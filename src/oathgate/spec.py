from __future__ import annotations

import datetime
import hashlib
import json
import math
import re
import unicodedata
from typing import Any


_DRIVE_LETTER = re.compile(r"^[a-zA-Z]:\\")
_MAX_EXACT_INT = 2 ** 53

class SpecError(Exception):
        """Any problem with reading, validating or canonicalizing a spec."""
   

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



