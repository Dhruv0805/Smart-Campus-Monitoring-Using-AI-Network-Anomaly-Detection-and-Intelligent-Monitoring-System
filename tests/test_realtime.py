"""Traffic -> graph -> alert -> log, end to end (simulator -> engine -> monitor service)."""
import pytest

from engine import MODEL_PATH
from simulator.simulation_config import SimulationConfig

pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run run_experiments.py first")


def make():
    from backend.services.monitor_service import MonitorService
    return MonitorService(SimulationConfig(seed=5, random_anomalies=False), autostart=False)


def test_normal_traffic_has_bounded_false_alarms():
    svc = make()
    for _ in range(300):
        svc.step()
    st = svc.stats()
    assert st["false_alarm_tick_rate"] < 0.10, st      # measured ~3% (README)


def test_manual_attack_flows_to_graph_alert_and_log():
    svc = make()
    for _ in range(40):
        svc.step()
    svc.sim.inject("udp-flood", intensity=1.0, duration=40, zone="services")
    for _ in range(40):
        svc.step()
    pts = svc.series(zone="services")["services"]
    attack_pts = [p for p in pts if p["truth"] == "udp-flood"]
    assert len(attack_pts) >= 30
    assert sum(p["is_anomaly"] for p in attack_pts) / len(attack_pts) > 0.6      # detected on the graph
    ev = [e for e in svc.get_events() if e["zone"] == "services"]
    assert ev and ev[-1]["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")  # alert + event log
    dev = {d["id"]: d for d in svc.devices()}
    assert dev["srv-web-01"]["status"] == "under attack"                          # device view


def test_traffic_returns_to_normal_after_stop():
    svc = make()
    for _ in range(30):
        svc.step()
    svc.sim.inject("tcp-syn", 1.0, 20, "services")
    for _ in range(25):
        svc.step()
    svc.sim.stop_anomalies()
    for _ in range(40):
        svc.step()
    last = [p for p in svc.series(zone="services")["services"]][-15:]
    assert sum(p["confirmed"] for p in last) <= 4
