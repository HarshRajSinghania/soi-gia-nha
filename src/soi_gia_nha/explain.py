"""Verdict and reasons for a single listing.

Contributions come from LightGBM's built-in TreeSHAP (``pred_contrib=True``) on the ``mid``
model. They are in log price per m2, so each one reads as a percentage: +0.10 means
"about 10% more per m2 than a typical listing of this kind in the training data".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .model import PriceModel

# Features grouped into reasons a buyer recognises.
GROUPS = {
    "location": [
        "province_name",
        "district_name",
        "ward_name",
        "ward_median",
        "district_median",
        "project_name",
    ],
    "type": ["property_type_name"],
    "size": ["log_area"],
    "floors": ["floor_count"],
    "rooms": ["bedroom_count", "bathroom_count"],
    "frontage": ["frontage_width", "house_depth"],
    "road": ["road_width"],
    "direction": ["house_direction", "balcony_direction"],
    "month": ["month"],
    "legal_book": ["legal_book"],
    "legal_weak": ["legal_weak"],
    "car_access": ["car_access"],
    "main_street": ["main_street"],
    "alley": ["alley"],
    "corner": ["corner"],
    "elevator": ["elevator"],
    "furnished": ["furnished"],
    "business": ["business"],
    "urgent": ["urgent"],
}

LABELS_VI = {
    "location": "Vị trí (quận, phường, dự án)",
    "type": "Loại bất động sản",
    "size": "Diện tích",
    "floors": "Số tầng",
    "rooms": "Số phòng",
    "frontage": "Mặt tiền, chiều sâu",
    "road": "Độ rộng đường, hẻm",
    "direction": "Hướng nhà",
    "month": "Thời điểm đăng",
    "legal_book": "Có sổ hồng / sổ đỏ",
    "legal_weak": "Giấy tờ yếu (sổ chung, vi bằng)",
    "car_access": "Ô tô vào được",
    "main_street": "Mặt phố, mặt đường",
    "alley": "Nhà trong ngõ, hẻm",
    "corner": "Lô góc",
    "elevator": "Thang máy",
    "furnished": "Đầy đủ nội thất",
    "business": "Kinh doanh được",
    "urgent": 'Ghi "bán gấp", "cắt lỗ"',
}

# Asking price vs the predicted range.
VERDICTS_VI = {
    "cheap": "Rẻ hơn mặt bằng",
    "fair": "Hợp lý",
    "expensive": "Đắt hơn mặt bằng",
}
# Far enough outside the range that the listing itself is probably wrong.
SUSPICIOUS_RATIO = 2.5


@dataclass
class Reason:
    group: str
    label: str
    effect: float  # relative change in price per m2, e.g. 0.12 = +12%


@dataclass
class Check:
    asked: float
    low: float
    mid: float
    high: float
    verdict: str
    diff: float  # asked / mid - 1
    reasons: list[Reason] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def verdict_vi(self) -> str:
        return VERDICTS_VI[self.verdict]


def contributions(model: PriceModel, df: pd.DataFrame) -> pd.DataFrame:
    """TreeSHAP values per feature (log price per m2) plus the ``bias`` column."""
    booster = model.boosters["mid"]
    X = model.features(df)
    raw = booster.predict(X, pred_contrib=True, num_iteration=booster.best_iteration)
    return pd.DataFrame(raw, index=df.index, columns=[*X.columns, "bias"])


def group_reasons(contrib: pd.Series, top: int = 5, min_effect: float = 0.02) -> list[Reason]:
    reasons = []
    for group, cols in GROUPS.items():
        phi = float(contrib[[c for c in cols if c in contrib.index]].sum())
        effect = float(np.expm1(phi))
        if abs(effect) >= min_effect:
            reasons.append(Reason(group, LABELS_VI[group], effect))
    reasons.sort(key=lambda r: abs(r.effect), reverse=True)
    return reasons[:top]


def verdict(asked: float, low: float, high: float) -> str:
    if asked < low:
        return "cheap"
    if asked > high:
        return "expensive"
    return "fair"


def warnings_for(row: pd.Series, asked: float, low: float, high: float) -> list[str]:
    out = []
    if asked < low / SUSPICIOUS_RATIO:
        out.append(
            "Giá thấp bất thường so với khu vực. Có thể giá đang ghi theo m², "
            "thiếu một số 0, hoặc là tin câu khách."
        )
    if asked > high * SUSPICIOUS_RATIO:
        out.append("Giá cao bất thường so với khu vực. Kiểm tra lại diện tích và đơn vị giá.")
    if row.get("legal_weak"):
        out.append("Tin nhắc tới sổ chung, vi bằng hoặc hợp đồng mua bán: kiểm tra kỹ pháp lý.")
    if row.get("urgent") and asked < low:
        out.append('Tin ghi "bán gấp" và giá dưới mặt bằng: nên hỏi rõ lý do bán.')
    return out


def check(model: PriceModel, listing: pd.DataFrame) -> Check:
    """Full check of one listing. ``listing`` is a one-row frame with the model columns."""
    if len(listing) != 1:
        raise ValueError("check() expects exactly one listing")
    row = listing.iloc[0]
    pred = model.predict(listing).iloc[0]
    asked = float(row["price"])
    c = contributions(model, listing).iloc[0]
    return Check(
        asked=asked,
        low=float(pred["low"]),
        mid=float(pred["mid"]),
        high=float(pred["high"]),
        verdict=verdict(asked, pred["low"], pred["high"]),
        diff=asked / pred["mid"] - 1,
        reasons=group_reasons(c),
        warnings=warnings_for(row, asked, pred["low"], pred["high"]),
    )


def format_vnd(v: float) -> str:
    """9_100_000_000 -> "9,1 tỷ", 850_000_000 -> "850 triệu"."""
    if v >= 1e9:
        s = f"{v / 1e9:.2f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") + " tỷ"
    return f"{v / 1e6:.0f} triệu"


def summary_vi(result: Check) -> str:
    """Plain Vietnamese explanation, built from the numbers only (no LLM needed)."""
    pct = abs(result.diff)
    head = {
        "cheap": f"Giá rao thấp hơn mức dự đoán khoảng {pct:.0%}",
        "fair": "Giá rao nằm trong khoảng hợp lý",
        "expensive": f"Giá rao cao hơn mức dự đoán khoảng {pct:.0%}",
    }[result.verdict]
    lines = [
        f"{head}. Khoảng giá hợp lý: {format_vnd(result.low)} – {format_vnd(result.high)}, "
        f"mức giữa {format_vnd(result.mid)}."
    ]
    ups = [r for r in result.reasons if r.effect > 0]
    downs = [r for r in result.reasons if r.effect < 0]
    if ups:
        lines.append(
            "Đẩy giá lên: " + ", ".join(f"{r.label.lower()} (+{r.effect:.0%})" for r in ups) + "."
        )
    if downs:
        lines.append(
            "Kéo giá xuống: "
            + ", ".join(f"{r.label.lower()} ({r.effect:.0%})" for r in downs)
            + "."
        )
    lines.extend(result.warnings)
    return "\n".join(lines)
