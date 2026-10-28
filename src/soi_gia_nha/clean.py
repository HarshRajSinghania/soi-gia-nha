"""Turn raw listings into a modelling table.

Every rule here comes from notebooks/01_eda.ipynb.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

DEFAULT_PROVINCES = ["Hà Nội", "Hồ Chí Minh"]

# Sanity bounds per property type: (min area m2, max area m2, min, max million VND per m2).
# Loose on purpose, they only remove what cannot be a real total price.
BOUNDS = {
    "Căn hộ chung cư": (20, 400, 15, 600),
    "Nhà": (10, 1_000, 15, 1_500),
    "Biệt thự/Nhà liền kề": (30, 2_000, 20, 1_500),
    "Shophouse": (20, 2_000, 20, 1_500),
    "Đất": (20, 10_000, 1, 1_000),
}
MIN_PRICE = 200e6


def _key(s: pd.Series) -> pd.Series:
    """Whitespace- and case-insensitive text key for spotting reposts."""
    return (
        s.fillna("")
        .map(lambda x: unicodedata.normalize("NFC", x))
        .str.lower()
        .map(lambda x: re.sub(r"\s+", " ", x).strip())
    )


def clean(df: pd.DataFrame, provinces: list[str] | None = DEFAULT_PROVINCES) -> pd.DataFrame:
    """Filter, type and deduplicate. Returns a new frame sorted by publish time."""
    out = df.copy()
    if provinces:
        out = out[out["province_name"].isin(provinces)]

    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["published_at"] = pd.to_datetime(out["published_at"], errors="coerce")
    out = out.dropna(subset=["price", "area", "published_at", "district_name"])
    out = out[out["property_type_name"].isin(BOUNDS) & (out["price"] >= MIN_PRICE)]

    bounds = out["property_type_name"].map(BOUNDS)
    ppm = out["price"] / out["area"] / 1e6
    keep = [
        lo_a <= a <= hi_a and lo_p <= p <= hi_p
        for a, p, (lo_a, hi_a, lo_p, hi_p) in zip(out["area"], ppm, bounds, strict=True)
    ]
    out = out[keep]

    # Keep the first appearance of each listing. Reposts would otherwise end up on both
    # sides of the time split and make the model look better than it is.
    out = out.sort_values("published_at", kind="stable")
    out = out.assign(_t=_key(out["name"]), _d=_key(out["description"]))
    out = out.drop_duplicates(["_t", "price", "area"])
    out = out[(out["_d"].str.len() < 50) | ~out.duplicated(["_d", "price", "area"])]

    out = out.drop(columns=["_t", "_d"]).reset_index(drop=True)
    out["price_per_m2"] = out["price"] / out["area"]
    return out
