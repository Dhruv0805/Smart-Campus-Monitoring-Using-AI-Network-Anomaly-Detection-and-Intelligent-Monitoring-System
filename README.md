# Smart Campus Monitoring Using AI

Real-time network anomaly detection for a simulated Smart Campus:
**SNMP counters → streaming features → improved ML engine → risk score → live graph / alert / log**,
with a Streamlit prototype and a Flask + React final app that share the same engine and simulator.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# models are already in models/. To re-run every experiment and retrain (~12 min on 1 CPU):
python run_experiments.py

python -m pytest -q                                      # 36 tests

# A) Streamlit prototype
streamlit run streamlit/app.py                           # http://localhost:8501

# B) Final app (Flask API + React)
cd frontend && npm install && npm run build && cd ..     # builds frontend/dist
python -m backend.app                                    # http://localhost:5000  (serves API + React)
#   dev mode with hot reload:  python -m backend.app  
cd frontend 
npm run dev  (http://localhost:5173)

python -m engine.visualize_model_accuracy                # standalone: PNG graphs -> data/results/plots/
```

**Demo (section 29 of the plan):** open *Simulation* → choose *TCP-SYN*, intensity 0.8-1.0, 20 s → **START ANOMALY** →
within ~1-3 s the packet-rate graph on *Dashboard* shows ✕ markers, the zone card turns red, an alert row appears
(attack, confidence, risk, time) → **STOP ALL** and traffic returns to normal.

## What was found in the data (important for the report)

| Dataset | Content | Finding |
|---|---|---|
| `all_data.csv` | 4,998 rows × 34 SNMP-MIB counters, 8 classes | Columns are **cumulative counters**, rows are stored **grouped by class in time order** (600 normal, then 632 icmp-echo, …). |
| `local_A..D.csv` | 40,262 rows × 22 features (6 constant), 8 classes | Per-interval interface statistics, 4 independent captures, ~97% normal. Not merged with dataset 1 (different features). |

(The plan says 9 classes for dataset 2; the files contain 8: `normal` + `sign_a … sign_g`.)

**The paper protocol is leaky on dataset 1.** Random 10-fold CV on raw cumulative counters gives ~99.9-100% for RF/J48/REPTree
(reproducing Paper 1's level), but:

* a Random Forest given **only the row number** (no traffic information) scores **91.3% accuracy** under blocked CV – the raw
  counters mostly encode *when in the capture* a row is, not what the traffic does;
* raw RF under blocked CV drops to 91.4% acc / 0.896 macro-F1 (J48/REPTree: 76%), and to **68.6%** if the counter offset of the
  test blocks is shifted;
* a live monitor never sees a meaningful absolute counter value – only how fast counters tick.

So the improved pipeline works on **per-poll deltas** (32-bit wrap repaired, resets invalidated), causal window mean/std
(window = 5) and traffic ratios (105 features, log scale), evaluated with **blocked 5-fold CV + embargo** so overlapping
windows cannot leak. The delta-based numbers are lower than the paper's *because they are honest*.

## Results (dataset 1, honest protocol; full table in `data/results/model_comparison.csv`)

| Experiment | Accuracy | Macro-F1 | Attack recall | False-alarm rate |
|---|---|---|---|---|
| Paper baseline RF / J48 / REPTree, random 10-fold, raw | 1.000 / 0.999 / 0.999 | 1.000 / 0.999 / 0.999 | ~1.0 | ~0 |
| Same raw features, blocked CV | 0.914 / 0.764 / 0.764 | 0.896 / 0.757 / 0.757 | – | 0.08 / 0.20 / 0.20 |
| Improved features: DT / RF / ExtraTrees / HistGB | 0.59 / 0.62 / 0.63 / 0.68 | 0.54 / 0.58 / 0.63 / 0.66 | 0.94-0.95 | 0.51-0.64 |
| **Deployed**: regularised HistGB + per-class thresholds (≤10% FAR budget) | 0.632 | 0.577 | **0.853** | **0.088** |

Honest reading: with delta features **normal vs. attack** is separable (anomaly F1 0.95 at a naive threshold) but at that threshold
~50% of normal polls are flagged. The deployed model trades recall for a usable alarm rate. Per-class recall at the deployed
operating point: httpFlood 0.95, tcp-syn 0.75, udp-flood 0.68, bruteForce 0.66, slowloris 0.51, icmp-echo 0.44, **slowpost 0.02**,
normal 0.91. Slow attacks (slowloris, slowpost) barely change IP/TCP counters, so this data fundamentally cannot detect them well.
**Do not claim "improved accuracy over Paper 1"**; the defensible claim is *a leakage-free evaluation, a deployable
streaming pipeline, and calibrated alarm rates*. Other experiments: window ablation (1/3/5/10 – all within noise except 10),
feature selection (InfoGain / ReliefF / model-importance, k=20/40 *inside* each fold – no gain over all 105 features),
HistGB grid search (`tuning_hgb.json`).

**Dataset 2:** 8-class signatures are essentially solved: RF 0.9997 acc / 0.9985 macro-F1 under *leave-one-capture-out*
(train on 3 captures, test on the 4th) – a harder protocol than random CV. Derived features (packet-size fractions, ratios) give
RF 0.9985 vs REPTree 0.954 macro-F1. Saved as `models/local_signature_model.pkl`; it needs interface statistics, which the
simulator does not emit, so the live system uses the dataset-1 model.

## Architecture

```
engine/       data_preprocessor · feature_extraction (+streaming) · feature_selection · model_training ·
              model_evaluation · calibration · local_features · visualize_model_accuracy (standalone) ·
              model_loader · anomaly_detector · risk_scoring · pipeline
simulator/    network_simulator · campus_entities (6 zones, 23 devices) · traffic_generator ·
              anomaly_generator (random Poisson + manual) · simulation_config · profiles
backend/      Flask REST API (validated)      frontend/  React + Tailwind + Recharts      streamlit/app.py  prototype
tests/        preprocessor · engine · simulator · api · realtime      run_experiments.py   reproducible experiments
```

* **Simulator contract** – `tick()` returns one cumulative-counter record per zone gateway (exactly what an SNMP poller returns).
  Replace it with a real poller and nothing else changes; `POST /api/detect` already scores external records.
  Counters are produced by block-resampling real per-class delta rows (keeps hard floors/joint structure that a Gaussian
  version broke) with intensity-weighted normal→attack interpolation and zone load scaling.
* **Detection** – per-class calibrated thresholds on `predict_proba`, probability smoothing, alert only after 2 of 3 consecutive
  flags once the window is full (`confirmed`), new incident = first confirmation of a type.
* **Risk** – `100 × strength × (0.15 + 0.35·severity + 0.25·intensity + 0.25·persistence)` → NORMAL/LOW/MEDIUM/HIGH/CRITICAL
  (`engine/risk_scoring.py`).
* **API** – `GET /api/{health,state,series,events,devices,zones,attack-types,analytics,settings,simulation}`,
  `POST /api/simulation/{inject,stop,config,reset}`, `POST /api/settings`, `POST /api/detect`; bodies/params are type- and
  range-checked (400/422 on bad input).

## Live-loop behaviour (simulator → engine; `data/results/live_detection_summary.txt`)

Normal traffic: **~3% of polls flagged**. 60 s attacks at intensity 1.0 – share of polls flagged / mean seconds to confirmation:
httpFlood 100% / 1.0, bruteForce 100% / 1.0, icmp-echo 100% / 1.0, tcp-syn 99% / 1.3, udp-flood 97% / 2.7, slowloris 66% / 5.0,
**slowpost 9% / ~38 (effectively undetected)**. At intensity 0.6 detection stays high for floods but the *class label* is often
wrong (e.g. tcp-syn 44% correct) – it is still alerted as an anomaly.

## Limitations (state these in the viva)

1. **Simulator traffic is resampled from the training rows**, so live detection is optimistic compared with the honest-CV numbers
   above (which are the ones to report as model quality).
2. Dataset 1 is one device/one capture per class; generalisation to other networks is untested.
3. SlowPOST is not detectable from these counters; slowloris only partially.
4. "J48" and "REPTree" are scikit-learn analogues (entropy tree / cost-complexity-pruned tree), not Weka's implementations;
   ReliefF is a compact in-house implementation.
5. Only the packet-rate series is plotted live; per-zone traffic is a single gateway, not per-device flows.
