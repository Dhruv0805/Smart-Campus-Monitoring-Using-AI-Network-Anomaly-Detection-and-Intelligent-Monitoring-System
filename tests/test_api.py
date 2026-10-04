import pytest

from engine import MODEL_PATH
from engine.feature_extraction import COUNTER_COLS

pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run run_experiments.py first")


@pytest.fixture()
def env():
    from backend.app import create_app
    from backend.services.monitor_service import MonitorService
    from simulator.simulation_config import SimulationConfig
    svc = MonitorService(SimulationConfig(seed=11, random_anomalies=False), autostart=False)
    for _ in range(15):
        svc.step()
    return create_app(svc).test_client(), svc


def test_health_and_state(env):
    c, _ = env
    assert c.get("/api/health").get_json()["status"] == "ok"
    s = c.get("/api/state").get_json()
    assert s["system"] == "ONLINE" and len(s["zones"]) == 6 and "stats" in s


def test_series_events_devices_zones(env):
    c, _ = env
    s = c.get("/api/series?limit=5&zone=iot").get_json()
    assert list(s) == ["iot"] and len(s["iot"]) == 5 and "packet_rate" in s["iot"][0]
    assert c.get("/api/series?zone=bad").status_code == 400
    assert c.get("/api/series?limit=abc").status_code == 400
    assert isinstance(c.get("/api/events").get_json(), list)
    assert len(c.get("/api/devices").get_json()) == 23
    assert len(c.get("/api/zones").get_json()) == 6
    assert "tcp-syn" in c.get("/api/attack-types").get_json()["types"]


def test_inject_validation(env):
    c, _ = env
    assert c.post("/api/simulation/inject", json={"attack": "bogus"}).status_code == 400
    assert c.post("/api/simulation/inject", json={"attack": "tcp-syn", "intensity": 7}).status_code == 400
    assert c.post("/api/simulation/inject", json={"attack": "tcp-syn", "duration": "x"}).status_code == 400
    assert c.post("/api/simulation/inject", json={"attack": "tcp-syn", "zone": "mars"}).status_code == 400
    r = c.post("/api/simulation/inject", json={"attack": "tcp-syn", "intensity": 0.9, "duration": 20, "zone": "services"})
    assert r.status_code == 201 and r.get_json()["zone"] == "services"
    assert len(c.get("/api/simulation").get_json()["active_incidents"]) == 1
    assert c.post("/api/simulation/stop", json={}).get_json()["stopped"] == 1


def test_config_and_settings(env):
    c, _ = env
    assert c.post("/api/simulation/config", json={"running": "yes"}).status_code == 400
    assert c.post("/api/simulation/config", json={"random_anomalies": True, "random_mean_gap_s": 30}).get_json()["random_anomalies"] is True
    assert c.post("/api/settings", json={"threshold_scale": 20}).status_code == 400
    assert c.post("/api/settings", json={"threshold_scale": 0.5, "smoothing": 0.3}).get_json()["threshold_scale"] == 0.5


def test_detect_endpoint_validation(env):
    c, _ = env
    good = {k: 1000.0 for k in COUNTER_COLS}
    assert c.post("/api/detect", json={"counters": good}).get_json()["warming_up"] is True
    assert c.post("/api/detect", json={"counters": {"x": 1}}).status_code == 422
    assert c.post("/api/detect", data="garbage", content_type="text/plain").status_code == 422


def test_analytics_and_reset(env):
    c, svc = env
    a = c.get("/api/analytics").get_json()
    assert "live" in a and "comparison" in a
    assert c.post("/api/simulation/reset").status_code == 200
    assert svc.stats()["ticks"] == 0
    assert c.get("/api/nope").status_code == 404
