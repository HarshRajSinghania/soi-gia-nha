"""Error measures in terms a buyer understands: how far off, in percent of the price."""

from __future__ import annotations

import numpy as np
import pandas as pd


def summary(y_true, y_pred, low=None, high=None) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ape = np.abs(y_pred - y_true) / y_true
    out = {
        "n": len(y_true),
        "median_ape": float(np.median(ape)),
        "mape": float(np.mean(ape)),
        "within_10": float(np.mean(ape <= 0.10)),
        "within_20": float(np.mean(ape <= 0.20)),
    }
    if low is not None and high is not None:
        inside = (np.asarray(low) <= y_true) & (y_true <= np.asarray(high))
        out["range_coverage"] = float(np.mean(inside))
        out["range_width"] = float(np.median((np.asarray(high) - np.asarray(low)) / y_pred))
    return out


def by_group(df: pd.DataFrame, keys: list[str], **cols: str) -> pd.DataFrame:
    """``summary`` for each group. ``cols`` maps summary arguments to column names."""
    rows = []
    for key, g in df.groupby(keys, observed=True):
        args = {k: g[v] for k, v in cols.items()}
        rows.append({**dict(zip(keys, key, strict=True)), **summary(**args)})
    return pd.DataFrame(rows)
