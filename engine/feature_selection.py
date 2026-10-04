"""Feature ranking / selection: InfoGain (mutual information), ReliefF, model importance."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_selection import mutual_info_classif


def infogain(X: pd.DataFrame, y, random_state=0) -> pd.Series:
    """Mutual information == information gain for a discretised feature (Weka InfoGain analogue)."""
    s = mutual_info_classif(X.values, y, random_state=random_state)
    return pd.Series(s, index=X.columns).sort_values(ascending=False)


def relieff(X: pd.DataFrame, y, n_neighbors=10, sample_size=600, random_state=0) -> pd.Series:
    """Compact ReliefF (multi-class, Manhattan distance on min-max scaled features)."""
    rng = np.random.RandomState(random_state)
    A = X.values.astype(float)
    rngs = A.max(0) - A.min(0)
    rngs[rngs == 0] = 1.0
    A = (A - A.min(0)) / rngs
    y = np.asarray(y)
    classes, counts = np.unique(y, return_counts=True)
    prior = dict(zip(classes, counts / len(y)))
    idx = rng.choice(len(A), size=min(sample_size, len(A)), replace=False)
    w = np.zeros(A.shape[1])
    for i in idx:
        dist = np.abs(A - A[i]).sum(1)
        dist[i] = np.inf
        for c in classes:
            members = np.where(y == c)[0]
            members = members[members != i]
            if len(members) == 0:
                continue
            near = members[np.argsort(dist[members])[:n_neighbors]]
            diff = np.abs(A[near] - A[i]).mean(0)
            if c == y[i]:
                w -= diff
            else:
                w += prior[c] / (1 - prior[y[i]]) * diff
    return pd.Series(w / len(idx), index=X.columns).sort_values(ascending=False)


def model_importance(X: pd.DataFrame, y, random_state=0) -> pd.Series:
    m = ExtraTreesClassifier(300, random_state=random_state, n_jobs=1).fit(X.values, y)
    return pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False)


METHODS = {"infogain": infogain, "relieff": relieff, "importance": model_importance}


def rank_features(X: pd.DataFrame, y, method="infogain") -> pd.Series:
    return METHODS[method](X, y)


def select_top_k(X: pd.DataFrame, y, k: int, method="infogain") -> list[str]:
    return list(rank_features(X, y, method).index[:k])
