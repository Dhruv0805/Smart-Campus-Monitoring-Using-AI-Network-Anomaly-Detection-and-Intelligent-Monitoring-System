"""Convert a detection into a 0-100 risk score and NORMAL/LOW/MEDIUM/HIGH/CRITICAL level.

score = 100 * strength * (0.15 + 0.35*severity(class) + 0.25*intensity + 0.25*persistence)
  severity    - fixed weight per attack class (flood-type attacks are more disruptive)
  intensity   - how far the window-mean traffic features are from the normal baseline (robust z)
  persistence - consecutive anomalous detections (decays when traffic looks normal again)
Predicted-normal ticks are capped at 20 so they can never exceed LOW.
"""
from __future__ import annotations

import numpy as np

LEVELS = [(15, "NORMAL"), (35, "LOW"), (55, "MEDIUM"), (75, "HIGH"), (101, "CRITICAL")]
SEVERITY = {"udp-flood": 0.95, "httpFlood": 0.90, "tcp-syn": 0.85, "bruteForce": 0.80,
            "slowloris": 0.70, "icmp-echo": 0.65, "slowpost": 0.60}
KEY_FEATURES = ["ipInReceives_m5", "ifInOctets11_m5", "tcpInSegs_m5", "udpInDatagrams_m5",
                "icmpInMsgs_m5", "ipForwDatagrams_m5"]


def level_for(score: float) -> str:
    for bound, name in LEVELS:
        if score < bound:
            return name
    return "CRITICAL"


class RiskScorer:
    """One instance per monitored zone (keeps the persistence counter)."""

    def __init__(self, bundle: dict):
        self.names = list(bundle["feature_names"])
        self.med = np.array([bundle["normal_median"][n] for n in self.names])
        self.mad = np.array([bundle["normal_mad"][n] for n in self.names])
        self.key_idx = [self.names.index(f) for f in KEY_FEATURES if f in self.names]
        self.streak = 0.0

    def reset(self):
        self.streak = 0.0

    def intensity(self, vec: np.ndarray) -> float:
        z = np.abs((vec[self.key_idx] - self.med[self.key_idx]) / self.mad[self.key_idx])
        return float(np.clip(np.mean(np.minimum(z, 12.0)) / 6.0, 0.0, 1.0))

    def score(self, detection: dict, vec: np.ndarray) -> dict:
        inten = self.intensity(vec)
        self.streak = self.streak + 1 if detection["is_anomaly"] else max(self.streak - 1, 0)
        persistence = min(self.streak / 8.0, 1.0)
        sev = SEVERITY.get(detection["prediction"], 0.5)
        # strength: how far past its calibrated threshold the winning class is (saturates at 3x)
        p = float(np.clip(0.4 + 0.2 * detection.get("score", 1.0), 0.0, 1.0)) if detection["is_anomaly"] else detection["p_anomaly"]
        if detection["is_anomaly"]:
            s = 100 * p * (0.15 + 0.35 * sev + 0.25 * inten + 0.25 * persistence)
        else:
            s = min(20.0, 100 * p * 0.5)
        s = float(np.clip(s, 0, 100))
        return {"score": round(s, 1), "level": level_for(s), "intensity": round(inten, 3),
                "persistence": round(persistence, 3), "severity": sev if detection["is_anomaly"] else 0.0}
