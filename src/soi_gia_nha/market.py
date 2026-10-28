"""Market context for one listing: how prices in the ward moved, and similar properties.

Both work on property-level tables built by ``scripts/build_app_data.py``, so a property
reposted 20 times counts once.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_MONTHLY = 8  # fewer properties than this in a month makes the median too noisy to plot


def monthly_pulse(props: pd.DataFrame) -> pd.DataFrame:
    """Median asking price per m2 of properties first listed each month, per ward and district.

    Rows with ``ward_name`` empty are district-level totals."""
    p = props.assign(
        month=props["first_seen"].dt.to_period("M").dt.to_timestamp(),
        ppm=props["first_price"] / props["area"],
    )
    keys = ["district_name", "property_type_name", "month"]
    ward = p.groupby(["district_name", "ward_name", "property_type_name", "month"]).agg(
        ppm=("ppm", "median"), listed=("ppm", "size")
    )
    district = p.groupby(keys).agg(ppm=("ppm", "median"), listed=("ppm", "size"))
    district = district.reset_index().assign(ward_name=None)
    return pd.concat([ward.reset_index(), district], ignore_index=True)


@dataclass
class Pulse:
    area: str  # "phường Dịch Vọng" or "quận Cầu Giấy"
    months: pd.Series  # median price per m2 indexed by month
    listed: int  # properties first listed in the period
    change: float | None  # last 3 months vs first 3 months


def pulse_for(
    table: pd.DataFrame, district: str, ward: str | None, property_type: str
) -> Pulse | None:
    """Ward trend when the ward has enough listings every month, else the district."""
    candidates = []
    if ward:
        candidates.append((table["ward_name"] == ward, f"phường {ward}"))
    candidates.append((table["ward_name"].isna(), f"quận {district}"))
    base = (table["district_name"] == district) & (table["property_type_name"] == property_type)
    for mask, label in candidates:
        rows = table[base & mask].sort_values("month")
        enough = rows[rows["listed"] >= MIN_MONTHLY]
        if len(enough) >= 6:
            months = enough.set_index("month")["ppm"]
            first, last = months.iloc[:3].median(), months.iloc[-3:].median()
            return Pulse(label, months, int(rows["listed"].sum()), last / first - 1)
    return None


def similar(listing: pd.Series, props: pd.DataFrame, n: int = 5, exclude: int | None = None):
    """The ``n`` closest properties in size and floors, same district and type, same ward first."""
    same = (props["district_name"] == listing["district_name"]) & (
        props["property_type_name"] == listing["property_type_name"]
    )
    area = float(listing["area"])
    cand = props[same & props["area"].between(area * 0.7, area * 1.3)]
    if exclude is not None:
        cand = cand[cand.index != exclude]
    if cand.empty:
        return cand
    score = np.abs(np.log(cand["area"] / area))
    floors = listing.get("floor_count")
    if pd.notna(floors):
        diff = (cand["floor_count"] - floors).abs()
        score = score + 0.15 * diff.fillna(2)
    ward = listing.get("ward_name")
    if isinstance(ward, str):
        score = score + 0.3 * (cand["ward_name"] != ward)
    # Prefer recent listings among equally close ones.
    age = (cand["last_seen"].max() - cand["last_seen"]).dt.days / 365
    score = score + 0.1 * age
    ranked = cand.assign(score=score).sort_values("score")
    # Same ward, size and price is the same unit posted under different texts.
    ranked = ranked.drop_duplicates(["ward_name", "area", "last_price"])
    return ranked.head(n)
