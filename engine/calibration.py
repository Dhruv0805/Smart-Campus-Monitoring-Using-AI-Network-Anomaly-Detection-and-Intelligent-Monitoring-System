"""Operating-point calibration with per-class thresholds.

A single p(anomaly) threshold cannot bound false alarms here: low-and-slow attacks (slowloris,
slowpost) look almost exactly like normal traffic, so a global threshold either floods the operator
with alerts or misses everything. Instead each attack class c gets its own threshold tau_c, set so
that at most `budget/K` of the *normal* out-of-fold rows exceed it (K = number of attack classes).
Decision rule (identical in AnomalyDetector):  flag class c  <=>  p_c >= tau_c ;  label = argmax p_c/tau_c.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import clone

from .model_evaluation import blocked_splits, metrics

TAU_MIN, TAU_MAX = 0.01, 0.95


def oof_proba(model, X, y, splits):
    X = X.values if hasattr(X, "values") else X
    y = np.asarray(y, dtype=object)
    P, done, classes = None, np.zeros(len(y), bool), None
    for tr, te in splits:
        m = clone(model).fit(X[tr], y[tr])
        if P is None:
            classes = list(m.classes_)
            P = np.zeros((len(y), len(classes)))
        P[te] = m.predict_proba(X[te])
        done[te] = True
    return P, done, classes


def apply_thresholds(P, classes, thresholds: dict, normal="normal"):
    """Vectorised decision rule. Returns an object array of predicted labels."""
    cls = np.array(classes, dtype=object)
    idx = [i for i, c in enumerate(classes) if c != normal]
    tau = np.array([thresholds[classes[i]] for i in idx])
    score = P[:, idx] / tau
    flagged = score.max(axis=1) >= 1.0
    pred = np.where(flagged, cls[np.array(idx)[score.argmax(axis=1)]], normal)
    return pred.astype(object)


def class_thresholds(P, y, classes, budget=0.10, normal="normal") -> dict:
    y = np.asarray(y, dtype=object)
    pn = P[y == normal]
    attack = [c for c in classes if c != normal]
    per_class_fp = budget / len(attack)
    thr = {}
    for c in attack:
        q = np.quantile(pn[:, classes.index(c)], 1.0 - per_class_fp)
        thr[c] = float(np.clip(q, TAU_MIN, TAU_MAX))
    return thr


def calibrate(model, X, y, window: int, budget: float = 0.10, normal="normal"):
    """Returns (thresholds, metrics_at_thresholds, oof_P, y_used, classes)."""
    P, done, classes = oof_proba(model, X, y, blocked_splits(len(y), 100, 5, embargo=window))
    y = np.asarray(y, dtype=object)[done]
    P = P[done]
    thr = class_thresholds(P, y, classes, budget, normal)
    res = metrics(y, apply_thresholds(P, classes, thr, normal))
    return thr, res, P, y, classes


def sensitivity_sweep(P, y, classes, thresholds, normal="normal", scales=(0.25, 0.5, 0.75, 1, 1.5, 2, 3)):
    """FAR / recall when all class thresholds are multiplied by `scale` (the UI 'sensitivity' knob)."""
    y = np.asarray(y, dtype=object)
    rows = []
    for s in scales:
        t = {c: float(np.clip(v * s, TAU_MIN, 0.99)) for c, v in thresholds.items()}
        m = metrics(y, apply_thresholds(P, classes, t, normal))
        rows.append({"scale": s, "false_alarm_rate": round(m["false_alarm_rate"], 4),
                     "binary_anomaly_recall": round(m["binary_anomaly_recall"], 4), "macro_f1": round(m["macro_f1"], 4)})
    return rows
