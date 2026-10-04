"""Load trained model bundles from models/ (cached; the app never retrains at start-up)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib

from . import MODEL_PATH, MODELS_DIR


@lru_cache(maxsize=4)
def load_bundle(path: str | Path = MODEL_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run `python run_experiments.py` first.")
    bundle = joblib.load(path)
    for key in ("model", "feature_names", "classes"):
        if key not in bundle:
            raise ValueError(f"Invalid model bundle: missing '{key}'")
    return bundle


def load_local_bundle() -> dict:
    return load_bundle(MODELS_DIR / "local_signature_model.pkl")
