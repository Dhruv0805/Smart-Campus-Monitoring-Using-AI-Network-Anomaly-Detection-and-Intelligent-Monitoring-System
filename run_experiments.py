"""Reproducible experiment runner: baseline (Paper 1 protocol) vs improved pipeline.

    python run_experiments.py            # full run (~10 min on 1 CPU)
    python run_experiments.py --quick    # skip tuning grid + ReliefF

Writes data/results/*.json|csv and the deployable models/anomaly_model.pkl.
"""
from __future__ import annotations

import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from engine import MODEL_PATH, MODELS_DIR, RESULTS_DIR
from engine import data_preprocessor as dp
from engine.calibration import calibrate, sensitivity_sweep
from engine.feature_extraction import RAW_COLS, WINDOW, batch_features, feature_names
from engine.feature_selection import infogain, select_top_k
from engine.local_features import local_features
from engine.model_evaluation import (blocked_splits, evaluate, group_splits, random_splits,
                                     summary_row)
from engine.model_training import (SelectKModel, baseline_models, candidate_models, fit_final,
                                   save_bundle, tune_hgb)
from simulator.profiles import build_profiles

warnings.filterwarnings("ignore")
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


def dump(name, obj):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / name).write_text(json.dumps(obj, indent=2, default=float))



def diagnostics(rows, full, Xraw, y1):
    """(1) row index alone, (2) raw counters when the test device has a different counter offset."""
    from sklearn.ensemble import RandomForestClassifier
    from engine.model_evaluation import metrics as _m
    n = len(y1)
    idx = pd.DataFrame({"row_index": np.arange(n, dtype=float)})
    res = evaluate(RandomForestClassifier(100, random_state=0, n_jobs=1), idx, y1, blocked_splits(n, 100, 5))
    rows.append(summary_row("DIAGNOSTIC row index only (no traffic features)", res, dataset="ds1", features="row index", protocol="blocked 5-fold (no embargo)"))
    full[rows[-1]["experiment"]] = res
    log(f"diagnostic row-index-only: acc={res['accuracy']:.3f}")
    # raw counters, test blocks shifted by a per-block additive offset (deltas would be unchanged)
    rng = np.random.RandomState(0)
    X = Xraw.values
    sd = X.std(0)
    pred = np.empty(n, dtype=object)
    for tr, te in blocked_splits(n, 100, 5):
        m = RandomForestClassifier(100, random_state=0, n_jobs=1).fit(X[tr], y1[tr])
        Xt = X[te].copy()
        blk = te // 100
        for b in np.unique(blk):
            Xt[blk == b] += rng.uniform(-0.5, 0.5, X.shape[1]) * sd
        pred[te] = m.predict(Xt)
    res = _m(y1, pred)
    rows.append(summary_row("DIAGNOSTIC raw RF, test counters offset +-0.5 sd", res, dataset="ds1", features="raw cumulative", protocol="blocked 5-fold, shifted test"))
    full[rows[-1]["experiment"]] = res
    log(f"diagnostic raw+offset: acc={res['accuracy']:.3f}")


def deploy_stage(rows, full, Fv, yv, best_params):
    """Compare deployable candidates under per-class calibrated operating points; export the best."""
    import joblib
    from sklearn.ensemble import ExtraTreesClassifier
    cands = {
        "HGB tuned": HistGradientBoostingClassifier(random_state=0, class_weight="balanced", **best_params),
        "HGB regularised": HistGradientBoostingClassifier(max_iter=60, learning_rate=0.05, max_depth=4, l2_regularization=5.0,
                                                          min_samples_leaf=40, class_weight="balanced", random_state=0),
        "ExtraTrees": ExtraTreesClassifier(300, min_samples_leaf=3, class_weight="balanced", random_state=0, n_jobs=1),
    }
    out = {}
    for name, model in cands.items():
        thr, res, P, y_oof, classes = calibrate(model, Fv, yv, WINDOW, budget=0.10)
        out[name] = (thr, res, P, y_oof, classes, model)
        rows.append(summary_row(f"DEPLOY {name} + per-class thresholds (FAR budget 10%)", res, dataset="ds1", features="delta+window",
                                protocol="blocked 5-fold + embargo (honest)"))
        full[rows[-1]["experiment"]] = res
        log(f"deploy candidate {name}: FAR={res['false_alarm_rate']:.3f} recall={res['binary_anomaly_recall']:.3f} macroF1={res['macro_f1']:.3f}")
    ok = {k: v for k, v in out.items() if v[1]["false_alarm_rate"] <= 0.12} or out
    best = max(ok, key=lambda k: (ok[k][1]["binary_anomaly_recall"] + ok[k][1]["macro_f1"]))
    thr, res, P, y_oof, classes, model = out[best]
    log(f"deployed model: {best}")
    fit_final(model, Fv, yv)
    normal = Fv[yv == "normal"]
    med = normal.median()
    mad = (normal - med).abs().median() * 1.4826 + 1e-3
    MODELS_DIR.mkdir(exist_ok=True)
    save_bundle(MODEL_PATH, model, Fv.columns, model.classes_, {
        "window": WINDOW, "model_name": best, "normal_label": "normal", "thresholds": thr,
        "normal_median": med.to_dict(), "normal_mad": mad.to_dict(),
        "cv": {k: res[k] for k in ("accuracy", "macro_f1", "binary_anomaly_f1", "binary_anomaly_recall", "false_alarm_rate")},
        "per_class_recall": {c: v["recall"] for c, v in res["per_class"].items()}, "trained_rows": int(len(yv))})
    dump("threshold_calibration.json", {"model": best, "thresholds": thr, "metrics_at_thresholds": res,
                                        "sweep": sensitivity_sweep(P, y_oof, classes, thr)})
    full["_best_model"] = f"DEPLOY {best} + per-class thresholds (FAR budget 10%)"
    build_profiles()


def main(quick: bool):
    rows, full = [], {}

    # ------------------------------------------------------------------ dataset audit
    raw1 = dp.load_snmp_dataset()
    raw2 = dp.load_local_dataset()
    audits = {"dataset1_all_data": dp.audit(raw1), "dataset2_local_A_D": dp.audit(raw2)}
    dump("dataset_audit.json", audits)
    log(f"audit done: ds1 {audits['dataset1_all_data']['rows']} rows, ds2 {audits['dataset2_local_A_D']['rows']} rows")

    # ================================================================== DATASET 1
    y1 = raw1["class"].astype(object).to_numpy()
    Xraw = raw1[RAW_COLS].astype(float)

    # ---- Baseline (Paper-1 protocol): raw cumulative counters, InfoGain, stratified 10-fold
    topk_raw = select_top_k(Xraw, y1, 20, "infogain")
    for name, model in baseline_models().items():
        for tag, cols in (("all34", RAW_COLS), ("infogain20", topk_raw)):
            res = evaluate(model, Xraw[cols], y1, random_splits(y1, 10))
            rows.append(summary_row(f"BASELINE {name} [{tag}]", res, dataset="ds1", features="raw cumulative", protocol="stratified 10-fold (paper)"))
            full[rows[-1]["experiment"]] = res
        log(f"baseline {name}")

    # ---- Same raw features, honest blocked CV  -> quantifies the leakage
    def blocked(embargo=0):
        return lambda: blocked_splits(len(y1), block=100, k=5, embargo=embargo)

    for name, model in baseline_models().items():
        res = evaluate(model, Xraw, y1, blocked(0)())
        rows.append(summary_row(f"BASELINE {name} [all34]", res, dataset="ds1", features="raw cumulative", protocol="blocked 5-fold (honest)"))
        full[rows[-1]["experiment"]] = res
    log("baseline under blocked CV")

    # ---- Improved features: deltas + causal window stats + ratios
    F, valid = batch_features(raw1, WINDOW)
    Fv, yv = F[valid].reset_index(drop=True), y1[valid]
    n = len(yv)

    def honest(embargo=WINDOW):
        return lambda: blocked_splits(n, block=100, k=5, embargo=embargo)

    cands = candidate_models()
    for name, model in cands.items():
        res = evaluate(model, Fv, yv, honest()())
        rows.append(summary_row(f"IMPROVED {name} [delta+window, 105 feat]", res, dataset="ds1", features="delta+window", protocol="blocked 5-fold + embargo (honest)"))
        full[rows[-1]["experiment"]] = res
        log(f"improved {name}: macroF1={res['macro_f1']:.3f} acc={res['accuracy']:.3f}")

    # ---- Window ablation (HGB)
    abl = []
    for w in (1, 3, 5, 10):
        Fw, vw = batch_features(raw1, w)
        Fw, yw = Fw[vw].reset_index(drop=True), y1[vw]
        res = evaluate(candidate_models()["GradientBoosting(Hist)"], Fw, yw,
                       blocked_splits(len(yw), 100, 5, embargo=w))
        abl.append({"window": w, "accuracy": round(res["accuracy"], 4), "macro_f1": round(res["macro_f1"], 4),
                    "binary_anomaly_f1": round(res["binary_anomaly_f1"], 4)})
    dump("window_ablation.json", abl)
    log(f"window ablation {abl}")

    # ---- Feature selection comparison (selection inside folds)
    sel_rows = []
    methods = ["infogain", "importance"] + ([] if quick else ["relieff"])
    hgb = candidate_models()["GradientBoosting(Hist)"]
    for method in methods:
        for k in (20, 40):
            m = SelectKModel(hgb, method, k, list(Fv.columns))
            res = evaluate(m, Fv, yv, honest()())
            sel_rows.append({"method": method, "k": k, "accuracy": round(res["accuracy"], 4), "macro_f1": round(res["macro_f1"], 4),
                             "binary_anomaly_f1": round(res["binary_anomaly_f1"], 4)})
            log(f"selection {method} k={k}: macroF1={res['macro_f1']:.3f}")
    base_res = full["IMPROVED GradientBoosting(Hist) [delta+window, 105 feat]"]
    sel_rows.append({"method": "none", "k": Fv.shape[1], "accuracy": round(base_res["accuracy"], 4),
                     "macro_f1": round(base_res["macro_f1"], 4), "binary_anomaly_f1": round(base_res["binary_anomaly_f1"], 4)})
    dump("feature_selection.json", sel_rows)
    pd.Series(infogain(Fv, yv)).head(25).to_csv(RESULTS_DIR / "top_features_infogain.csv", header=["mutual_information"])

    # ---- Hyper-parameter tuning (HGB)
    grid = {"learning_rate": [0.1], "max_depth": [None], "max_iter": [150], "l2_regularization": [0.0]} if quick else \
           {"learning_rate": [0.05, 0.1], "max_depth": [None, 6], "max_iter": [120], "l2_regularization": [0.0, 1.0]}
    best_params, tune_rows = tune_hgb(Fv, yv, honest(), grid=grid)
    dump("tuning_hgb.json", {"best": best_params, "trials": tune_rows})
    log(f"tuned best={best_params}")
    tuned = HistGradientBoostingClassifier(random_state=0, class_weight="balanced", **best_params)
    res = evaluate(tuned, Fv, yv, honest()())
    rows.append(summary_row("IMPROVED HGB tuned [delta+window, 105 feat]", res, dataset="ds1", features="delta+window", protocol="blocked 5-fold + embargo (honest)"))
    full[rows[-1]["experiment"]] = res

    # ---- Diagnostics: why raw cumulative counters are not a valid basis for a live monitor
    diagnostics(rows, full, Xraw, y1)
    deploy_stage(rows, full, Fv, yv, best_params)

    # ================================================================== DATASET 2
    d2, rep2 = dp.clean(raw2)
    y2 = d2["class"].astype(object).to_numpy()
    groups = d2["source"].to_numpy()
    dump("dataset2_cleaning.json", rep2)
    Xr2 = local_features(d2, derived=False)
    Xd2 = local_features(d2, derived=True)

    for name, model in baseline_models().items():
        res = evaluate(model, Xr2, y2, random_splits(y2, 10))
        rows.append(summary_row(f"BASELINE {name} [raw16]", res, dataset="ds2", features="raw 16", protocol="stratified 10-fold (paper)"))
        full[rows[-1]["experiment"]] = res
        res = evaluate(model, Xr2, y2, group_splits(groups))
        rows.append(summary_row(f"BASELINE {name} [raw16]", res, dataset="ds2", features="raw 16", protocol="leave-one-capture-out (honest)"))
        full[rows[-1]["experiment"]] = res
    log("ds2 baselines")
    for name, model in candidate_models().items():
        res = evaluate(model, Xd2, y2, group_splits(groups))
        rows.append(summary_row(f"IMPROVED {name} [derived+log]", res, dataset="ds2", features="log + derived", protocol="leave-one-capture-out (honest)"))
        full[rows[-1]["experiment"]] = res
        log(f"ds2 improved {name}: macroF1={res['macro_f1']:.3f}")

    ds2_best = max((k for k in full if k.startswith("IMPROVED") and "[derived+log]" in k), key=lambda k: full[k]["macro_f1"])
    m2 = candidate_models()[ds2_best.split(" [")[0].replace("IMPROVED ", "")]
    fit_final(m2, Xd2, y2)
    save_bundle(MODELS_DIR / "local_signature_model.pkl", m2, Xd2.columns, m2.classes_,
                {"model_name": ds2_best, "dropped_constant": rep2["constant_removed"],
                 "cv": {k: full[ds2_best][k] for k in ("accuracy", "macro_f1")}})

    # ------------------------------------------------------------------ persist
    res_df = pd.DataFrame(rows)
    res_df.to_csv(RESULTS_DIR / "model_comparison.csv", index=False)
    dump("model_results_full.json", full)
    log("DONE")
    print(res_df[["experiment", "protocol", "accuracy", "macro_f1", "binary_anomaly_f1", "false_alarm_rate"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
