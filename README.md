# oathgate

**Freeze the eval scoring spec and your prediction before the run.**

## The problem
Someone reports 87% accuracy. A month later, 91%. Is that progress?

Or was the dataset trimmed and the scoring loosened between the runs?

## What it does
Oathgate freezes the dataset, the metrics, and the scorer source code.
It does not freeze the model or the prompt — so you can change those and
still compare results, because the measurement stays the same.

## Installation
`pip install oathgate`

## Spec example
```toml
[dataset]
path = "examples/golden.jsonl"

[metrics.accuracy]
impl = "examples/accuracy.py"
```

## Usage

`oathgate freeze`

Prints the hash of your scoring spec:

```
90d4af4923f4ca466021ab36e24e5fc749eaf6108a7bbf56c13d73faba7baf0c
```

## Status
Early alpha. Only `freeze` works today. `predict` and `run` are planned.

