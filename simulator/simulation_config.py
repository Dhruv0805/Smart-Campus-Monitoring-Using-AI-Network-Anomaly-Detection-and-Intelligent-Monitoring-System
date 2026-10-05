"""Simulator configuration and the attack catalogue (names match the trained model's labels)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

ATTACK_TYPES = {
    "tcp-syn": {"label": "TCP-SYN flood", "desc": "Unusually high number of connection attempts", "zones": ["services", "faculty", "admin"]},
    "udp-flood": {"label": "UDP flood", "desc": "Very high UDP packet traffic", "zones": ["iot", "services", "labs"]},
    "icmp-echo": {"label": "ICMP echo anomaly", "desc": "Excessive ICMP echo requests", "zones": ["labs", "student", "services"]},
    "httpFlood": {"label": "HTTP flood", "desc": "High number of HTTP requests", "zones": ["services", "faculty"]},
    "slowloris": {"label": "Slowloris", "desc": "Many long-running half-open HTTP connections", "zones": ["services", "faculty"]},
    "slowpost": {"label": "SlowPOST", "desc": "Slow POST-style request bodies", "zones": ["services", "admin"]},
    "bruteForce": {"label": "Brute force", "desc": "Repeated authentication attempts", "zones": ["admin", "services", "faculty"]},
}


@dataclass
class SimulationConfig:
    tick_seconds: float = 1.0          # simulated seconds per poll (also the wall-clock sleep when live)
    running: bool = True
    random_anomalies: bool = True
    random_mean_gap_s: float = 120.0    # mean seconds between random anomalies (Poisson process)
    random_duration_s: tuple = (20, 45)
    random_intensity: tuple = (0.7, 1.0)
    zone_jitter: float = 0.04          # +-4% per-zone traffic load jitter
    seed: int | None = None
    history_points: int = 600          # per-zone points kept for charts
    max_events: int = 500

    def to_dict(self):
        return asdict(self)


INTENSITY_RANGE = (0.1, 1.0)
DURATION_RANGE = (3, 120)
