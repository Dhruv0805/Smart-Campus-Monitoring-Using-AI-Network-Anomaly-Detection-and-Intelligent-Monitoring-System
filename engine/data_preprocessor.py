"""Load, validate and clean the raw datasets. Nothing here trains a model."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import RAW_DIR

LABEL = "class"
LOCAL_FILES = ["local_A.csv", "local_B.csv", "local_C.csv", "local_D.csv"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and illegal characters (the raw file has 'tcp?ActiveOpens')."""
    df = df.copy()
    df.columns = [c.strip().replace("?", "") for c in df.columns]
    return df


def load_snmp_dataset(path=None) -> pd.DataFrame:
    """Dataset 1 (all_data.csv): cumulative SNMP-MIB counters, 8 classes, time-ordered."""
    df = normalize_columns(pd.read_csv(path or RAW_DIR / "all_data.csv"))
    df[LABEL] = df[LABEL].astype(str).str.strip()
    return df


def load_local_dataset(files=None) -> pd.DataFrame:
    """Dataset 2 (local_A..D): per-interval interface statistics; adds a `source` column."""
    frames = []
    for f in files or LOCAL_FILES:
        d = normalize_columns(pd.read_csv(RAW_DIR / f))
        d[LABEL] = d[LABEL].astype(str).str.strip()
        d["source"] = f.split("_")[1].split(".")[0]
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def validate_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


def audit(df: pd.DataFrame, label: str = LABEL) -> dict:
    """Dataset-quality report (missing, duplicates, constants, class balance, invalid values)."""
    feats = df.drop(columns=[c for c in (label, "source") if c in df.columns])
    num = feats.select_dtypes(include=[np.number])
    counts = df[label].value_counts()
    return {
        "rows": int(len(df)),
        "features": int(feats.shape[1]),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(feats.duplicated().sum()),
        "constant_features": [c for c in feats if feats[c].nunique(dropna=True) <= 1],
        "negative_values": int((num < 0).sum().sum()),
        "non_numeric_features": [c for c in feats if c not in num.columns],
        "inf_values": int(np.isinf(num.to_numpy(dtype=float)).sum()),
        "class_counts": {k: int(v) for k, v in counts.items()},
        "imbalance_ratio": float(counts.max() / counts.min()),
    }


def clean(df: pd.DataFrame, label: str = LABEL, drop_constant: bool = True, drop_duplicates=False):
    """Return (clean_df, report). Never reorders rows (order matters for time-aware CV)."""
    report = {"before_rows": len(df)}
    df = df.replace([np.inf, -np.inf], np.nan)
    feats = [c for c in df.columns if c not in (label, "source")]
    # Impute any missing numeric value by the column median (none expected in these datasets).
    n_missing = int(df[feats].isna().sum().sum())
    if n_missing:
        df[feats] = df[feats].fillna(df[feats].median())
    report["imputed_cells"] = n_missing
    if drop_duplicates:
        before = len(df)
        df = df.drop_duplicates(subset=feats).reset_index(drop=True)
        report["duplicates_removed"] = before - len(df)
    const = [c for c in feats if df[c].nunique() <= 1]
    if drop_constant and const:
        df = df.drop(columns=const)
    report["constant_removed"] = const
    report["after_rows"] = len(df)
    return df, report
