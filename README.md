# oathgate

**Take the oath before you run the eval.**

`oathgate` blocks an evaluation run until two things are on the record:

1. **The measurement ruler is frozen** — metrics, thresholds, dataset composition and references are hashed.
2. **A prediction is written down** — what you expect to happen, before you know what happened.

Nothing here measures your model. It measures whether you were honest about how you measured.

## The problem

Evals drift. Not because anyone lies, but because the ruler is soft: a threshold moves from 0.85 to 0.80, three hard cases quietly leave the set, a metric is swapped for a friendlier one — and the number goes up. Every step is defensible on its own. The result is a benchmark that only ever improves.

The fix is not more rigour in the moment. It is making the ruler expensive to change _after_ you have seen the outcome.

## What gets hashed

Only the ruler:

| Hashed                      | Not hashed                |
| --------------------------- | ------------------------- |
| `metrics`                   | prompt                    |
| `thresholds`                | model / checkpoint        |
| `dataset` (composition)     | agent scaffold            |
| `references` (gold answers) | temperature, seeds, infra |

This split is the whole design. You are _supposed_ to change the system under test — that is the experiment. The ruler is what has to hold still for the comparison to mean anything.

## Usage

Freeze the ruler and commit to a prediction:

```console
$ oathgate freeze examples/spec.json --predict "f1 lands between 0.88 and 0.92; exact_match misses the 0.80 bar"
frozen  4f2a91c0d3e8  -> oath.lock.json
oath    f1 lands between 0.88 and 0.92; exact_match misses the 0.80 bar
```

Then, as the first step of your run:

```console
$ oathgate check && python run_eval.py
ok      4f2a91c0d3e8  ruler unchanged
oath    f1 lands between 0.88 and 0.92; exact_match misses the 0.80 bar
```

If someone nudged a threshold in between, the gate refuses and exits non-zero:

```console
$ oathgate check
BLOCKED: the measurement ruler changed after the oath was taken.
  frozen:  4f2a91c0d3e8  (2026-08-31T09:14:00+00:00)
  current: b71e05ad9c2f
  Re-freeze deliberately, or restore the spec. Do not do it silently.
```

Re-freezing is allowed. It just cannot happen by accident, and it leaves a timestamp.

## Install

```console
pip install oathgate
```

## Spec format

A JSON file with the four ruler keys. Anything else — including a `system` block describing what you are testing — is ignored by the hash and free to change.

See [`examples/spec.json`](https://github.com/UladzKha/oathgate/blob/main/examples/spec.json).

## Status

Early. The CLI is the whole surface right now; an MCP wrapper is planned so agents can be held to the same gate.

## Licence

MIT
