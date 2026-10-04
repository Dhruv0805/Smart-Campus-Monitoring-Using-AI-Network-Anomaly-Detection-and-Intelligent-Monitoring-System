"""Smart Campus AI Monitor - Streamlit prototype.

    streamlit run streamlit/app.py

Own monitoring loop + UI (simulator -> engine -> charts). Shares only the AI engine and the
simulator with the Flask/React app.
"""
from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from engine import RESULTS_DIR  # noqa: E402
from engine.pipeline import MonitoringPipeline  # noqa: E402
from simulator.campus_entities import DEVICES, ZONES  # noqa: E402
from simulator.network_simulator import NetworkSimulator  # noqa: E402
from simulator.simulation_config import ATTACK_TYPES, SimulationConfig  # noqa: E402

st.set_page_config(page_title="Smart Campus AI Monitor", page_icon="🛰️", layout="wide")

LEVEL_COLOR = {"NORMAL": "#22c55e", "LOW": "#eab308", "MEDIUM": "#f97316", "HIGH": "#ef4444", "CRITICAL": "#d946ef"}
LEVELS = list(LEVEL_COLOR)
ZONE_NAME = {z.id: z.name for z in ZONES}

st.markdown("""
<style>
.stApp {background: radial-gradient(1200px 600px at 10% -10%, #1e2a5a 0%, #0b1020 55%) fixed; color:#e5e9f7;}
section[data-testid="stSidebar"] {background:#0a0f20; border-right:1px solid #1d2748;}
.kpi {background:linear-gradient(145deg,rgba(40,52,110,.55),rgba(16,22,48,.75)); border:1px solid #27345f;
      border-radius:16px; padding:16px 18px; box-shadow:0 8px 24px rgba(0,0,0,.35);}
.kpi .l {font-size:12px; letter-spacing:.08em; color:#8d9ac7; text-transform:uppercase;}
.kpi .v {font-size:30px; font-weight:700; margin-top:2px;}
.badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600;}
.live {color:#22c55e; font-weight:700;}
h1,h2,h3 {color:#f1f4ff !important;}
div[data-testid="stDataFrame"] {border-radius:12px;}
</style>""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- monitor state
class LiveMonitor:
    """Streamlit's own monitoring logic: tick simulator, run engine, keep history/events."""

    def __init__(self):
        self.sim = NetworkSimulator(SimulationConfig())
        self.engine = MonitoringPipeline()
        self.hist = {z.id: deque(maxlen=600) for z in ZONES}
        self.events: list[dict] = []
        self.latest: dict = {}
        self.last_wall = time.time()
        self.alerts = 0

    def step(self):
        for rec in self.sim.tick():
            r = self.engine.process(rec["counters"], zone=rec["zone"], timestamp=rec["timestamp"])
            r.update(truth=rec["truth"], device=rec["device"])
            self.hist[rec["zone"]].append(r)
            self.latest[rec["zone"]] = r
            if r["new_incident"]:
                self.alerts += 1
                self.events.insert(0, {"time (s)": r["timestamp"], "zone": ZONE_NAME[r["zone"]], "detected": r["prediction"],
                                       "actual": r["truth"], "confidence": r["confidence"], "risk": r["risk"]["level"],
                                       "score": r["risk"]["score"]})
                self.events = self.events[:300]

    def advance(self):
        """Catch up with wall-clock so the simulation keeps running whichever page is open."""
        now = time.time()
        if self.sim.cfg.running:
            n = int(min((now - self.last_wall) / self.sim.cfg.tick_seconds, 120))
            for _ in range(max(n, 0)):
                self.step()
            if n > 0:
                self.last_wall = now
        else:
            self.last_wall = now


def mon() -> LiveMonitor:
    if "mon" not in st.session_state:
        st.session_state.mon = LiveMonitor()
        for _ in range(12):      # warm-up so charts are not empty
            st.session_state.mon.step()
    return st.session_state.mon


def kpi(label, value, color="#e5e9f7"):
    st.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v" style="color:{color}">{value}</div></div>',
                unsafe_allow_html=True)


def dark(fig, h=340):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,20,44,.55)",
                      height=h, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.12))
    return fig


def frame(zone):
    rows = [{"t": p["timestamp"], "packets": p["metrics"]["packet_rate"], "bytes": p["metrics"]["byte_rate"],
             "risk": p["risk"]["score"], "level": p["risk"]["level"], "anom": p["confirmed"], "pred": p["prediction"],
             "truth": p["truth"]} for p in mon().hist[zone] if not p["warming_up"]]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- pages
def page_dashboard():
    m = mon()
    st.title("Smart Campus AI Monitor")
    zone_ids = [z.id for z in ZONES]
    zone = st.selectbox("Zone", zone_ids, format_func=lambda z: ZONE_NAME[z], key="dash_zone")

    @st.fragment(run_every=1.0 if m.sim.cfg.running else None)
    def live():
        m.advance()
        latest = [v for v in m.latest.values() if v]
        worst = max((LEVELS.index(v["risk"]["level"]) for v in latest), default=0)
        now_anoms = sum(1 for v in latest if v["confirmed"])
        c = st.columns(4)
        with c[0]:
            kpi("Network status", "● ONLINE" if m.sim.cfg.running else "❚❚ PAUSED", "#22c55e" if m.sim.cfg.running else "#eab308")
        with c[1]:
            kpi("Active anomalies", f"{now_anoms:02d}", "#ef4444" if now_anoms else "#e5e9f7")
        with c[2]:
            kpi("Overall risk", LEVELS[worst], LEVEL_COLOR[LEVELS[worst]])
        with c[3]:
            kpi("Alerts raised", m.alerts)
        df = frame(zone)
        if df.empty:
            st.info("Collecting data…")
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.t, y=df.packets, mode="lines", name="Packet rate (pkts/interval)",
                                 line=dict(color="#38bdf8", width=2), fill="tozeroy", fillcolor="rgba(56,189,248,.10)"))
        a = df[df.anom]
        if len(a):
            fig.add_trace(go.Scatter(x=a.t, y=a.packets, mode="markers", name="AI detection",
                                     marker=dict(symbol="x", size=11, color=[LEVEL_COLOR[l] for l in a.level], line=dict(width=1, color="white")),
                                     text=a.pred, hovertemplate="%{text}<br>t=%{x}s<br>%{y:,.0f} pkts<extra></extra>"))
        fig.update_layout(title=f"Real-time packet rate - {ZONE_NAME[zone]}", xaxis_title="simulated time (s)")
        st.plotly_chart(dark(fig), width="stretch", key=f"pk{time.time()}")
        l, r = st.columns([1, 1])
        with l:
            f2 = go.Figure(go.Scatter(x=df.t, y=df.risk, mode="lines", line=dict(color="#a78bfa", width=2), fill="tozeroy",
                                      fillcolor="rgba(167,139,250,.15)", name="risk"))
            f2.update_layout(title="Risk score (0-100)", yaxis_range=[0, 100])
            st.plotly_chart(dark(f2, 260), width="stretch", key=f"rk{time.time()}")
        with r:
            st.markdown("**Network zones**")
            cols = st.columns(3)
            for i, z in enumerate(ZONES):
                v = m.latest.get(z.id)
                lvl = v["risk"]["level"] if v else "NORMAL"
                label = (v["prediction"] if v and v["confirmed"] else "normal")
                with cols[i % 3]:
                    st.markdown(f'<div class="kpi" style="padding:10px 12px;margin-bottom:8px"><div class="l">{z.name}</div>'
                                f'<div class="v" style="font-size:16px;color:{LEVEL_COLOR[lvl]}">{lvl}</div>'
                                f'<div class="l">{label}</div></div>', unsafe_allow_html=True)
        st.markdown("**Recent anomalies**")
        st.dataframe(pd.DataFrame(m.events[:8]), width="stretch", hide_index=True)

    live()


def page_network():
    m = mon()
    m.advance()
    st.title("Network overview")
    import math
    fig = go.Figure()
    xs, ys = [0.0], [0.0]
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["Campus core"], textposition="bottom center",
                             marker=dict(size=34, color="#6366f1"), showlegend=False))
    for i, z in enumerate(ZONES):
        ang = 2 * math.pi * i / len(ZONES)
        x, y = 2 * math.cos(ang), 2 * math.sin(ang)
        v = m.latest.get(z.id)
        lvl = v["risk"]["level"] if v else "NORMAL"
        fig.add_trace(go.Scatter(x=[0, x], y=[0, y], mode="lines", line=dict(color="#334170", width=2), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[z.name], textposition="top center", showlegend=False,
                                 marker=dict(size=26, color=LEVEL_COLOR[lvl], line=dict(width=2, color="white")),
                                 hovertext=f"{z.gateway}<br>{lvl}", hoverinfo="text"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    st.plotly_chart(dark(fig, 480), width="stretch")
    rows = []
    for z in ZONES:
        v = m.latest.get(z.id)
        if v and not v["warming_up"]:
            rows.append({"zone": z.name, "gateway": z.gateway, "packets/int": int(v["metrics"]["packet_rate"]),
                         "bytes/int": int(v["metrics"]["byte_rate"]), "status": v["prediction"], "risk": v["risk"]["level"]})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def page_anomalies():
    m = mon()
    m.advance()
    st.title("Anomaly history")
    if not m.events:
        st.info("No anomalies detected yet. Use the Simulation page to inject one.")
        return
    df = pd.DataFrame(m.events)
    sel = st.multiselect("Filter by detected type", sorted(df["detected"].unique()))
    if sel:
        df = df[df["detected"].isin(sel)]
    st.dataframe(df, width="stretch", hide_index=True)
    st.bar_chart(df["detected"].value_counts())


def page_devices():
    m = mon()
    m.advance()
    st.title("Campus devices")
    rows = []
    for d in DEVICES:
        v = m.latest.get(d.zone)
        hit = bool(v and v["confirmed"])
        rows.append({"device": d.name, "type": d.type, "zone": ZONE_NAME[d.zone], "address": d.ip, "services": ", ".join(d.services),
                     "status": "under attack" if hit else "healthy", "attack": v["prediction"] if hit else "-"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def page_simulation():
    m = mon()
    m.advance()
    st.title("Simulation control")
    c1, c2 = st.columns(2)
    with c1:
        run = st.toggle("Simulation running", value=m.sim.cfg.running)
        rnd = st.toggle("Random anomalies", value=m.sim.cfg.random_anomalies)
        gap = st.slider("Mean seconds between random anomalies", 10, 300, int(m.sim.cfg.random_mean_gap_s))
        m.sim.configure(running=run, random_anomalies=rnd, random_mean_gap_s=float(gap))
    with c2:
        st.subheader("Manual anomaly injection")
        atk = st.selectbox("Attack type", list(ATTACK_TYPES), format_func=lambda k: ATTACK_TYPES[k]["label"])
        zone = st.selectbox("Target zone", ["(auto)"] + [z.id for z in ZONES], format_func=lambda z: ZONE_NAME.get(z, z))
        inten = st.slider("Intensity", 0.1, 1.0, 0.8, 0.05)
        dur = st.slider("Duration (s)", 3, 120, 15)
        b1, b2 = st.columns(2)
        if b1.button("START ANOMALY", type="primary", width="stretch"):
            inc = m.sim.inject(atk, inten, dur, None if zone == "(auto)" else zone)
            st.success(f"Injected {atk} into {ZONE_NAME[inc.zone]} for {dur}s")
        if b2.button("STOP ALL", width="stretch"):
            st.info(f"Stopped {m.sim.stop_anomalies()} incident(s)")
    st.subheader("Active incidents")
    st.dataframe(pd.DataFrame(m.sim.active_incidents()), width="stretch", hide_index=True)


def page_analytics():
    mon().advance()
    st.title("Model analytics")
    p = RESULTS_DIR / "model_comparison.csv"
    if not p.exists():
        st.warning("Run `python run_experiments.py` to generate results.")
        return
    df = pd.read_csv(p)
    st.dataframe(df, width="stretch", hide_index=True)
    d1 = df[df.dataset == "ds1"]
    fig = go.Figure()
    for metric, col in (("Macro F1", "#38bdf8"), ("Accuracy", "#a78bfa")):
        fig.add_trace(go.Bar(x=d1.experiment, y=d1["macro_f1" if metric == "Macro F1" else "accuracy"], name=metric, marker_color=col))
    fig.update_layout(title="Dataset 1: baseline (paper protocol) vs improved (honest protocol)", barmode="group", xaxis_tickangle=-35)
    st.plotly_chart(dark(fig, 520), width="stretch")
    full = RESULTS_DIR / "model_results_full.json"
    if full.exists():
        j = json.loads(full.read_text())
        best = j.get("_best_model")
        st.caption("Rows labelled DIAGNOSTIC show that raw cumulative counters are not a safe basis for deployment.")
        if best:
            cm = j[best]
            fig = go.Figure(go.Heatmap(z=cm["confusion_matrix"], x=cm["labels"], y=cm["labels"], colorscale="Blues", text=cm["confusion_matrix"], texttemplate="%{text}"))
            fig.update_layout(title=f"Confusion matrix - {best}", xaxis_title="predicted", yaxis_title="actual")
            st.plotly_chart(dark(fig, 480), width="stretch")


def page_settings():
    m = mon()
    m.advance()
    st.title("Settings")
    thr = st.slider("Detection threshold scale (x calibrated per-class thresholds; <1 more sensitive)", 0.25, 3.0, float(m.engine.detector.threshold_scale), 0.05)
    smo = st.slider("Probability smoothing (weight of previous tick)", 0.0, 0.9, float(m.engine.smoothing), 0.05)
    m.engine.detector.threshold_scale, m.engine.smoothing = thr, smo
    st.caption("Calibrated thresholds: " + ", ".join(f"{k} {v:.2f}" for k, v in m.engine.detector.thresholds.items()))
    st.caption(f"Model: {m.engine.bundle.get('model_name')} - window {m.engine.window} - classes {', '.join(m.engine.detector.classes)}")
    if st.button("Reset monitor"):
        del st.session_state["mon"]
        st.rerun()


PAGES = {"Dashboard": page_dashboard, "Network": page_network, "Anomalies": page_anomalies, "Devices": page_devices,
         "Simulation": page_simulation, "Analytics": page_analytics, "Settings": page_settings}

with st.sidebar:
    st.markdown("### 🛰️ SMART CAMPUS\n**AI Monitor**")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.markdown('<span class="live">● LIVE</span>' if mon().sim.cfg.running else "❚❚ paused", unsafe_allow_html=True)

PAGES[page]()
