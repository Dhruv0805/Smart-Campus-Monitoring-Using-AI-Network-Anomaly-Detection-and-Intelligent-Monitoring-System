"""Per-class traffic banks learned from dataset 1 so the simulator emits realistic SNMP counters.

A first version sampled per-class Gaussians in log space. That broke hard structure present in the
real data (e.g. udpOutDatagrams never drops below a 252/poll floor, many counters are exactly
constant) and the model - which learns those fingerprints - flagged 40% of simulated normal traffic.
Now each class keeps the real per-interval delta rows and the generator block-resamples them
(preserving temporal correlation and joint structure), then interpolates normal->attack by intensity.
"""
from __future__ import annotations

import joblib
import numpy as np

from engine import MODELS_DIR
from engine.data_preprocessor import load_snmp_dataset
from engine.feature_extraction import COUNTER_COLS, GAUGE_COLS, counters_to_deltas

PROFILE_PATH = MODELS_DIR / "traffic_profiles.pkl"


def build_profiles(save: bool = True) -> dict:
    df = load_snmp_dataset()
    D = counters_to_deltas(df)
    ok = ~D.isna().any(axis=1).to_numpy()
    banks = {}
    for cls in sorted(df["class"].unique()):
        m = (df["class"] == cls).to_numpy() & ok
        banks[cls] = {"deltas": D[m].to_numpy(dtype=float), "n": int(m.sum()),
                      "gauge": {g: float(df.loc[df["class"] == cls, g].median()) for g in GAUGE_COLS}}
    pivot = D[ok].min(axis=0).to_numpy(dtype=float)   # per-counter floor across all classes
    start = df[df["class"] == "normal"].iloc[0][COUNTER_COLS + GAUGE_COLS].astype(float).to_dict()
    bundle = {"columns": COUNTER_COLS, "banks": banks, "pivot": pivot, "start_counters": start}
    if save:
        MODELS_DIR.mkdir(exist_ok=True)
        joblib.dump(bundle, PROFILE_PATH)
    return bundle


def load_profiles() -> dict:
    if not PROFILE_PATH.exists():
        return build_profiles()
    b = joblib.load(PROFILE_PATH)
    return b if "banks" in b else build_profiles()


if __name__ == "__main__":
    for k, v in build_profiles()["banks"].items():
        print(k, v["n"])
