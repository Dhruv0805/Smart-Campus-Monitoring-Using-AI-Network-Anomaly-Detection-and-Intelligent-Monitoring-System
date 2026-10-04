import numpy as np
import pytest

from engine import MODEL_PATH
from engine import data_preprocessor as dp
from engine.feature_extraction import (COUNTER_COLS, WINDOW, StreamingFeatureExtractor, batch_features,
                                       counters_to_deltas, feature_names)
from engine.model_evaluation import blocked_splits, metrics
from engine.pipeline import MonitoringPipeline, validate_record
from engine.risk_scoring import RiskScorer, level_for

needs_model = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run run_experiments.py first")


def test_wraparound_repaired_and_reset_invalid():
    import pandas as pd
    rows = [{c: 0.0 for c in COUNTER_COLS} for _ in range(4)]
    rows[0]["ifInOctets11"] = 2 ** 32 - 10
    rows[1]["ifInOctets11"] = 5          # wrapped: true delta = 15
    rows[2]["ifInOctets11"] = 25
    rows[3]["ifInOctets11"] = 3          # tiny prev -> counter reset => invalid row
    for r in rows[2:]:
        r["ipInReceives"] = 100
    D = counters_to_deltas(pd.DataFrame(rows))
    assert D["ifInOctets11"].iloc[1] == 15 and D["ifInOctets11"].iloc[2] == 20
    assert D.iloc[3].isna().all()


def test_streaming_matches_batch_features():
    raw = dp.load_snmp_dataset().iloc[:500]
    F, valid = batch_features(raw)
    ex = StreamingFeatureExtractor(WINDOW)
    for i in range(len(raw)):
        vec, _ = ex.push(raw.iloc[i][COUNTER_COLS].to_dict())
        if i == 0:
            assert vec is None
        else:
            np.testing.assert_allclose(vec, F.iloc[i].to_numpy(), rtol=1e-6, atol=1e-5, err_msg=f"row {i}")
    assert list(F.columns) == feature_names()


def test_validate_record_rejects_bad_input():
    good = {c: 1.0 for c in COUNTER_COLS}
    assert validate_record(good)
    with pytest.raises(ValueError):
        validate_record("nope")
    with pytest.raises(ValueError):
        validate_record({k: v for k, v in good.items() if k != "ipInReceives"})
    with pytest.raises(ValueError):
        validate_record({**good, "tcpInSegs": -5})
    with pytest.raises(ValueError):
        validate_record({**good, "tcpInSegs": float("nan")})
    with pytest.raises(ValueError):
        validate_record({**good, "tcpInSegs": "12"})


def test_risk_levels_monotonic():
    assert [level_for(s) for s in (0, 20, 40, 60, 90)] == ["NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_blocked_split_has_no_overlap_and_embargo():
    for tr, te in blocked_splits(1000, block=100, k=5, embargo=5):
        assert not set(tr) & set(te)
        assert not any((i + d) in set(tr) for i in te for d in range(1, 6))


def test_metrics_perfect_and_false_alarm():
    m = metrics(["normal", "a", "a"], ["normal", "a", "a"])
    assert m["accuracy"] == 1 and m["false_alarm_rate"] == 0 and m["binary_anomaly_f1"] == 1
    m = metrics(["normal", "normal", "a"], ["a", "normal", "a"])
    assert m["false_alarm_rate"] == 0.5


@needs_model
def test_pipeline_output_schema_and_warmup():
    p = MonitoringPipeline()
    raw = dp.load_snmp_dataset()
    first = p.process(raw.iloc[0][COUNTER_COLS].to_dict(), zone="z")
    assert first["warming_up"] and not first["is_anomaly"]
    out = p.process(raw.iloc[1][COUNTER_COLS].to_dict(), zone="z", timestamp=1.0)
    for k in ("prediction", "is_anomaly", "confidence", "p_anomaly", "risk", "metrics", "probabilities", "confirmed"):
        assert k in out
    assert 0 <= out["confidence"] <= 1 and out["risk"]["level"] in ("NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert abs(sum(out["probabilities"].values()) - 1) < 0.01


@needs_model
def test_zones_are_isolated():
    p = MonitoringPipeline()
    raw = dp.load_snmp_dataset()
    p.process(raw.iloc[0][COUNTER_COLS].to_dict(), zone="a")
    assert p.process(raw.iloc[1][COUNTER_COLS].to_dict(), zone="b")["warming_up"]


@needs_model
def test_saved_model_beats_chance_on_honest_cv():
    from engine.model_loader import load_bundle
    b = load_bundle()
    assert b["cv"]["macro_f1"] > 0.5 and b["cv"]["binary_anomaly_f1"] > 0.85
    assert set(b["thresholds"]) == set(b["classes"]) - {"normal"}
    assert all(0.01 <= t <= 0.95 for t in b["thresholds"].values())
