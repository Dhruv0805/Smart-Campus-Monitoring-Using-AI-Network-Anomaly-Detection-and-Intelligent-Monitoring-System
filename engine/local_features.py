"""Features for dataset 2 (local_A..D, per-interval interface statistics)."""
import numpy as np
import pandas as pd

PKT_BINS = ["etherStatsPkts64Octets", "etherStatsPkts65to127Octets", "etherStatsPkts128to255Octets",
            "etherStatsPkts256to511Octets", "etherStatsPkts512to1023Octets", "etherStatsPkts1024to1518Octets"]


def local_features(df: pd.DataFrame, derived: bool = True) -> pd.DataFrame:
    X = df.drop(columns=[c for c in ("class", "source") if c in df.columns]).astype(float).copy()
    if not derived:
        return X
    pk_total = X[PKT_BINS].sum(axis=1) + 1.0
    in_pkts = X["ifInUcastPkts"] + X["ifInMulticastPkts"] + X["ifInBroadcastPkts"] + 1.0
    D = pd.DataFrame(index=X.index)
    for c in PKT_BINS:
        D["frac_" + c.replace("etherStatsPkts", "")] = X[c] / pk_total
    D["avg_in_pkt_bytes"] = X["ifHCInOctets"] / in_pkts
    D["avg_out_pkt_bytes"] = X["ifHCOutOctets"] / (X["ifOutUcastPkts"] + X["ifOutMulticastPkts"] + X["ifOutBroadcastPkts"] + 1.0)
    D["bcast_frac"] = X["ifInBroadcastPkts"] / in_pkts
    D["mcast_frac"] = X["ifInMulticastPkts"] / in_pkts
    D["out_in_octet_ratio"] = X["ifHCOutOctets"] / (X["ifHCInOctets"] + 1.0)
    D["out_in_pkt_ratio"] = X["ifOutUcastPkts"] / (X["ifInUcastPkts"] + 1.0)
    D["discard_rate"] = X["ifInDiscards"] / in_pkts
    out = pd.concat([np.log1p(X.clip(lower=0)), D], axis=1)
    return out
