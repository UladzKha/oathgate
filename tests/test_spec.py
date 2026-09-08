from oathgate.spec import _canon_value, SpecError, _hash_bytes, canonical_payload, collect_files, load_spec, ruler_hash

import pytest
import datetime


def test_int_and_float_hash_the_same():
    assert _canon_value(1, where="x") == _canon_value(1.0, where="x")

def test_bool_hash():
    assert _canon_value(True, where="x") is True

def test_negative_zero_normalized_to_positive():
    assert repr(_canon_value(-0.0, where="x")) ==  "0.0"

def test_nested_structures_canonicalized_recursively():
    assert _canon_value({"a": [1, {"b": "c"}]}, where="spec") == {"a": [1.0, {"b": "c"}]}

def test_number_is_too_big():
    with pytest.raises(SpecError):
        _canon_value(2**60, where="x")
def test_NaN_is_not_allowed():
    with pytest.raises(SpecError):
        _canon_value(float("nan"), where="x")

def test_infinity_is_not_allowed():
    with pytest.raises(SpecError):
        _canon_value(float("inf"), where="x")

def test_NFC_normalization_of_strings():
    assert _canon_value("e\u0301", where="x") == "é"

def test_key_duplicate_after_normalization():
    with pytest.raises(SpecError):
        _canon_value({"e\u0301": 1, "é": 2}, where="\u00e9")

def test_non_string_key_raises():
    with pytest.raises(SpecError):
        _canon_value({1: "a"}, where="x")

def test_date_is_ISO_string():
    assert _canon_value(datetime.date(2023, 1, 1), where="x") == "2023-01-01"

def test_tuple_and_list_are_equivalent():
    assert _canon_value((1, 2), where="x") == _canon_value([1, 2], where="x")
    assert isinstance(_canon_value((1, 2), where="x"), list)

def test_bytes_rejected():
    with pytest.raises(SpecError):
        _canon_value(b"abc", where="x")

def test_set_rejected():
    with pytest.raises(SpecError):
        _canon_value({1, 2, 3}, where="x")

def test_hash_bytes_matches_known_sha256():
    assert _hash_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def test_canonical_payload_structure():
    result = canonical_payload({}, {"a.py": b""})
    assert result["_format"] == "gate-spec-v1"
    assert result["spec"] == {}
    assert result["files"]["a.py"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def test_ruler_hash():
    payload = canonical_payload({}, {"a.py": b"", "b.py": b""})
    result = ruler_hash(payload)
    assert len(result) == 64

def test_ruler_hash_ignores_key_order():
    a = canonical_payload({}, {"a.py": b"", "b.py": b""})
    b = canonical_payload({}, {"b.py": b"", "a.py": b""})
    assert ruler_hash(a) == ruler_hash(b)

def test_load_spec_reads_valid_file(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""
[dataset]
path = "data/golden.jsonl"

[metrics.accuracy]
impl = "scorers/accuracy.py"
""")
    result = load_spec(spec_file)
    assert result["dataset"]["path"] == "data/golden.jsonl"

def test_load_spec_missing_dataset(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("")

    with pytest.raises(SpecError, match="missing \\[dataset\\] section"):
        load_spec(spec_file)

def test_load_spec_missing_dataset_path(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
""")
    
    with pytest.raises(SpecError, match="missing \\[dataset\\].path"):
        load_spec(spec_file)

def test_load_spec_missing_metrics(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
""")
    with pytest.raises(SpecError, match="missing \\[metrics\\] section"):
        load_spec(spec_file)

def test_load_spec_empty_metrics(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
[metrics]""")
    with pytest.raises(SpecError, match="empty \\[metrics\\] section"):
        load_spec(spec_file)

def test_load_spec_missing_metric_impl(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
[metrics.accuracy]""")
    with pytest.raises(SpecError, match="missing \\[metrics\\].accuracy.impl"):
        load_spec(spec_file)

def test_load_spec_extra_files_not_list(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
[metrics.accuracy]
impl = "scorers/accuracy.py"
extra_files = "not a list" """)
    with pytest.raises(SpecError, match="extra_files must be a list"):
        load_spec(spec_file)

def test_load_spec_extra_files_not_strings(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
[metrics.accuracy]
impl = "scorers/accuracy.py"
extra_files = [1, 2, 3]""")
    with pytest.raises(SpecError, match="extra_files must be a list of strings"):
        load_spec(spec_file)

def test_load_spec_reads_valid_file_with_extra_files(tmp_path):
    spec_file = tmp_path / "oathgate.toml"
    spec_file.write_text("""[dataset]
path = "data/golden.jsonl"
[metrics.accuracy]
impl = "scorers/accuracy.py"
extra_files = ["file1.txt", "file2.txt"]""")
    result = load_spec(spec_file)
    assert result["metrics"]["accuracy"]["extra_files"] == ["file1.txt", "file2.txt"]

def test_collect_files_reads_all(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "golden.jsonl").write_bytes(b"line1")
    (tmp_path / "scorers").mkdir()
    (tmp_path / "scorers" / "accuracy.py").write_bytes(b"code")

    spec = {
        "dataset": {"path": "data/golden.jsonl"},
        "metrics": {"accuracy": {"impl": "scorers/accuracy.py"}},
    }
    result = collect_files(spec, tmp_path)

    assert result == {
        "data/golden.jsonl": b"line1",
        "scorers/accuracy.py": b"code",
    }

def test_collect_files_reads_extra_files(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "golden.jsonl").write_bytes(b"line1")
    (tmp_path / "scorers").mkdir()
    (tmp_path / "scorers" / "accuracy.py").write_bytes(b"code")
    (tmp_path / "scorers" / "common.py").write_bytes(b"common code")

    spec = {
        "dataset": {"path": "data/golden.jsonl"},
        "metrics": {"accuracy": {"impl": "scorers/accuracy.py", "extra_files": ['scorers/common.py']}},
    }
    result = collect_files(spec, tmp_path)

    assert result == {
        "data/golden.jsonl": b"line1",
        "scorers/accuracy.py": b"code",
        "scorers/common.py": b"common code"
    }