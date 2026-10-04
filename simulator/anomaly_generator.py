"""Random + manual anomaly scheduling."""
from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass

import numpy as np

from .simulation_config import ATTACK_TYPES, DURATION_RANGE, INTENSITY_RANGE, SimulationConfig


@dataclass
class Incident:
    id: int
    type: str
    zone: str
    intensity: float
    start: float
    end: float
    source: str  # "manual" | "random"

    def active(self, t: float) -> bool:
        return self.start <= t < self.end

    def to_dict(self):
        return asdict(self)


class AnomalyManager:
    def __init__(self, zone_ids: list[str], seed: int | None = None):
        self.zone_ids = zone_ids
        self.rng = np.random.default_rng(seed)
        self.incidents: list[Incident] = []
        self._ids = itertools.count(1)

    def inject(self, attack: str, zone: str | None, intensity: float, duration: float, t: float, source="manual") -> Incident:
        if attack not in ATTACK_TYPES:
            raise ValueError(f"unknown attack type '{attack}'. Valid: {list(ATTACK_TYPES)}")
        if zone is None:
            zone = self.rng.choice(ATTACK_TYPES[attack]["zones"])
        if zone not in self.zone_ids:
            raise ValueError(f"unknown zone '{zone}'. Valid: {self.zone_ids}")
        if not (INTENSITY_RANGE[0] <= intensity <= INTENSITY_RANGE[1]):
            raise ValueError(f"intensity must be in {INTENSITY_RANGE}")
        if not (DURATION_RANGE[0] <= duration <= DURATION_RANGE[1]):
            raise ValueError(f"duration must be in {DURATION_RANGE} seconds")
        inc = Incident(next(self._ids), attack, zone, float(intensity), t, t + duration, source)
        self.incidents.append(inc)
        return inc

    def maybe_random(self, cfg: SimulationConfig, t: float):
        """Poisson arrivals: P(new anomaly this tick) = dt / mean_gap. At most one active per zone."""
        if not cfg.random_anomalies:
            return None
        if self.rng.random() < cfg.tick_seconds / cfg.random_mean_gap_s:
            attack = str(self.rng.choice(list(ATTACK_TYPES)))
            zone = str(self.rng.choice(ATTACK_TYPES[attack]["zones"]))
            if self.active_for(zone, t) is None:
                return self.inject(attack, zone, float(self.rng.uniform(*cfg.random_intensity)),
                                   float(self.rng.integers(*cfg.random_duration_s)), t, "random")
        return None

    def active_for(self, zone: str, t: float) -> Incident | None:
        act = [i for i in self.incidents if i.zone == zone and i.active(t)]
        return max(act, key=lambda i: i.intensity) if act else None

    def stop_all(self, t: float, zone: str | None = None) -> int:
        n = 0
        for i in self.incidents:
            if i.active(t) and (zone is None or i.zone == zone):
                i.end = t
                n += 1
        return n

    def active(self, t: float):
        return [i for i in self.incidents if i.active(t)]

    def prune(self, t: float, keep=200):
        self.incidents = [i for i in self.incidents if i.end > t - 600][-keep:]
