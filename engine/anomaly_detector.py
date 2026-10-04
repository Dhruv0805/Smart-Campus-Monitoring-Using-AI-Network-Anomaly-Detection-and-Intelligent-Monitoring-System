"""Real-time prediction on one feature vector."""
from __future__ import annotations

import numpy as np

from .model_loader import load_bundle


class AnomalyDetector:
    """Per-class thresholds (calibrated, see calibration.py) scaled by a user-facing sensitivity knob.
    `threshold_scale` < 1 -> more sensitive (more alerts); > 1 -> stricter."""

    def __init__(self, bundle: dict | None = None, threshold_scale: float = 1.0):
        self.bundle = bundle or load_bundle()
        self.model = self.bundle["model"]
        self.classes = list(self.bundle["classes"])
        self.normal_label = self.bundle.get("normal_label", "normal")
        self.normal_idx = self.classes.index(self.normal_label)
        self.base_thresholds = dict(self.bundle.get("thresholds") or {c: 0.5 for c in self.classes if c != self.normal_label})
        self.threshold_scale = float(threshold_scale)
        self.feature_names = self.bundle["feature_names"]

    @property
    def thresholds(self) -> dict:
        return {c: float(np.clip(t * self.threshold_scale, 0.01, 0.99)) for c, t in self.base_thresholds.items()}

    def predict_proba(self, vec: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(np.asarray(vec, dtype=float).reshape(1, -1))[0]

    def decide(self, proba: np.ndarray) -> dict:
        thr = self.thresholds
        best_c, best_s = None, 0.0
        for i, c in enumerate(self.classes):
            if i == self.normal_idx:
                continue
            s = proba[i] / thr[c]
            if s > best_s:
                best_c, best_s = c, s
        is_anomaly = best_s >= 1.0
        p_anom = float(1.0 - proba[self.normal_idx])
        if is_anomaly:
            label, confidence = best_c, p_anom   # P(attack); per-class probabilities are in `probabilities`
        else:
            label, confidence = self.normal_label, float(proba[self.normal_idx])
        return {"prediction": label, "is_anomaly": bool(is_anomaly), "confidence": round(confidence, 4),
                "p_anomaly": round(p_anom, 4), "score": round(float(best_s), 3),
                "probabilities": {c: round(float(p), 4) for c, p in zip(self.classes, proba)}}

    def predict(self, vec: np.ndarray) -> dict:
        return self.decide(self.predict_proba(vec))
