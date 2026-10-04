"""Candidate models, small hyper-parameter search, final fit and model bundle export."""
from __future__ import annotations

import itertools
import time

import joblib
import numpy as np
from sklearn.ensemble import (ExtraTreesClassifier, HistGradientBoostingClassifier,
                              RandomForestClassifier)
from sklearn.tree import DecisionTreeClassifier

from .model_evaluation import blocked_splits, evaluate


def baseline_models(seed=0) -> dict:
    """Paper-1 style baselines. J48 ~ C4.5 (entropy tree); REPTree ~ reduced-error-pruned tree."""
    return {
        "RandomForest": RandomForestClassifier(100, random_state=seed, n_jobs=1),
        "J48 (C4.5-like)": DecisionTreeClassifier(criterion="entropy", min_samples_leaf=2, random_state=seed),
        "REPTree (pruned)": DecisionTreeClassifier(criterion="entropy", ccp_alpha=0.002, random_state=seed),
    }


def candidate_models(seed=0, balanced=True) -> dict:
    cw = "balanced" if balanced else None
    return {
        "DecisionTree": DecisionTreeClassifier(random_state=seed, class_weight=cw, min_samples_leaf=2),
        "RandomForest": RandomForestClassifier(200, random_state=seed, n_jobs=1, class_weight=cw),
        "ExtraTrees": ExtraTreesClassifier(300, random_state=seed, n_jobs=1, class_weight=cw),
        "GradientBoosting(Hist)": HistGradientBoostingClassifier(max_iter=150, random_state=seed, class_weight=cw),
    }


HGB_GRID = {"learning_rate": [0.05, 0.1], "max_depth": [None, 6], "max_iter": [100, 200],
            "l2_regularization": [0.0, 1.0]}


def tune_hgb(X, y, splits_fn, seed=0, grid=HGB_GRID, balanced=True):
    """Exhaustive search over a small grid, scored by macro-F1 under the supplied (honest) splits."""
    rows, best = [], (-1, None)
    keys = list(grid)
    for vals in itertools.product(*[grid[k] for k in keys]):
        params = dict(zip(keys, vals))
        t = time.time()
        m = HistGradientBoostingClassifier(random_state=seed, class_weight="balanced" if balanced else None, **params)
        res = evaluate(m, X, y, splits_fn())
        rows.append({**params, "macro_f1": round(res["macro_f1"], 4), "accuracy": round(res["accuracy"], 4),
                     "seconds": round(time.time() - t, 1)})
        if res["macro_f1"] > best[0]:
            best = (res["macro_f1"], params)
    return best[1], rows


def fit_final(model, X, y):
    return model.fit(X.values if hasattr(X, "values") else X, np.asarray(y, dtype=object))


def save_bundle(path, model, feature_names, classes, extra: dict):
    joblib.dump({"model": model, "feature_names": list(feature_names), "classes": list(classes), **extra}, path)


from sklearn.base import BaseEstimator, ClassifierMixin, clone as _clone  # noqa: E402

from .feature_selection import rank_features  # noqa: E402


class SelectKModel(BaseEstimator, ClassifierMixin):
    """Feature selection *inside* each CV fold (no label leakage from selecting on all data)."""

    def __init__(self, estimator=None, method="infogain", k=40, columns=None):
        self.estimator, self.method, self.k, self.columns = estimator, method, k, columns

    def fit(self, X, y):
        import pandas as pd
        df = pd.DataFrame(X, columns=self.columns)
        self.selected_ = list(rank_features(df, y, self.method).index[: self.k])
        self.idx_ = [list(self.columns).index(c) for c in self.selected_]
        self.model_ = _clone(self.estimator).fit(X[:, self.idx_], y)
        self.classes_ = self.model_.classes_
        return self

    def predict(self, X):
        return self.model_.predict(X[:, self.idx_])

    def predict_proba(self, X):
        return self.model_.predict_proba(X[:, self.idx_])
