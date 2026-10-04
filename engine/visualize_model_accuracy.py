"""STANDALONE utility (not part of the running app).  python -m engine.visualize_model_accuracy

Reads data/results/model_comparison.csv + model_results_full.json and writes PNG graphs to
data/results/plots/: accuracy, precision/recall/F1, per-class F1 and confusion matrices.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import RESULTS_DIR  # noqa: E402

PLOTS = RESULTS_DIR / "plots"


def short(s: str) -> str:
    return (s.replace("IMPROVED ", "IMP ").replace("BASELINE ", "BASE ").replace(" [delta+window, 105 feat]", "")
             .replace(" [derived+log]", "").replace("GradientBoosting(Hist)", "HGB"))


def grouped_bar(df, cols, title, fname, labels=None):
    fig, ax = plt.subplots(figsize=(max(9, len(df) * 0.9), 6))
    x = np.arange(len(df))
    w = 0.8 / len(cols)
    for i, c in enumerate(cols):
        ax.bar(x + i * w, df[c], w, label=(labels or cols)[i])
    ax.set_xticks(x + w * (len(cols) - 1) / 2)
    ax.set_xticklabels([f"{short(e)}\n{p.split(' ')[0]}" for e, p in zip(df.experiment, df.protocol)], rotation=40, ha="right", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / fname, dpi=130)
    plt.close(fig)


def confusion(res, title, fname):
    cm = np.array(res["confusion_matrix"])
    labs = res["labels"]
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labs)), labs, rotation=45, ha="right")
    ax.set_yticks(range(len(labs)), labs)
    for i in range(len(labs)):
        for j in range(len(labs)):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=8)
    ax.set_title(title)
    ax.set_xlabel("predicted")
    ax.set_ylabel("actual")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(PLOTS / fname, dpi=130)
    plt.close(fig)


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS_DIR / "model_comparison.csv")
    full = json.loads((RESULTS_DIR / "model_results_full.json").read_text())
    for ds, name in (("ds1", "dataset1"), ("ds2", "dataset2")):
        d = df[df.dataset == ds]
        if d.empty:
            continue
        grouped_bar(d, ["accuracy", "macro_f1"], f"{name}: accuracy vs macro-F1 (baseline vs improved)", f"{name}_accuracy.png", ["Accuracy", "Macro-F1"])
        grouped_bar(d, ["macro_precision", "macro_recall", "macro_f1"], f"{name}: macro precision / recall / F1", f"{name}_prf.png", ["Precision", "Recall", "F1"])
    best = full.get("_best_model")
    if best:
        confusion(full[best], f"Confusion matrix - {short(best)} (honest CV)", "confusion_best_model.png")
        pc = full[best]["per_class"]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(pc.keys(), [v["f1"] for v in pc.values()], color="#38bdf8")
        ax.set_ylim(0, 1)
        ax.set_title(f"Per-class F1 - {short(best)}")
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
        fig.tight_layout()
        fig.savefig(PLOTS / "per_class_f1_best_model.png", dpi=130)
        plt.close(fig)
    leaky = next((k for k in full if k.startswith("BASELINE RandomForest [all34]") and False), None)
    for k, r in full.items():
        if k == "BASELINE RandomForest [all34]":
            confusion(r, "Baseline RF, raw counters (paper protocol: random 10-fold)", "confusion_baseline_paper_protocol.png")
    wa = RESULTS_DIR / "window_ablation.json"
    if wa.exists():
        w = pd.DataFrame(json.loads(wa.read_text()))
        fig, ax = plt.subplots(figsize=(6, 4))
        for c in ("accuracy", "macro_f1", "binary_anomaly_f1"):
            ax.plot(w.window, w[c], marker="o", label=c)
        ax.set_xlabel("window (polls)")
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_title("Window-size ablation")
        fig.tight_layout()
        fig.savefig(PLOTS / "window_ablation.png", dpi=130)
        plt.close(fig)
    print("plots written to", PLOTS)


if __name__ == "__main__":
    main()
