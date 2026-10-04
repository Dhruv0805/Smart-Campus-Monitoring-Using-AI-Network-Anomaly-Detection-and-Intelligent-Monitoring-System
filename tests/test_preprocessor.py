import numpy as np
import pandas as pd
import pytest

from engine import data_preprocessor as dp


def test_normalize_columns_removes_question_mark():
    df = pd.DataFrame({"tcp?ActiveOpens": [1], " x ": [2], "class": ["normal"]})
    assert list(dp.normalize_columns(df).columns) == ["tcpActiveOpens", "x", "class"]


def test_dataset1_shape_and_classes():
    df = dp.load_snmp_dataset()
    assert df.shape == (4998, 35)
    assert set(df["class"]) == {"normal", "tcp-syn", "slowloris", "udp-flood", "icmp-echo", "httpFlood", "slowpost", "bruteForce"}
    assert "tcpActiveOpens" in df.columns


def test_dataset2_shape_and_sources():
    df = dp.load_local_dataset()
    assert len(df) == 40262
    assert set(df["source"]) == {"A", "B", "C", "D"}
    assert df["class"].nunique() == 8


def test_audit_detects_problems():
    df = pd.DataFrame({"a": [1, 1, 1, 2], "const": [5, 5, 5, 5], "b": [1.0, np.nan, 3, -1], "class": ["n", "n", "x", "x"]})
    rep = dp.audit(df)
    assert rep["constant_features"] == ["const"]
    assert rep["missing_values"] == 1
    assert rep["negative_values"] == 1
    assert rep["class_counts"] == {"n": 2, "x": 2}


def test_clean_imputes_removes_constant_and_keeps_order():
    df = pd.DataFrame({"a": [3, 1, np.inf, 2], "const": [5, 5, 5, 5], "class": list("wxyz")})
    out, rep = dp.clean(df)
    assert "const" not in out.columns and rep["constant_removed"] == ["const"]
    assert not out["a"].isna().any() and np.isfinite(out["a"]).all()
    assert list(out["class"]) == list("wxyz")          # row order preserved (time order matters)


def test_validate_columns():
    assert dp.validate_columns(pd.DataFrame({"a": [1]}), ["a", "b"]) == ["b"]


def test_dataset_has_no_missing_or_duplicates():
    for rep in (dp.audit(dp.load_snmp_dataset()), dp.audit(dp.load_local_dataset())):
        assert rep["missing_values"] == 0 and rep["duplicate_rows"] == 0
