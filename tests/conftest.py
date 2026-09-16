import pytest


@pytest.fixture
def tree(tmp_path):
    """A minimal valid spec tree: spec, dataset, scorer."""
    (tmp_path / "data.csv").write_text("id,label\n1,cat\n")
    (tmp_path / "scorer.py").write_text("def score(row):\n  return 1.0\n")
    (tmp_path / "oathgate.toml").write_text(
        '[dataset]\npath = "data.csv"\n\n[metrics.accuracy]\nimpl = "scorer.py"\n'
    )
    return tmp_path
