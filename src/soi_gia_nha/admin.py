"""Map pre-July-2025 addresses (province / district / ward) to the new units.

Vietnam merged its provinces from 63 to 34 and removed the district level on 1 July 2025.
The listings still use the old names, people now search with the new ones.

Sources, downloaded at build time and not redistributed here:

- old units with district codes: daohoangson/dvhcvn, tag v20250301 (GPL-3.0)
- old ward -> new ward: dvhcvn/20250701 (MIT), built from the National Assembly resolutions
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

from .data import PROCESSED_DIR, RAW_DIR

OLD_UNITS_URL = "https://raw.githubusercontent.com/daohoangson/dvhcvn/v20250301/data/sorted.json"
SPLITS_URL = "https://raw.githubusercontent.com/dvhcvn/20250701/main/mapping/splits.json"

_PREFIX = re.compile(r"^(thành phố|tỉnh|quận|huyện|thị xã|phường|xã|thị trấn|tp\.?)\s+")
# Old style puts the tone on the first vowel of open oa/oe/uy ("Hòa"), new style on the
# second ("Hoà"). Sources mix both, so compare in one style.
_OLD_TONE = {
    "òa": "oà", "óa": "oá", "ỏa": "oả", "õa": "oã", "ọa": "oạ",
    "òe": "oè", "óe": "oé", "ỏe": "oẻ", "õe": "oẽ", "ọe": "oẹ",
    "ùy": "uỳ", "úy": "uý", "ủy": "uỷ", "ũy": "uỹ", "ụy": "uỵ",
}  # fmt: skip
_OLD_TONE_RE = re.compile("(" + "|".join(_OLD_TONE) + r")(?![a-zà-ỹ])")


def canon(name: object) -> str | None:
    """Comparable form of a unit name: "Phường 07" -> "7", "Q. Trung Hòa" -> "trung hoà"."""
    if name is None or (isinstance(name, float) and name != name):
        return None
    s = unicodedata.normalize("NFC", str(name)).strip().lower()
    s = _PREFIX.sub("", s)
    s = re.sub(r"^0+(?=\d)", "", s)
    s = _OLD_TONE_RE.sub(lambda m: _OLD_TONE[m.group(1)], s)
    return re.sub(r"\s+", " ", s) or None


def _fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def build_map(provinces: list[str] | None = None, cache: Path = RAW_DIR / "admin") -> pd.DataFrame:
    """One row per old ward: canonical old keys plus the new province and ward(s).

    A few old wards were split between several new ones. Those get every candidate in
    ``new_ward`` joined by " / " and ``ambiguous=True``.
    """
    old = json.loads(_fetch(OLD_UNITS_URL, cache / "sorted.json").read_text("utf-8"))
    splits = json.loads(_fetch(SPLITS_URL, cache / "splits.json").read_text("utf-8"))["data"]

    new_by_ward: dict[str, list[str]] = {}
    new_province: dict[str, str] = {}
    for prov in splits:
        new_province[prov["level1_id"]] = prov["splits"][0]["name"]
        for w in prov["level3s"]:
            new_by_ward[w["level3_id"]] = [s["name"] for s in w["splits"]]

    wanted = {canon(p) for p in provinces} if provinces else None
    rows = []
    for p_id, p_name, _, _, districts in old:
        if wanted and canon(p_name) not in wanted:
            continue
        for _, d_name, _, _, wards in districts:
            for w_id, w_name, *_ in wards:
                new = new_by_ward.get(w_id, [])
                rows.append(
                    {
                        "province_key": canon(p_name),
                        "district_key": canon(d_name),
                        "ward_key": canon(w_name),
                        "new_province": new_province.get(p_id),
                        "new_ward": " / ".join(new) or None,
                        "ambiguous": len(new) > 1,
                    }
                )
    return pd.DataFrame(rows)


def attach_new_units(df: pd.DataFrame, admin_map: pd.DataFrame) -> pd.DataFrame:
    """Add ``new_province``, ``new_ward`` and ``ambiguous`` columns to the listings."""
    keys = pd.DataFrame(
        {
            "province_key": df["province_name"].map(canon),
            "district_key": df["district_name"].map(canon),
            "ward_key": df["ward_name"].map(canon),
        },
        index=df.index,
    )
    merged = keys.merge(
        admin_map.drop_duplicates(["province_key", "district_key", "ward_key"]),
        how="left",
        on=["province_key", "district_key", "ward_key"],
    )
    out = df.copy()
    for col in ("new_province", "new_ward", "ambiguous"):
        out[col] = merged[col].to_numpy()
    out["ambiguous"] = out["ambiguous"].fillna(False).astype(bool)
    return out


def save_map(admin_map: pd.DataFrame, dest: Path = PROCESSED_DIR / "admin_map.parquet") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    admin_map.to_parquet(dest, index=False)
    return dest
