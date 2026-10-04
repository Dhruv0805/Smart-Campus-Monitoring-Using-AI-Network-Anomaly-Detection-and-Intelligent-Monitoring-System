"""End-to-end engine: raw counter record -> validated -> features -> model -> risk -> standard output.

The same object is used by Streamlit and Flask, so both UIs show identical results.
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from .anomaly_detector import AnomalyDetector
from .feature_extraction import COUNTER_COLS, GAUGE_COLS, StreamingFeatureExtractor
from .model_loader import load_bundle
from .risk_scoring import RiskScorer

REQUIRED_FIELDS = COUNTER_COLS


def validate_record(record: dict) -> dict:
    """Reject malformed records before they reach the model. Returns the clean counter dict."""
    if not isinstance(record, dict):
        raise ValueError("record must be a JSON object of counter name -> number")
    counters = record.get("counters", record)
    missing = [c for c in REQUIRED_FIELDS if c not in counters]
    if missing:
        raise ValueError(f"missing counters: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    clean = {}
    for c in REQUIRED_FIELDS + GAUGE_COLS:
        if c not in counters:
            clean[c] = 0.0
            continue
        v = counters[c]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"counter '{c}' must be a finite non-negative number, got {v!r}")
        clean[c] = float(v)
    return clean


class _ZoneState:
    def __init__(self, bundle, window):
        self.extractor = StreamingFeatureExtractor(window)
        self.risk = RiskScorer(bundle)
        self.prev_proba: np.ndarray | None = None
        self.recent = deque(maxlen=3)       # last anomaly flags -> confirmation rule
        self.open_type: str | None = None   # currently open incident type
        self.ticks = 0


class MonitoringPipeline:
    def __init__(self, bundle: dict | None = None, smoothing: float = 0.5, threshold_scale: float = 1.0):
        self.bundle = bundle or load_bundle()
        self.detector = AnomalyDetector(self.bundle, threshold_scale)
        self.window = self.bundle.get("window", 5)
        self.smoothing = smoothing  # weight of the previous probability vector (0 = off)
        self.zones: dict[str, _ZoneState] = {}

    def reset(self, zone: str | None = None):
        if zone is None:
            self.zones.clear()
        else:
            self.zones.pop(zone, None)

    def _state(self, zone):
        if zone not in self.zones:
            self.zones[zone] = _ZoneState(self.bundle, self.window)
        return self.zones[zone]

    def process(self, record: dict, zone: str = "default", timestamp: float | None = None) -> dict:
        counters = validate_record(record)
        st = self._state(zone)
        vec, delta = st.extractor.push(counters)
        out = {"timestamp": timestamp, "zone": zone, "warming_up": vec is None}
        if vec is None:
            out.update(prediction="normal", is_anomaly=False, confidence=0.0, p_anomaly=0.0, confirmed=False,
                       new_incident=False, risk={"score": 0.0, "level": "NORMAL", "intensity": 0, "persistence": 0, "severity": 0},
                       metrics={}, probabilities={})
            return out
        st.ticks += 1
        proba = self.detector.predict_proba(vec)
        if self.smoothing and st.prev_proba is not None:
            proba = self.smoothing * st.prev_proba + (1 - self.smoothing) * proba
        st.prev_proba = proba
        det = self.detector.decide(proba)
        risk = st.risk.score(det, vec)
        st.recent.append(det["is_anomaly"])
        settled = st.ticks > self.window + 2        # rolling window must be full before alerting
        confirmed = settled and sum(st.recent) >= 2 and det["is_anomaly"]
        new_incident = bool(confirmed and st.open_type != det["prediction"])
        if confirmed:
            st.open_type = det["prediction"]
        elif not any(st.recent):
            st.open_type = None
        out.update(det, risk=risk, confirmed=bool(confirmed), new_incident=new_incident, metrics={
            "packet_rate": delta["ipInReceives"], "byte_rate": delta["ifInOctets11"],
            "tcp_rate": delta["tcpInSegs"], "udp_rate": delta["udpInDatagrams"],
            "icmp_rate": delta["icmpInMsgs"], "conn_rate": delta["tcpPassiveOpens"]})
        return out
