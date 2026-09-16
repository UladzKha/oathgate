import os
from datetime import datetime, timezone

import pytest

from oathgate.lock import LOCK_NAME, read_lock, write_lock
from oathgate.spec import SpecError, compute_ruler

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_lock_hash_matches_freeze(tree):
    digest, _, _ = compute_ruler(tree / "oathgate.toml")

    write_lock(
        tree / LOCK_NAME,
        digest=digest,
        spec_name="oathgate.toml",
        metric="accuracy",
        operator=">=",
        value=0.85,
        now=FIXED_NOW
    )

    lock = read_lock(tree / LOCK_NAME)
    assert lock["ruler_hash"] == digest


def test_read_lock_rejects_history_that_is_not_a_list(tree):
    (tree / LOCK_NAME).write_text(
        '{"version": 1, "ruler_hash": "abc", "history": "x"}'
    )

    with pytest.raises(SpecError, match="history is not a list"):
        read_lock(tree / LOCK_NAME)


def test_write_lock_removes_the_temp_file_when_replace_fails(tree, monkeypatch):
    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(SpecError, match="cannot write"):
        write_lock(
            tree / LOCK_NAME,
            digest="0" * 64,
            spec_name="oathgate.toml",
            metric="accuracy",
            operator=">=",
            value=0.85,
            now=FIXED_NOW,
        )

    assert not list(tree.glob("*.tmp"))
    assert not (tree / LOCK_NAME).exists()
