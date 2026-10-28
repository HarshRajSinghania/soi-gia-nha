"""Listing history: recognise the same property across reposts.

Agents repost the same property again and again so it looks fresh. Two posts are treated
as the same property when they share district, ward, property type and exact area, and
either the description or the title matches once numbers, punctuation and case are
ignored. Dropping the numbers matters: a price cut usually edits the number and nothing
else.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
import pandas as pd

BLOCK = ["district_name", "ward_name", "property_type_name", "area"]
MIN_TEXT = 30  # shorter texts ("Bán nhà", "Cần bán gấp") are too generic to link on
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NON_WORD = re.compile(r"[^\w]+")


def fingerprint(text: str | None, length: int = 200) -> str:
    """Normalised start of a text, without numbers. Empty when too short to be specific."""
    if not isinstance(text, str):
        return ""
    t = _NUMBER.sub(" ", text.lower())
    t = " ".join(_NON_WORD.sub(" ", t).split())[:length]
    return t if len(t) >= MIN_TEXT else ""


def text_hash(texts: pd.Series) -> pd.Series:
    """64-bit hash of each fingerprint, 0 for none. Stable across runs and machines."""

    def h(t: str) -> int:
        if not t:
            return 0
        return int.from_bytes(
            hashlib.blake2b(t.encode(), digest_size=8).digest(), "little", signed=True
        )

    return texts.map(fingerprint).map(h).astype("int64")


def property_ids(df: pd.DataFrame) -> np.ndarray:
    """Connected components over two links: same block + same description, or same block +
    same title. Expects ``desc_hash`` and ``title_hash`` columns."""
    labels = np.arange(len(df))
    keys = []
    for col in ("desc_hash", "title_hash"):
        k = df.groupby([*BLOCK, col], dropna=False, sort=False).ngroup().to_numpy()
        keys.append(np.where(df[col].to_numpy() != 0, k, -1))
    # Label propagation: every row takes the smallest label among rows sharing a key.
    # Two keys link at most a few posts, so this settles in a handful of rounds.
    while True:
        before = labels.copy()
        for k in keys:
            valid = k >= 0
            m = pd.Series(labels[valid]).groupby(k[valid]).transform("min").to_numpy()
            labels[valid] = np.minimum(labels[valid], m)
        if np.array_equal(before, labels):
            break
    return pd.factorize(labels)[0]


def add_ids(df: pd.DataFrame) -> pd.DataFrame:
    out = df.assign(
        desc_hash=text_hash(df["description"]),
        title_hash=text_hash(df["name"]),
    )
    out["property_id"] = property_ids(out)
    return out


def price_steps(posts: pd.DataFrame) -> pd.DataFrame:
    """Collapse a property's posts into price steps: when each asking price first appeared,
    and how many times it was posted."""
    p = posts.sort_values("published_at")
    step = (p["price"] != p["price"].shift()).cumsum()
    return (
        p.groupby(step)
        .agg(
            since=("published_at", "first"),
            until=("published_at", "last"),
            price=("price", "first"),
            posts=("price", "size"),
        )  # fmt: skip
        .reset_index(drop=True)
    )


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """One row per property with posting and price history."""
    d = df.sort_values("published_at", kind="stable")
    g = d.groupby("property_id")
    out = g.agg(
        posts=("price", "size"),
        first_seen=("published_at", "first"),
        last_seen=("published_at", "last"),
        first_price=("price", "first"),
        last_price=("price", "last"),
        min_price=("price", "min"),
        max_price=("price", "max"),
    )
    prev = g["price"].shift()
    changed = d["price"].ne(prev) & prev.notna()
    out["price_changes"] = changed.groupby(d["property_id"]).sum()
    # A real property rarely goes back to a price it already left. Prices that alternate
    # (4.2, 5.7, 4.2, 5.7) are usually several units of one project posted from the same
    # template, merged here because they share ward and area.
    steps = d[d["price"].ne(prev)]
    out["returns"] = steps.duplicated(["property_id", "price"]).groupby(steps["property_id"]).sum()
    out["days_listed"] = (out["last_seen"] - out["first_seen"]).dt.days
    out["change"] = out["last_price"] / out["first_price"] - 1
    return out


def match(listing: pd.Series, index: pd.DataFrame) -> int | None:
    """Property id of a listing in ``index`` (posts with BLOCK columns and both hashes).

    The index may store the hashes truncated to 32 bits, as the app data does."""
    desc = text_hash(pd.Series([listing.get("description")])).iloc[0]
    title = text_hash(pd.Series([listing.get("name")])).iloc[0]
    if not desc and not title:
        return None
    if index["desc_hash"].dtype == np.uint32:
        desc, title = desc & 0xFFFFFFFF, title & 0xFFFFFFFF
    district = index["district_name"].eq(listing["district_name"]) & index["property_type_name"].eq(
        listing["property_type_name"]
    )
    same = district & np.isclose(index["area"], listing["area"])
    ward = listing.get("ward_name")
    if isinstance(ward, str):
        same &= index["ward_name"].eq(ward)
    by_desc = (index["desc_hash"] == desc) & (desc != 0)
    hit = index[same & (by_desc | ((index["title_hash"] == title) & (title != 0)))]
    if hit.empty:
        # The area typed in a pasted listing often differs from the one the seller entered
        # in the form. A full description match in the same district is specific enough.
        hit = index[district & by_desc]
    if hit.empty:
        return None
    return int(hit["property_id"].mode().iloc[0])
