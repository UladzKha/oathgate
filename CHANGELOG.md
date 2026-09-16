# Changelog

## 0.1.0

The release that makes the tool usable end to end: record a prediction,
run the eval, verify the ruler did not move.

### Added

- `oathgate predict` — record a prediction and write `oathgate.lock`.
  `--at-least` for metrics where higher is better, `--at-most` where lower is
  (error rate, latency, hallucination rate). Both inclusive.
- `oathgate check` — recompute the ruler and compare it against the lock.
  Exit 0 unchanged, 1 moved, 2 cannot tell.
- `--force` replaces an existing lock and moves the previous one into
  `history`, keeping its own `superseded_at`.
- `--note` stores a free-form line in the lock. Not hashed.
- `--lock` reads the lock from a path other than next to the spec.

### Changed

- Paths in the spec are normalized before hashing, so `data.csv`,
  `./data.csv` and `sub/../data.csv` produce the same ruler hash. Absolute
  paths, drive letters, backslashes and paths escaping the spec directory are
  rejected.
- File keys in the hashed payload are normalized to NFC, so a path written in
  decomposed form hashes the same as its composed form.
- Malformed specs and locks now exit 2 with a message instead of raising a
  traceback.

### Notes

The lock is JSON while the spec is TOML: you write the spec, the tool writes
the lock, and Python reads JSON without a dependency. oathgate still has no
runtime dependencies.