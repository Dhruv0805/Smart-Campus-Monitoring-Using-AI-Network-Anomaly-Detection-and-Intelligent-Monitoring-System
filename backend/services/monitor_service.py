"""Background monitoring loop shared by all API routes: simulator -> engine -> stores."""
from __future__ import annotations

import threading
import time
from collections import deque

from engine.pipeline import MonitoringPipeline
from simulator.campus_entities import DEVICES, ZONES, devices_dict, zones_dict
from simulator.network_simulator import NetworkSimulator
from simulator.simulation_config import ATTACK_TYPES, SimulationConfig


class MonitorService:
    def __init__(self, config: SimulationConfig | None = None, autostart: bool = True):
        self.sim = NetworkSimulator(config)
        self.engine = MonitoringPipeline()
        self.lock = threading.RLock()
        n = self.sim.cfg.history_points
        self.history = {z.id: deque(maxlen=n) for z in ZONES}
        self.events: deque = deque(maxlen=self.sim.cfg.max_events)
        self.latest: dict[str, dict] = {}
        self.counts = {"ticks": 0, "anomaly_ticks": 0, "alerts": 0, "false_alarm_ticks": 0, "missed_ticks": 0,
                       "correct_ticks": 0, "evaluated_ticks": 0}
        self._event_id = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if autostart:
            self.start()

    # ------------------------------------------------------------------ loop
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="monitor-loop")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            t0 = time.time()
            if self.sim.cfg.running:
                self.step()
            time.sleep(max(0.05, self.sim.cfg.tick_seconds - (time.time() - t0)))

    def step(self):
        """One poll of every zone. Public so tests can drive it deterministically."""
        with self.lock:
            for rec in self.sim.tick():
                res = self.engine.process(rec["counters"], zone=rec["zone"], timestamp=rec["timestamp"])
                res.update(truth=rec["truth"], incident_id=rec["incident_id"], device=rec["device"], wall_time=time.time())
                self._record(res)

    def _record(self, r: dict):
        z = r["zone"]
        self.history[z].append(r)
        self.latest[z] = r
        if r["warming_up"]:
            return
        c = self.counts
        c["ticks"] += 1
        c["anomaly_ticks"] += int(r["is_anomaly"])
        c["evaluated_ticks"] += 1
        truth_anom = r["truth"] != "normal"
        c["false_alarm_ticks"] += int(r["is_anomaly"] and not truth_anom)
        c["missed_ticks"] += int((not r["is_anomaly"]) and truth_anom)
        c["correct_ticks"] += int(r["prediction"] == r["truth"])
        if r["new_incident"]:
            self._event_id += 1
            c["alerts"] += 1
            self.events.appendleft({"id": self._event_id, "timestamp": r["timestamp"], "wall_time": r["wall_time"],
                                    "zone": z, "device": r["device"], "attack": r["prediction"],
                                    "attack_label": ATTACK_TYPES.get(r["prediction"], {}).get("label", r["prediction"]),
                                    "confidence": r["confidence"], "risk_score": r["risk"]["score"],
                                    "risk_level": r["risk"]["level"], "truth": r["truth"],
                                    "correct": r["prediction"] == r["truth"]})

    # ------------------------------------------------------------------ views
    def snapshot(self) -> dict:
        with self.lock:
            zones = []
            for z in zones_dict():
                lr = self.latest.get(z["id"])
                zones.append({**z, "latest": lr})
            levels = ["NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
            worst = max((levels.index(l["risk"]["level"]) for l in self.latest.values() if l), default=0)
            active = [i for i in self.sim.active_incidents()]
            confirmed_now = [l for l in self.latest.values() if l and l["confirmed"]]
            return {"system": "ONLINE" if self.sim.cfg.running else "PAUSED", "sim_time": self.sim.t,
                    "overall_risk": levels[worst], "zones": zones, "active_incidents": active,
                    "anomalies_now": len(confirmed_now), "alerts_total": self.counts["alerts"],
                    "config": self.sim.cfg.to_dict()}

    def series(self, since: float = 0.0, zone: str | None = None, limit: int = 300) -> dict:
        with self.lock:
            out = {}
            for zid, h in self.history.items():
                if zone and zid != zone:
                    continue
                pts = [p for p in h if p["timestamp"] > since and not p["warming_up"]][-limit:]
                out[zid] = [{"t": p["timestamp"], "packet_rate": p["metrics"]["packet_rate"], "byte_rate": p["metrics"]["byte_rate"],
                             "tcp_rate": p["metrics"]["tcp_rate"], "udp_rate": p["metrics"]["udp_rate"],
                             "icmp_rate": p["metrics"]["icmp_rate"], "risk": p["risk"]["score"], "level": p["risk"]["level"],
                             "is_anomaly": p["is_anomaly"], "confirmed": p["confirmed"], "prediction": p["prediction"],
                             "confidence": p["confidence"], "truth": p["truth"]} for p in pts]
            return out

    def get_events(self, limit=100, zone=None):
        with self.lock:
            ev = [e for e in self.events if not zone or e["zone"] == zone]
            return ev[:limit]

    def devices(self) -> list[dict]:
        with self.lock:
            snap = self.latest
            out = []
            for d in devices_dict():
                lr = snap.get(d["zone"])
                level = lr["risk"]["level"] if lr else "NORMAL"
                attack = lr["prediction"] if lr and lr["confirmed"] else None
                out.append({**d, "status": "under attack" if attack else "healthy", "risk_level": level if attack else "NORMAL",
                            "attack": attack})
            return out

    def stats(self) -> dict:
        with self.lock:
            c = dict(self.counts)
            ev = max(c["evaluated_ticks"], 1)
            by_type: dict[str, int] = {}
            for e in self.events:
                by_type[e["attack"]] = by_type.get(e["attack"], 0) + 1
            return {**c, "tick_accuracy": round(c["correct_ticks"] / ev, 4),
                    "false_alarm_tick_rate": round(c["false_alarm_ticks"] / ev, 4),
                    "alerts_by_type": by_type, "devices": len(DEVICES)}

    # ------------------------------------------------------------------ control
    def reset(self):
        with self.lock:
            cfg = self.sim.cfg
            self.sim = NetworkSimulator(cfg)
            self.engine.reset()
            for h in self.history.values():
                h.clear()
            self.events.clear()
            self.latest.clear()
            for k in self.counts:
                self.counts[k] = 0
            self._event_id = 0

    def update_engine_settings(self, threshold_scale=None, smoothing=None):
        with self.lock:
            if threshold_scale is not None:
                self.engine.detector.threshold_scale = float(threshold_scale)
            if smoothing is not None:
                self.engine.smoothing = float(smoothing)
            return self.engine_settings()

    def engine_settings(self):
        return {"threshold_scale": self.engine.detector.threshold_scale, "thresholds": self.engine.detector.thresholds, "smoothing": self.engine.smoothing,
                "window": self.engine.window, "model": self.engine.bundle.get("model_name"),
                "classes": self.engine.detector.classes}
