"""Metrics and validation splitters.

Two protocols are provided:
* stratified random k-fold  -> what the baseline paper uses (optimistic on time-ordered counters)
* blocked CV with embargo   -> contiguous blocks, rows after a test block are removed from training
                               so overlapping windows cannot leak (honest estimate)
* leave-one-source-out      -> for the local_A..D captures
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)
from sklearn.model_selection import StratifiedKFold


def blocked_splits(n: int, block: int = 100, k: int = 5, embargo: int = 0, seed: int = 0):
    g = np.arange(n) // block
    fold = np.random.RandomState(seed).permutation(g.max() + 1)[g] % k
    for f in range(k):
        te = np.where(fold == f)[0]
        tr_mask = fold != f
        if embargo:
            bad = np.zeros(n, bool)
            for i in te:
                bad[i + 1:i + 1 + embargo] = True
            tr_mask &= ~bad
        yield np.where(tr_mask)[0], te


def random_splits(y, k: int = 10, seed: int = 0):
    yield from StratifiedKFold(k, shuffle=True, random_state=seed).split(np.zeros(len(y)), y)


def group_splits(groups):
    groups = np.asarray(groups)
    for g in np.unique(groups):
        yield np.where(groups != g)[0], np.where(groups == g)[0]


def cross_predict(model, X, y, splits):
    X = X.values if hasattr(X, "values") else X
    y = np.asarray(y, dtype=object)
    pred = np.empty(len(y), dtype=object)
    done = np.zeros(len(y), bool)
    for tr, te in splits:
        m = clone(model).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
        done[te] = True
    return pred, done


def metrics(y_true, y_pred, labels=None, normal_label="normal") -> dict:
    y_true, y_pred = np.asarray(y_true, dtype=object), np.asarray(y_pred, dtype=object)
    labels = labels or sorted(set(y_true) | set(y_pred))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    yb, pb = y_true != normal_label, y_pred != normal_label
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(p.mean()), "macro_recall": float(r.mean()),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "binary_anomaly_f1": float(f1_score(yb, pb, zero_division=0)),
        "binary_anomaly_recall": float((pb & yb).sum() / max(yb.sum(), 1)),
        "false_alarm_rate": float((pb & ~yb).sum() / max((~yb).sum(), 1)),
        "per_class": {l: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
                          "support": int(s[i])} for i, l in enumerate(labels)},
        "labels": list(labels),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def evaluate(model, X, y, splits) -> dict:
    pred, done = cross_predict(model, X, y, list(splits))
    return metrics(np.asarray(y, dtype=object)[done], pred[done])


def summary_row(name: str, res: dict, **extra) -> dict:
    keys = ["accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1",
            "binary_anomaly_f1", "binary_anomaly_recall", "false_alarm_rate"]
    return {"experiment": name, **extra, **{k: round(res[k], 4) for k in keys}}
