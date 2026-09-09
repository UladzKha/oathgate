[![tests](https://github.com/UladzKha/oathgate/actions/workflows/ci.yml/badge.svg)](https://github.com/UladzKha/oathgate/actions/workflows/ci.yml)
# oathgate

**Freeze the eval scoring spec and your prediction before the run.**

## The problem
Someone reports 87% accuracy. A month later, 91%. Is that progress?

Or was the dataset trimmed and the scoring loosened between the runs?

## What it does
Oathgate hashes the dataset by content, the metric definitions, and the
source code of every scorer. Rename nothing, edit one row, and the hash moves.

It does not hash the model or the prompt — you are supposed to change those.
The ruler is what has to hold still.

## Installation
`pip install oathgate==0.0.4`

## Spec example
```toml
[dataset]
path = "examples/golden.jsonl"

[metrics.accuracy]
impl = "examples/accuracy.py"
```

## Usage

`oathgate freeze`

Reads `oathgate.toml` from the current directory and prints the hash of your
scoring spec:

```
90d4af4923f4ca466021ab36e24e5fc749eaf6108a7bbf56c13d73faba7baf0c
```

## Status
Early alpha. Only `freeze` works today. `predict` and `run` are planned.

