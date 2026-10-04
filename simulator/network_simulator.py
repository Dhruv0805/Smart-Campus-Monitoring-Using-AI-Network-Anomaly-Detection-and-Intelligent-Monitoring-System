"""Smart Campus network simulator: the replaceable data source.

Contract (what a real SNMP collector must also provide):
    tick() -> list[{"timestamp", "zone", "device", "counters": {33 cumulative SNMP counters + gauge}, ...}]
Ground-truth fields (`truth`, `incident_id`) are for evaluation/demo only; the engine never sees them.
"""
from __future__ import annotations

import threading

import numpy as np

from . import profiles  # noqa: F401
from .anomaly_generator import AnomalyManager
from .campus_entities import ZONES
from .simulation_config import SimulationConfig
from .traffic_generator import CounterGenerator


class NetworkSimulator:
    def __init__(self, config: SimulationConfig | None = None):
        self.cfg = config or SimulationConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.t = 0.0
        self.tick_count = 0
        self.lock = threading.RLock()
        self.gens = {z.id: CounterGenerator(z.id, z.load, seed=None if self.cfg.seed is None else self.cfg.seed + i)
                     for i, z in enumerate(ZONES)}
        self.anoms = AnomalyManager([z.id for z in ZONES], self.cfg.seed)

    # ---- control surface (used by Streamlit and Flask)
    def configure(self, **kw):
        with self.lock:
            for k, v in kw.items():
                if not hasattr(self.cfg, k):
                    raise ValueError(f"unknown setting '{k}'")
                setattr(self.cfg, k, v)
            return self.cfg.to_dict()

    def inject(self, attack: str, intensity: float = 0.8, duration: float = 10, zone: str | None = None):
        with self.lock:
            return self.anoms.inject(attack, zone, intensity, duration, self.t, "manual")

    def stop_anomalies(self, zone: str | None = None) -> int:
        with self.lock:
            return self.anoms.stop_all(self.t, zone)

    def active_incidents(self):
        with self.lock:
            return [i.to_dict() for i in self.anoms.active(self.t)]

    # ---- data source
    def tick(self) -> list[dict]:
        with self.lock:
            self.t += self.cfg.tick_seconds
            self.tick_count += 1
            self.anoms.maybe_random(self.cfg, self.t)
            if self.tick_count % 200 == 0:
                self.anoms.prune(self.t)
            out = []
            diurnal = 1.0 + 0.04 * np.sin(self.t / 90.0)
            for z in ZONES:
                inc = self.anoms.active_for(z.id, self.t)
                load_mod = diurnal * (1 + self.rng.uniform(-self.cfg.zone_jitter, self.cfg.zone_jitter))
                if inc:
                    counters = self.gens[z.id].step(inc.type, inc.intensity, load_mod)
                    truth, iid, src = inc.type, inc.id, inc.source
                else:
                    counters = self.gens[z.id].step("normal", None, load_mod)
                    truth, iid, src = "normal", None, None
                out.append({"timestamp": self.t, "zone": z.id, "device": z.gateway, "counters": counters,
                            "truth": truth, "incident_id": iid, "source": src})
            return out
