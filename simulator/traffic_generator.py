"""Behaviour-driven SNMP counter generator for one monitored gateway.

Each tick: take the next row of a block-resampled real delta sequence for the active class
(normal or attack); for a partial-intensity attack interpolate normal -> attack in log space;
scale the traffic above each counter's floor by the zone load; accumulate into 32-bit cumulative
counters - exactly what an SNMP poller would read from a real device.
"""
from __future__ import annotations

import numpy as np

from engine.feature_extraction import COUNTER_COLS, GAUGE_COLS, WRAP

from .profiles import load_profiles

# Activity mix the zone's normal profile represents (documentation for the demo/README):
ZONE_ACTIVITY = {
    "student": ["DNS lookup", "web request", "LMS", "response"],
    "faculty": ["authentication", "LMS", "email", "web services"],
    "admin": ["authentication", "database query", "management system"],
    "labs": ["DNS", "web", "internal server"],
    "iot": ["periodic sensor data", "IoT gateway", "campus server"],
    "services": ["DNS", "web", "database", "LMS", "authentication"],
}
BLOCK = (6, 16)       # contiguous rows copied before jumping to a new random position


class _Cursor:
    def __init__(self, n, rng):
        self.n, self.rng, self.i, self.left = n, rng, 0, 0

    def next(self) -> int:
        if self.left <= 0 or self.i >= self.n:
            self.i = int(self.rng.integers(0, self.n))
            self.left = int(self.rng.integers(*BLOCK))
        j = self.i
        self.i += 1
        self.left -= 1
        return j


class CounterGenerator:
    def __init__(self, zone_id: str, load: float = 1.0, seed: int | None = None, profiles: dict | None = None):
        self.zone_id, self.load = zone_id, load
        self.rng = np.random.default_rng(seed)
        self.pb = profiles or load_profiles()
        self.banks = self.pb["banks"]
        self.pivot = self.pb["pivot"]
        self._cur = {c: _Cursor(len(b["deltas"]), self.rng) for c, b in self.banks.items()}
        start = self.pb["start_counters"]
        jitter = self.rng.uniform(0.2, 0.9)
        self.counters = {c: float(round(float(start[c]) * jitter)) for c in COUNTER_COLS}
        self.gauges = {g: float(start[g]) for g in GAUGE_COLS}

    def _row(self, cls: str) -> np.ndarray:
        return self.banks[cls]["deltas"][self._cur[cls].next()]

    def sample_delta(self, cls: str, intensity: float | None = None) -> np.ndarray:
        """intensity None -> pure class rows; else weight w = 0.35 + 0.65*intensity of the attack row."""
        if cls == "normal" or intensity is None:
            return self._row(cls)
        w = float(np.clip(0.35 + 0.65 * intensity, 0.0, 1.0))
        a, n = self._row(cls), self._row("normal")
        if w >= 0.999:
            return a
        return np.round(np.expm1((1 - w) * np.log1p(n) + w * np.log1p(a)))

    def step(self, cls: str = "normal", intensity: float | None = None, load_mod: float = 1.0) -> dict:
        delta = self.sample_delta(cls, intensity)
        scale = self.load * load_mod
        delta = np.round(self.pivot + (delta - self.pivot) * scale)   # scale only the traffic above the floor
        delta = np.clip(delta, 0, None)
        for i, c in enumerate(COUNTER_COLS):
            self.counters[c] = (self.counters[c] + delta[i]) % WRAP
        return {**{c: float(v) for c, v in self.counters.items()}, **self.gauges}
