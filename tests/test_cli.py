from oathgate.cli import main
from oathgate.lock import LOCK_NAME, read_lock
from oathgate.spec import compute_ruler

def test_predict_unknown_metric_writes_nothing(tree):
    code = main(
        ["predict", "--spec", str(tree / "oathgate.toml"),
         "--metric", "f1", "--at-least", "0.9"]
    )

    assert code == 2
    assert not (tree / LOCK_NAME).exists()

def test_predict_refuses_to_overwrite(tree):
    args = ["predict", "--spec", str(tree / "oathgate.toml"),
            "--metric", "accuracy", "--at-least", "0.85"]

    assert main(args) == 0
    before = (tree / LOCK_NAME).read_text()

    assert main(args) == 2
    assert (tree / LOCK_NAME).read_text() == before

def test_force_moves_previous_into_history(tree):
    spec = str(tree / "oathgate.toml")
    base = ["predict", "--spec", spec, "--metric", "accuracy"]

    assert main(base + ["--at-least", "0.85"]) == 0
    assert main(base + ["--at-least", "0.90", "--force"]) == 0

    lock = read_lock(tree / LOCK_NAME)

    assert lock["predictions"][0]["value"] == 0.90
    assert len(lock["history"]) == 1

    old = lock["history"][0]
    assert old["predictions"][0]["value"] == 0.85
    assert "superseded_at" in old
    assert "history" not in old

def test_check_passes_then_fails_after_edit(tree):
    spec = str(tree / "oathgate.toml")

    assert main(["predict", "--spec", spec,
                "--metric", "accuracy", "--at-least", "0.85"
                 ]) == 0
    assert main(["check", "--spec", spec]) == 0

    (tree / "data.csv").write_text("id,label\n1,dog\n")
    assert main(["check", "--spec", spec]) == 1

def test_check_without_lock_cannot_compute(tree):
    assert main(["check", "--spec", str(tree / "oathgate.toml")]) == 2

def test_check_fails_after_scorer_edit(tree):
    spec = str(tree / "oathgate.toml")

    assert main(["predict", "--spec", spec, "--metric", "accuracy", "--at-least", "0.85"]) == 0

    (tree / "scorer.py").write_text("def score(row):\n  return 0.0\n")
    assert main(["check", "--spec", str(tree / "oathgate.toml")]) == 1

def test_check_rejects_lock_that_is_not_an_object(tree):
    (tree / LOCK_NAME).write_text("42\n")
    assert main(["check", "--spec", str(tree / "oathgate.toml")]) == 2

def test_check_rejects_broken_json(tree):
    (tree / LOCK_NAME).write_text("{not json\n}")
    assert main(["check", "--spec", str(tree / "oathgate.toml")]) == 2

def test_writing_lock_does_not_change_hash(tree):
    spec_path = tree / "oathgate.toml"
    before, _, _ = compute_ruler(spec_path)

    assert main(["predict", "--spec", str(spec_path), "--metric", "accuracy", "--at-least", "0.85"]) == 0

    after, _, _ = compute_ruler(spec_path)
    assert after == before

def test_at_most_records_the_other_operator(tree):
    spec = str(tree / "oathgate.toml")

    assert main(["predict", "--spec", spec,
                 "--metric", "accuracy", "--at-most", "0.10"]) == 0

    lock = read_lock(tree / LOCK_NAME)
    assert lock["predictions"][0]["operator"] == "<="
    assert lock["predictions"][0]["value"] == 0.10
def test_check_rejects_lock_with_non_list_history(tree):
    (tree / LOCK_NAME).write_text('{"version": 1, "ruler_hash": "abc", "history": {}}\n')
    assert main(["check", "--spec", str(tree / "oathgate.toml")]) == 2
