# oathgate

[![tests](https://github.com/UladzKha/oathgate/actions/workflows/ci.yml/badge.svg)](https://github.com/UladzKha/oathgate/actions/workflows/ci.yml)

**Freeze the eval scoring spec and your prediction before the run.**

## The problem
Someone reports 87% accuracy. A month later, 91%. Is that progress?

Or was the dataset trimmed and the scoring loosened between the runs?

## What it does
oathgate hashes the dataset by content, the metric definitions, and the
source code of every scorer. Rename nothing, edit one row, and the hash moves.

The spec has no place for the model or the prompt — you are supposed to change
those. The ruler is what has to hold still. Anything you do write in the spec
is hashed, though, so the model name does not belong there either.

It hashes the ruler, not the thing being measured.

## Status
Early but usable. All three commands work: `freeze`, `predict`, `check`.
The lock file carries a format version, so locks written today stay readable.

## Installation
`pip install oathgate`

## Usage

### The spec

By default oathgate looks for `oathgate.toml` in the current directory.
`--spec path/to/oathgate.toml` points it somewhere else, and the paths inside
the spec are then relative to the spec file rather than to the working
directory.

```toml
[dataset]
path = "data/golden.jsonl"

[metrics.accuracy]
impl = "scorers/accuracy.py"
extra_files = ["scorers/common.py"]
```

### 1. Predict

Record what you expect before you run the eval. This writes `oathgate.lock`.

```
$ oathgate predict --metric accuracy --at-least 0.85
86c6474e143095d8facf62bea2697998c7b93215d8103c0ecf37ae92431daec4
wrote oathgate.lock: accuracy >= 0.85
```

Commit the lock file. Then run your eval.

Use `--at-most` for metrics where lower is better — error rate, latency,
hallucination rate:

```
$ oathgate predict --metric error_rate --at-most 0.05
```

Both operators are inclusive. `--at-least 0.85` passes at exactly 0.85, and
`--at-most 0.05` passes at exactly 0.05.

`--force` replaces an existing lock and moves the old one into `history`.

`--note "after prompt v3"` stores a free-form line in the lock. It goes into the
prediction, not into the hash, so adding one does not move the ruler.

### 2. Check

After the run, confirm the ruler did not move while you were at it.

```
$ oathgate check
ok 86c6474e143095d8facf62bea2697998c7b93215d8103c0ecf37ae92431daec4
```

If something the spec names has changed:

```
$ oathgate check
ruler moved
    expected 86c6474e143095d8facf62bea2697998c7b93215d8103c0ecf37ae92431daec4
    actual   aff71591a5a2aaf7203f17ea84c4b7b8be51d0fb60c79ed5b0a5e976e3f4a4c3
hashed inputs:
   data/golden.jsonl
   scorers/accuracy.py
   scorers/common.py
```

The list is every file that went into the hash. One of them changed, or the
spec itself did.

The lock is written next to the spec. `check --lock <path>` reads it from
somewhere else instead — useful when the lock arrives as an artifact from
another CI job rather than living in the tree.

### freeze

`oathgate freeze` prints the ruler hash and writes nothing. Use it to see the
current hash without touching the lock file.

```
$ oathgate freeze
86c6474e143095d8facf62bea2697998c7b93215d8103c0ecf37ae92431daec4
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | The ruler is the one you froze |
| 1 | The ruler moved |
| 2 | Cannot tell — no lock file, unreadable spec, broken lock |

1 and 2 are different failures and should be handled differently.

1 means oathgate did the comparison and it came out negative. The methodology
changed between the prediction and the run, so the new number and the old
number do not measure the same thing. They are not comparable.

2 means oathgate never got far enough to compare. The spec would not parse, the
lock file is missing, a scorer file was deleted. That is a setup problem, not a
methodology one. Nothing is known yet about whether the ruler moved.

CI depends on this distinction. A 1 means someone changed the ruler and owes an
explanation. A 2 means the job is misconfigured and the result tells you
nothing either way.

## In CI

Run `oathgate check` before the step that runs the eval. A moved ruler then
fails the build instead of quietly producing a number nobody can compare to
last week's.

```yaml
name: eval

on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install oathgate
        run: pip install oathgate==0.1.0

      - name: Check the ruler
        run: oathgate check

      - name: Run the eval
        run: python run_eval.py
```

Pin the version. An unpinned install lets a future release of oathgate change
what CI compares against, which is the one thing this tool exists to prevent —
a hash that moves because the tool changed looks exactly like a hash that moved
because the ruler did.

The `oathgate.lock` file must be committed for this to work. If it is missing,
`check` exits 2 and the build fails with a setup error rather than a false pass.

## What this actually guarantees

oathgate does not stop anyone from editing the lock file. It is a text file in
your own repository and you have write access to it. Nothing in the tool
prevents someone from running the eval, seeing 0.83, and changing the
prediction to `--at-least 0.80`.

The guarantee comes from git, not from oathgate. Commit the lock file before
you run the eval. The history then shows the prediction was written first, by
whom, and at what time. Changing it afterwards means a second commit, and that
commit is visible.

Storing a hash next to the prediction would not add anything. Whoever can edit
the prediction can recompute the hash over the edited version. The integrity has
to come from somewhere the editor does not control, and in a normal workflow
that place is the commit history.

Signing and trusted timestamps are out of scope. If you need a prediction that
holds up against someone with force-push rights, oathgate is not enough.

The discipline is four steps:

1. `oathgate predict` — record what you expect
2. `git commit` — put the prediction in the history
3. Run the eval
4. `oathgate check` — confirm the ruler did not move

Step 2 is the one that matters. The other three are bookkeeping around it.

## Known limitations

**Everything in the spec goes into the hash, not just paths.** Renaming a metric
or changing a threshold inside the spec moves the ruler. This is intentional —
the spec *is* the methodology, and a renamed metric is a different metric. It
does mean the spec is not a place for notes: a `description` field you add to
explain a choice moves the hash just like a threshold does. TOML comments are
safe, since the parser drops them before oathgate sees the spec.

**The spec is TOML and the lock is JSON.** The human writes the spec, so it
should be pleasant to write. The tool writes the lock, so it only has to read
back unambiguously, and Python parses JSON without a dependency.

**Paths are normalized lexically, not resolved.** A symlinked directory inside
the spec tree can point the hash at a file outside it. oathgate does not apply
`resolve()` semantics, so `a/../b` collapses to `b` even when `a` is a symlink.

**`check` verifies the ruler, not the measurement.** oathgate never runs your
eval, so it has no number to compare against the prediction. It tells you the
methodology held still. Comparing the number you got against the number you
predicted is your job, or your CI's.