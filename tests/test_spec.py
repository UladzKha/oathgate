from oathgate.spec import _canon_value, SpecError

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

