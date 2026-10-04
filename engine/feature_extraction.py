"""Turn cumulative SNMP counters into rate/window features.

Why: the dataset-1 columns are *cumulative counters*. Their absolute level mostly encodes *when*
the capture was taken, not what the traffic is doing. A monitor that polls a real device only sees
the counters tick up, so the transferable signal is the per-interval delta. The streaming extractor
below produces exactly the same features as the batch one used for training (tested).
"""
from __future__ import annotations

import warnings
from collections import deque

import numpy as np
import pandas as pd

WRAP = 2.0 ** 32
WINDOW = 5

# The 34 raw input columns of dataset 1 (after normalize_columns). tcpCurrEstab is a gauge.
GAUGE_COLS = ["tcpCurrEstab"]
COUNTER_COLS = [
    "ifInOctets11", "ifOutOctets11", "ifoutDiscards11", "ifInUcastPkts11", "ifInNUcastPkts11",
    "ifInDiscards11", "ifOutUcastPkts11", "ifOutNUcastPkts11", "tcpOutRsts", "tcpInSegs",
    "tcpOutSegs", "tcpPassiveOpens", "tcpRetransSegs", "tcpEstabResets", "tcpActiveOpens",
    "udpInDatagrams", "udpOutDatagrams", "udpInErrors", "udpNoPorts", "ipInReceives",
    "ipInDelivers", "ipOutRequests", "ipOutDiscards", "ipInDiscards", "ipForwDatagrams",
    "ipOutNoRoutes", "ipInAddrErrors", "icmpInMsgs", "icmpInDestUnreachs", "icmpOutMsgs",
    "icmpOutDestUnreachs", "icmpInEchos", "icmpOutEchoReps",
]
RAW_COLS = COUNTER_COLS + GAUGE_COLS

# (name, numerator, denominator) ratios computed on the window means
RATIOS = [
    ("r_tcp_ip", "tcpInSegs", "ipInDelivers"),
    ("r_udp_ip", "udpInDatagrams", "ipInDelivers"),
    ("r_icmp_ip", "icmpInMsgs", "ipInDelivers"),
    ("r_fwd_rec", "ipForwDatagrams", "ipInReceives"),
    ("r_out_in", "ipOutRequests", "ipInDelivers"),
    ("bytes_per_pkt", "ifInOctets11", "ifInUcastPkts11"),
]


def feature_names(window: int = WINDOW) -> list[str]:
    return ([f"{c}_d" for c in COUNTER_COLS] + [f"{c}_m{window}" for c in COUNTER_COLS]
            + [f"{c}_s{window}" for c in COUNTER_COLS] + [r[0] for r in RATIOS])


def counters_to_deltas(raw: pd.DataFrame) -> pd.DataFrame:
    """Per-interval deltas of the cumulative counters. 32-bit wrap-arounds are repaired; a counter
    reset (device restart / new capture) makes the whole row invalid (NaN)."""
    X = raw[COUNTER_COLS].astype(float)
    d = X.diff()
    prev = X.shift()
    wrapped = (d < 0) & (prev > WRAP * 0.5) & ((d + WRAP) < WRAP * 0.5)
    D = d.where(~(d < 0), np.nan).mask(wrapped, d + WRAP)
    reset_row = ((d < 0).sum(axis=1) - wrapped.sum(axis=1)) > 0
    D.loc[reset_row, :] = np.nan
    D.iloc[0] = np.nan
    return D


def deltas_to_features(D: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Causal window features (only past rows are used) on log1p scale."""
    R = D.rolling(window, min_periods=1)
    mean, std = R.mean(), R.std().fillna(0)
    base = D.fillna(mean).fillna(0)
    F = pd.concat([base.add_suffix("_d"), mean.fillna(0).add_suffix(f"_m{window}"),
                   std.add_suffix(f"_s{window}")], axis=1)
    m = mean.fillna(0)
    for name, num, den in RATIOS:
        F[name] = m[num] / (m[den] + 1.0)
    return np.log1p(F.clip(lower=0))[feature_names(window)]


def batch_features(raw: pd.DataFrame, window: int = WINDOW):
    """Raw cumulative frame -> (feature frame, valid-row mask). Row 0 has no delta -> invalid."""
    F = deltas_to_features(counters_to_deltas(raw), window)
    valid = np.ones(len(F), dtype=bool)
    valid[0] = False
    return F, valid


class StreamingFeatureExtractor:
    """Stateful, one instance per monitored device. push() takes a cumulative-counter dict."""

    def __init__(self, window: int = WINDOW):
        self.window = window
        self.prev: dict | None = None
        self.hist: deque = deque(maxlen=window)
        self.last_delta: dict = {}

    def reset(self):
        self.prev = None
        self.hist.clear()
        self.last_delta = {}

    def push(self, counters: dict):
        """Returns (feature_vector | None, delta_dict | None). None while warming up."""
        cur = np.array([float(counters[c]) for c in COUNTER_COLS])
        if self.prev is None:
            self.prev = cur
            return None, None
        d = cur - self.prev
        neg = d < 0
        wrapped = neg & (self.prev > WRAP * 0.5) & ((d + WRAP) < WRAP * 0.5)
        d = np.where(wrapped, d + WRAP, d)
        reset = bool((neg & ~wrapped).any())
        self.prev = cur
        row = np.full(len(COUNTER_COLS), np.nan) if reset else d
        self.hist.append(row)
        H = np.vstack(self.hist)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            cnt = np.sum(~np.isnan(H), axis=0)
            mean = np.where(cnt > 0, np.nanmean(H, axis=0), np.nan)
            std = np.where(cnt > 1, np.nanstd(H, axis=0, ddof=1), 0.0)
        base = np.where(np.isnan(row), mean, row)
        base, mean_f = np.nan_to_num(base), np.nan_to_num(mean)
        idx = {c: i for i, c in enumerate(COUNTER_COLS)}
        ratios = [mean_f[idx[n]] / (mean_f[idx[dn]] + 1.0) for _, n, dn in RATIOS]
        vec = np.log1p(np.clip(np.concatenate([base, mean_f, std, ratios]), 0, None))
        self.last_delta = {c: float(base[i]) for i, c in enumerate(COUNTER_COLS)}
        return vec, self.last_delta
