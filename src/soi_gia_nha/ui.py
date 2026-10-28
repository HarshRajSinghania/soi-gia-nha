"""HTML pieces for the demo. Plain functions of data, no Streamlit calls."""

from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd

from soi_gia_nha.explain import Check, format_vnd
from soi_gia_nha.market import Pulse

VERDICT_TEXT = {
    "cheap": "Rẻ hơn mặt bằng",
    "fair": "Giá hợp lý",
    "expensive": "Đắt hơn mặt bằng",
}
DATA_SPAN = "6/2025 – 3/2026"


def _pos(value: float, lo: float, hi: float) -> float:
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def _month(t: pd.Timestamp) -> str:
    return f"{t.month}/{t.year}"


def _date(t: pd.Timestamp) -> str:
    return f"{t.day}/{t.month}/{t.year}"


def _duration(days: int) -> str:
    if days < 2:
        return "trong một ngày"
    if days < 45:
        return f"{days} ngày"
    return f"{round(days / 30.4)} tháng"


def _million(x: float) -> str:
    return f"{x / 1e6:,.0f}".replace(",", ".") + " tr/m²"


def section(title: str, body: str, hint: str = "", extra_class: str = "") -> str:
    hint_html = f'<p class="sg-hint">{hint}</p>' if hint else ""
    return f'<section class="sg-block {extra_class}"><h4>{title}</h4>{hint_html}{body}</section>'


# -- verdict ----------------------------------------------------------------------------


def price_card(result: Check, area: float) -> str:
    lo = min(result.low, result.asked) * 0.92
    hi = max(result.high, result.asked) * 1.08
    left, right = _pos(result.low, lo, hi), _pos(result.high, lo, hi)
    side = "cao" if result.diff > 0 else "thấp"
    note = f"{side.capitalize()} hơn mức giữa {abs(result.diff):.0%}."
    if result.verdict == "fair":
        note = f"Nằm trong khoảng hợp lý, {side} hơn mức giữa {abs(result.diff):.0%}."
    span = f"{format_vnd(result.low)} – {format_vnd(result.high)}"
    return f"""
<div class="sg-card">
  <div class="sg-verdict sg-{result.verdict}">{VERDICT_TEXT[result.verdict]}</div>
  <div class="sg-asked">{format_vnd(result.asked)}
    <span>giá rao · {_million(result.asked / area)}</span></div>
  <p class="sg-note">{note}</p>
  <div class="sg-track">
    <div class="sg-range" style="left:{left:.1f}%;width:{right - left:.1f}%"></div>
    <div class="sg-mid" style="left:{_pos(result.mid, lo, hi):.1f}%"></div>
    <div class="sg-pin sg-{result.verdict}" style="left:{_pos(result.asked, lo, hi):.1f}%"></div>
  </div>
  <div class="sg-legend">
    <div><span>Khoảng giá hợp lý</span><b>{span}</b></div>
    <div><span>Mức giữa</span><b>{format_vnd(result.mid)}</b></div>
  </div>
</div>"""


# -- listing history ----------------------------------------------------------------------


def _steps_svg(steps: pd.DataFrame, end: pd.Timestamp) -> str:
    t0 = steps["since"].iloc[0]
    span = max((end - t0).total_seconds(), 1.0)
    lo, hi = steps["price"].min(), steps["price"].max()
    # Keep at least ±10% of the price on the axis, so a 3% cut looks like a 3% cut.
    pad = max((hi - lo) * 0.25, hi * 0.1 - (hi - lo) / 2)

    def x(t):
        return 4 + (t - t0).total_seconds() / span * 592

    def y(p):
        return 100 - (p - lo + pad) / (hi - lo + 2 * pad) * 88

    pts = []
    for i, s in steps.iterrows():
        nxt = steps["since"].iloc[i + 1] if i + 1 < len(steps) else end
        pts += [(x(s["since"]), y(s["price"])), (x(nxt), y(s["price"]))]
    line = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    dots = "".join(
        f'<circle cx="{x(s["since"]):.1f}" cy="{y(s["price"]):.1f}" r="3.5"></circle>'
        for _, s in steps.iterrows()
    )
    return (
        '<svg class="sg-steps" viewBox="0 0 600 108" preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline points="{line}"></polyline>{dots}</svg>'
    )


def history_card(summary: pd.Series, steps: pd.DataFrame) -> str:
    days = int(summary["days_listed"])
    posts = int(summary["posts"])
    facts = (
        f'<div class="sg-facts">'
        f"<div><span>Rao lần đầu</span><b>{_date(summary['first_seen'])}</b></div>"
        f"<div><span>Thời gian trên sàn</span><b>{_duration(days)}</b></div>"
        f"<div><span>Số lần đăng</span><b>{posts}</b></div>"
        "</div>"
    )
    if summary["returns"] > 0:
        story = (
            '<p class="sg-story sg-caution">Giá đi lên đi xuống qua lại giữa vài mức. '
            "Nhiều khả năng đây là vài căn cùng diện tích trong một dự án, "
            "được đăng bằng cùng một nội dung, chứ không phải một căn đổi giá.</p>"
        )
    elif summary["price_changes"] == 0:
        story = (
            f'<p class="sg-story">Đăng {posts} lần, giá giữ nguyên '
            f"{format_vnd(summary['first_price'])}.</p>"
        )
    else:
        change = float(summary["change"])
        direction = "xuống còn" if change < 0 else "lên"
        story = (
            f'<p class="sg-story">Giá đã đổi {int(summary["price_changes"])} lần, '
            f"từ {format_vnd(summary['first_price'])} {direction} "
            f"{format_vnd(summary['last_price'])} (<b>{change:+.0%}</b>).</p>"
        )

    chart = ""
    if len(steps) > 1:
        rows = "".join(
            f"<li><span>{_date(s['since'])}</span><b>{format_vnd(s['price'])}</b>"
            f"<em>{s['posts']} lần đăng</em></li>"
            for _, s in steps.iterrows()
        )
        chart = _steps_svg(steps, summary["last_seen"]) + f'<ol class="sg-steplist">{rows}</ol>'
    return section(
        "Lý lịch tin",
        facts + story + chart,
        f"Căn này đã xuất hiện trong dữ liệu {DATA_SPAN}.",
        "sg-history",
    )


def history_missing() -> str:
    return section(
        "Lý lịch tin",
        '<p class="sg-story sg-muted">Chưa thấy căn này trong 2,2 triệu tin đã rao từ '
        f"{DATA_SPAN}. Tin mới đăng, hoặc nội dung và diện tích đã khác lần rao trước.</p>",
        extra_class="sg-history",
    )


# -- ward trend ---------------------------------------------------------------------------


def _spark_svg(values: np.ndarray, marker: float | None) -> str:
    lo, hi = float(values.min()), float(values.max())
    if marker is not None:
        lo, hi = min(lo, marker), max(hi, marker)
    pad = (hi - lo) * 0.15 or hi * 0.05
    lo, hi = lo - pad, hi + pad

    def y(v):
        return 76 - (v - lo) / (hi - lo) * 68

    xs = np.linspace(4, 596, len(values))
    line = " ".join(f"{a:.1f},{y(v):.1f}" for a, v in zip(xs, values, strict=True))
    area = f"4,80 {line} 596,80"
    mark = ""
    if marker is not None:
        ym = y(marker)
        mark = f'<line class="sg-you" x1="0" x2="600" y1="{ym:.1f}" y2="{ym:.1f}"></line>'
    return (
        '<svg class="sg-spark" viewBox="0 0 600 80" preserveAspectRatio="none" aria-hidden="true">'
        f'<polygon points="{area}"></polygon><polyline points="{line}"></polyline>{mark}</svg>'
    )


def pulse_card(pulse: Pulse, listing_ppm: float) -> str:
    m = pulse.months
    first, last = _month(m.index[0]), _month(m.index[-1])
    listed = f"{pulse.listed:,}".replace(",", ".")
    head = (
        f'<div class="sg-facts">'
        f"<div><span>Giá/m² trung vị, {last}</span><b>{_million(m.iloc[-1])}</b></div>"
        f"<div><span>So với {first}</span><b>{pulse.change:+.0%}</b></div>"
        f"<div><span>Căn rao trong kỳ</span><b>{listed}</b></div>"
        "</div>"
    )
    axis = f'<div class="sg-axisline"><span>{first}</span><span>{last}</span></div>'
    key = (
        '<p class="sg-key"><i class="sg-key-line"></i>trung vị khu vực'
        f'<i class="sg-key-you"></i>căn này, {_million(listing_ppm)}</p>'
    )
    return section(
        f"Giá {escape(pulse.area)}",
        head + _spark_svg(m.to_numpy(), listing_ppm) + axis + key,
        "Giá rao trên mỗi m² của các căn cùng loại, mỗi căn tính một lần dù đăng nhiều lần.",
    )


# -- similar properties ---------------------------------------------------------------------


def comps_card(comps: pd.DataFrame, listing_ppm: float) -> str:
    if comps.empty:
        return ""
    rows = []
    for _, c in comps.iterrows():
        ppm = c["last_price"] / c["area"]
        diff = ppm / listing_ppm - 1
        bits = [f"{c['area']:g} m²"]
        if pd.notna(c["floor_count"]):
            bits.append(f"{int(c['floor_count'])} tầng")
        if isinstance(c["ward_name"], str):
            bits.append(escape(c["ward_name"]))
        reposted = f" · đăng {int(c['posts'])} lần" if c["posts"] > 1 else ""
        cls = "sg-up" if diff > 0.03 else "sg-down" if diff < -0.03 else ""
        rows.append(
            f'<li><div class="sg-comp-main"><b>{format_vnd(c["last_price"])}</b>'
            f"<span>{' · '.join(bits)}</span></div>"
            f'<div class="sg-comp-side"><span class="{cls}">{_million(ppm)}</span>'
            f"<em>{_month(c['last_seen'])}{reposted}</em></div></li>"
        )
    return section(
        "Căn giống nhất đã rao",
        f'<ul class="sg-comps">{"".join(rows)}</ul>',
        "Cùng quận và loại, diện tích gần nhất. Màu đỏ: giá/m² cao hơn căn này, xanh: thấp hơn.",
    )


# -- reasons, notes, empty state --------------------------------------------------------------


def reasons_block(result: Check) -> str:
    if not result.reasons:
        return ""
    top = max(abs(r.effect) for r in result.reasons)
    rows = []
    for r in result.reasons:
        width = abs(r.effect) / top * 50
        side = "up" if r.effect > 0 else "down"
        rows.append(
            f'<div class="sg-reason"><span class="sg-label">{escape(r.label)}</span>'
            f'<span class="sg-axis"><i class="sg-{side}" style="width:{width:.1f}%"></i></span>'
            f'<span class="sg-val sg-{side}">{r.effect:+.0%}</span></div>'
        )
    return section(
        "Vì sao ra mức giá này",
        "".join(rows),
        "So với giá/m² của một tin trung bình trong dữ liệu.",
    )


def notes_block(result: Check, new_address: str | None) -> str:
    items = [f'<div class="sg-warn">{escape(w)}</div>' for w in result.warnings]
    if new_address:
        items.append(f'<div class="sg-addr"><span>Địa chỉ sau 1/7/2025</span>{new_address}</div>')
    return "".join(items)


def empty_state() -> str:
    return """
<div class="sg-card sg-empty">
  <p>Dán một tin rao bán, hoặc bấm <b>Lấy một tin có thật</b> để xem thử.</p>
  <ul>
    <li><b>Giá này đắt hay rẻ</b> so với các căn tương tự, kèm khoảng giá hợp lý</li>
    <li><b>Lý lịch tin</b>: căn này đã rao bao lâu, đăng bao nhiêu lần, giá đổi thế nào</li>
    <li><b>Giá khu vực</b> lên hay xuống trong 10 tháng</li>
    <li><b>Những căn giống nhất</b> đã rao, để tự đối chiếu</li>
  </ul>
</div>"""
