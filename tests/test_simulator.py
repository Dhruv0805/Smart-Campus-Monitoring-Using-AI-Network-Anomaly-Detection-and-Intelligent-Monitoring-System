import numpy as np
import pytest

from engine.feature_extraction import COUNTER_COLS, WRAP
from simulator.campus_entities import DEVICES, ZONES
from simulator.network_simulator import NetworkSimulator
from simulator.simulation_config import ATTACK_TYPES, SimulationConfig


def sim(**kw):
    return NetworkSimulator(SimulationConfig(seed=7, random_anomalies=False, **kw))


def test_record_schema_and_zones():
    s = sim()
    recs = s.tick()
    assert [r["zone"] for r in recs] == [z.id for z in ZONES]
    for r in recs:
        assert set(COUNTER_COLS) <= set(r["counters"])
        assert all(0 <= v < WRAP for c, v in r["counters"].items() if c in COUNTER_COLS)
        assert r["truth"] == "normal"


def test_counters_are_cumulative_modulo_wrap():
    s = sim()
    prev = s.tick()[0]["counters"]
    for _ in range(50):
        cur = s.tick()[0]["counters"]
        for c in COUNTER_COLS:
            assert (cur[c] - prev[c]) % WRAP < WRAP / 2, c      # never goes "backwards" except by wrapping
        prev = cur


def test_manual_injection_marks_ground_truth_and_expires():
    s = sim()
    for _ in range(3):
        s.tick()
    inc = s.inject("tcp-syn", intensity=0.9, duration=5, zone="services")
    hit = [r for r in s.tick() if r["zone"] == "services"][0]
    assert hit["truth"] == "tcp-syn" and hit["incident_id"] == inc.id and hit["source"] == "manual"
    for _ in range(6):
        recs = s.tick()
    assert [r for r in recs if r["zone"] == "services"][0]["truth"] == "normal"


def test_attack_raises_packet_rate_vs_normal():
    s = sim()
    for _ in range(5):
        s.tick()
    s.inject("udp-flood", 1.0, 40, "iot")
    iot_prev, others = None, []
    deltas_attack, deltas_norm = [], []
    for _ in range(30):
        recs = {r["zone"]: r for r in s.tick()}
        if iot_prev:
            deltas_attack.append(recs["iot"]["counters"]["ipInReceives"] - iot_prev["iot"]["counters"]["ipInReceives"])
            deltas_norm.append(recs["labs"]["counters"]["ipInReceives"] - iot_prev["labs"]["counters"]["ipInReceives"])
        iot_prev = recs
    d = [(a % WRAP) for a in deltas_attack]
    n = [(a % WRAP) for a in deltas_norm]
    assert np.median(d) > 1.2 * np.median(n)


@pytest.mark.parametrize("bad", [dict(attack="nope"), dict(attack="tcp-syn", intensity=5), dict(attack="tcp-syn", duration=0),
                                 dict(attack="tcp-syn", zone="moon")])
def test_injection_validation(bad):
    with pytest.raises(ValueError):
        sim().inject(**bad)


def test_random_anomalies_occur_and_can_be_disabled():
    s = NetworkSimulator(SimulationConfig(seed=3, random_anomalies=True, random_mean_gap_s=5))
    for _ in range(300):
        s.tick()
    assert any(i.source == "random" for i in s.anoms.incidents)
    s2 = sim()
    for _ in range(300):
        s2.tick()
    assert not s2.anoms.incidents


def test_catalogue_matches_model_labels():
    from engine.data_preprocessor import load_snmp_dataset
    labels = set(load_snmp_dataset()["class"]) - {"normal"}
    assert set(ATTACK_TYPES) == labels


def test_inventory_covers_all_zones():
    assert {d.zone for d in DEVICES} == {z.id for z in ZONES}
