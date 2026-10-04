"""REST API. Every request body is validated before it reaches the engine/simulator."""
from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request

from engine import RESULTS_DIR
from engine.pipeline import MonitoringPipeline
from simulator.campus_entities import ZONES, zones_dict
from simulator.simulation_config import ATTACK_TYPES, DURATION_RANGE, INTENSITY_RANGE

bp = Blueprint("api", __name__, url_prefix="/api")
ZONE_IDS = [z.id for z in ZONES]


def svc():
    return current_app.config["MONITOR"]


def err(msg, code=400):
    return jsonify({"error": msg}), code


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def num(data, key, lo, hi, default=None):
    v = data.get(key, default)
    if v is None:
        raise ValueError(f"'{key}' is required")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"'{key}' must be a number")
    if not (lo <= v <= hi):
        raise ValueError(f"'{key}' must be between {lo} and {hi}")
    return float(v)


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "model": svc().engine_settings()["model"], "running": svc().sim.cfg.running})


@bp.get("/state")
def state():
    return jsonify({**svc().snapshot(), "stats": svc().stats()})


@bp.get("/series")
def series():
    try:
        since = float(request.args.get("since", 0))
        limit = max(1, min(int(request.args.get("limit", 300)), 600))
    except ValueError:
        return err("since/limit must be numeric")
    zone = request.args.get("zone")
    if zone and zone not in ZONE_IDS:
        return err(f"unknown zone '{zone}'")
    return jsonify(svc().series(since, zone, limit))


@bp.get("/events")
def events():
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
    except ValueError:
        return err("limit must be an integer")
    return jsonify(svc().get_events(limit, request.args.get("zone")))


@bp.get("/devices")
def devices():
    return jsonify(svc().devices())


@bp.get("/zones")
def zones():
    return jsonify(zones_dict())


@bp.get("/attack-types")
def attack_types():
    return jsonify({"types": ATTACK_TYPES, "intensity_range": INTENSITY_RANGE, "duration_range": DURATION_RANGE})


@bp.post("/simulation/inject")
def inject():
    d = body()
    attack = d.get("attack")
    if attack not in ATTACK_TYPES:
        return err(f"'attack' must be one of {list(ATTACK_TYPES)}")
    zone = d.get("zone") or None
    if zone and zone not in ZONE_IDS:
        return err(f"'zone' must be one of {ZONE_IDS}")
    try:
        inten = num(d, "intensity", *INTENSITY_RANGE, default=0.8)
        dur = num(d, "duration", *DURATION_RANGE, default=10)
    except ValueError as e:
        return err(str(e))
    inc = svc().sim.inject(attack, inten, dur, zone)
    return jsonify(inc.to_dict()), 201


@bp.post("/simulation/stop")
def stop():
    zone = body().get("zone") or None
    if zone and zone not in ZONE_IDS:
        return err(f"'zone' must be one of {ZONE_IDS}")
    return jsonify({"stopped": svc().sim.stop_anomalies(zone)})


@bp.post("/simulation/config")
def config():
    d = body()
    kw = {}
    for k in ("running", "random_anomalies"):
        if k in d:
            if not isinstance(d[k], bool):
                return err(f"'{k}' must be boolean")
            kw[k] = d[k]
    try:
        if "random_mean_gap_s" in d:
            kw["random_mean_gap_s"] = num(d, "random_mean_gap_s", 5, 600)
        if "tick_seconds" in d:
            kw["tick_seconds"] = num(d, "tick_seconds", 0.2, 5)
    except ValueError as e:
        return err(str(e))
    return jsonify(svc().sim.configure(**kw))


@bp.post("/simulation/reset")
def reset():
    svc().reset()
    return jsonify({"status": "reset"})


@bp.get("/simulation")
def sim_status():
    return jsonify({"config": svc().sim.cfg.to_dict(), "active_incidents": svc().sim.active_incidents()})


@bp.post("/detect")
def detect():
    """Score an externally supplied cumulative-counter record (proves the simulator is replaceable)."""
    d = body()
    ext = current_app.config.setdefault("EXTERNAL_ENGINE", MonitoringPipeline())
    try:
        res = ext.process(d.get("counters", d), zone=str(d.get("zone", "external")), timestamp=d.get("timestamp"))
    except ValueError as e:
        return err(str(e), 422)
    return jsonify(res)


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        return jsonify(svc().engine_settings())
    d = body()
    try:
        thr = num(d, "threshold_scale", 0.25, 3.0) if "threshold_scale" in d else None
        smo = num(d, "smoothing", 0.0, 0.9) if "smoothing" in d else None
    except ValueError as e:
        return err(str(e))
    return jsonify(svc().update_engine_settings(thr, smo))


def _load(name):
    p = RESULTS_DIR / name
    return json.loads(p.read_text()) if p.exists() else None


@bp.get("/analytics")
def analytics():
    import csv
    comp = []
    p = RESULTS_DIR / "model_comparison.csv"
    if p.exists():
        with open(p) as f:
            comp = list(csv.DictReader(f))
    full = _load("model_results_full.json") or {}
    best = full.get("_best_model")
    cm = full.get(best) if best else None
    return jsonify({"comparison": comp, "window_ablation": _load("window_ablation.json"),
                    "feature_selection": _load("feature_selection.json"), "calibration": _load("threshold_calibration.json"),
                    "audit": _load("dataset_audit.json"), "best_model": best,
                    "confusion": {"labels": cm["labels"], "matrix": cm["confusion_matrix"]} if cm else None,
                    "live": svc().stats()})
