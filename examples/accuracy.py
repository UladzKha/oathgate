def score(predictions, expected):
    correct = sum(p == e for p, e in zip(predictions, expected))
    return correct / len(expected)