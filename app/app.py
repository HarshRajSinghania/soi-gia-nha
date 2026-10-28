"""Streamlit demo: paste a listing, get a verdict and the reasons behind it.

streamlit run app/app.py
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from soi_gia_nha.admin import attach_new_units, build_map
from soi_gia_nha.assets import ensure_model
from soi_gia_nha.explain import Check, check, format_vnd
from soi_gia_nha.listing import build, parse_area, parse_price
from soi_gia_nha.model import PriceModel
from soi_gia_nha.text import extract, prepare_text

EXAMPLE = (
    "Bán nhà riêng Cầu Giấy, ngõ ô tô đỗ cửa, 5 tầng, 4 phòng ngủ, sổ đỏ chính chủ. "
    "Diện tích 45m2, mặt tiền 4,2m. Giá 9,5 tỷ có thương lượng."
)
NO_WARD = "Không rõ"
NO_PROJECT = "Không thuộc dự án"
VERDICT_TEXT = {
    "cheap": "Rẻ hơn mặt bằng",
    "fair": "Giá hợp lý",
    "expensive": "Đắt hơn mặt bằng",
}

st.set_page_config(page_title="Soi giá nhà", layout="wide")
st.markdown(
    f"<style>{(Path(__file__).parent / 'style.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Đang tải mô hình, lần đầu mất khoảng một phút...")
def load_model() -> PriceModel:
    return PriceModel.load(ensure_model())


@st.cache_resource(show_spinner=False)
def load_admin_map() -> pd.DataFrame | None:
    try:
        return build_map(["Hà Nội", "Hồ Chí Minh"])
    except OSError:  # offline: the new-ward lookup is a bonus, not a requirement
        return None


def wards_by_district(model: PriceModel) -> dict[tuple[str, str], list[str]]:
    idx = model.ward_medians.index.to_frame(index=False)
    return {
        (t, d): sorted(g["ward_name"].unique())
        for (t, d), g in idx.groupby(["property_type_name", "district_name"])
    }


def districts_for(province: str, model: PriceModel) -> list[str]:
    # Ho Chi Minh City numbers its inner districts ("1", "10"), sort those numerically.
    return sorted(
        model.districts[province],
        key=lambda d: (not d.isdigit(), int(d) if d.isdigit() else 0, d),
    )


def district_label(d: str) -> str:
    return f"Quận {d}" if d.isdigit() else d


def _pos(value: float, lo: float, hi: float) -> float:
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


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
    <span>giá rao · {result.asked / area / 1e6:,.0f} triệu/m²</span></div>
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
    return (
        '<div class="sg-section"><h4>Vì sao ra mức giá này</h4>'
        '<p class="sg-hint">So với giá/m² của một tin trung bình trong dữ liệu.</p>'
        + "".join(rows)
        + "</div>"
    )


def notes_block(result: Check, new_address: str | None) -> str:
    items = [f'<div class="sg-warn">{escape(w)}</div>' for w in result.warnings]
    if new_address:
        items.append(f'<div class="sg-addr"><span>Địa chỉ sau 1/7/2025</span>{new_address}</div>')
    return "".join(items)


def new_address_for(row: pd.DataFrame, ward: str | None) -> str | None:
    admin_map = load_admin_map()
    if admin_map is None or ward is None:
        return None
    new = attach_new_units(row, admin_map).iloc[0]
    if pd.isna(new["new_ward"]):
        return None
    wards = " hoặc ".join(escape(w) for w in new["new_ward"].split(" / "))
    return f"<b>{wards}</b>, {escape(new['new_province'])}"


def empty_state() -> str:
    return """
<div class="sg-card sg-empty">
  <p>Kết quả sẽ hiện ở đây.</p>
  <ul>
    <li>Khoảng giá hợp lý cho căn này</li>
    <li>Giá rao đang cao hay thấp hơn bao nhiêu</li>
    <li>Những yếu tố đẩy giá lên, kéo giá xuống</li>
    <li>Tên phường mới sau sắp xếp hành chính</li>
  </ul>
</div>"""


def main() -> None:
    st.markdown(
        '<header class="sg-top"><div class="sg-brand">Soi giá nhà</div>'
        '<div class="sg-tag">Tin này đắt hay rẻ? So với 1,5 triệu tin rao bán ở Hà Nội và '
        "TP.HCM, kèm lý do.</div></header>",
        unsafe_allow_html=True,
    )

    model = load_model()
    wards = wards_by_district(model)
    left, right = st.columns([5, 6], gap="large")

    with left:
        text = st.text_area("Nội dung tin đăng", value=EXAMPLE, height=150)
        feats = extract(prepare_text(pd.Series([""]), pd.Series([text]))).iloc[0]

        c1, c2 = st.columns(2)
        province = c1.selectbox("Thành phố", ["Hà Nội", "Hồ Chí Minh"])
        types = model.categories["property_type_name"]
        property_type = c2.selectbox("Loại", types, index=types.index("Nhà"))
        districts = districts_for(province, model)
        default_d = districts.index("Cầu Giấy") if "Cầu Giấy" in districts else 0
        district = c1.selectbox(
            "Quận, huyện", districts, index=default_d, format_func=district_label
        )
        ward = c2.selectbox("Phường, xã", [NO_WARD] + wards.get((property_type, district), []))
        ward = None if ward == NO_WARD else ward
        project = None
        if property_type == "Căn hộ chung cư":
            project = st.selectbox("Dự án", [NO_PROJECT] + model.categories["project_name"])
            project = None if project == NO_PROJECT else project
        st.caption("Dùng tên quận, phường cũ như trong tin đăng (trước 1/7/2025).")

        c1, c2, c3 = st.columns([4, 4, 3])
        price_bn = c1.number_input(
            "Giá rao, tỷ", min_value=0.0, value=round((parse_price(text) or 0) / 1e9, 3), step=0.1
        )
        area = c2.number_input("Diện tích, m²", min_value=0.0, value=float(parse_area(text) or 0))
        floors = c3.number_input(
            "Số tầng",
            min_value=0,
            value=int(feats["txt_floors"]) if pd.notna(feats["txt_floors"]) else 0,
        )
        st.caption("Ba ô trên được đọc tự động từ tin, sửa lại nếu chưa đúng.")
        clicked = st.button("Soi giá", type="primary", width="stretch")

    with right:
        if not clicked:
            st.markdown(empty_state(), unsafe_allow_html=True)
        elif price_bn <= 0 or area <= 0:
            st.error("Tin chưa có giá hoặc diện tích. Điền vào hai ô bên trái rồi thử lại.")
        else:
            row = build(
                text,
                province=province,
                district=district,
                ward=ward,
                project=project,
                property_type=property_type,
                price=price_bn * 1e9,
                area=area,
                floor_count=floors or None,
            )
            result = check(model, row)
            st.markdown(
                price_card(result, area)
                + reasons_block(result)
                + notes_block(result, new_address_for(row, ward)),
                unsafe_allow_html=True,
            )

    st.markdown(
        '<footer class="sg-foot">So với <b>giá rao</b> của các tin đăng từ 6/2025 đến 3/2026, '
        "không phải giá giao dịch và không thay cho thẩm định. Sai số trung vị khoảng 12% "
        "(căn hộ khoảng 7%). Dữ liệu: "
        '<a href="https://huggingface.co/datasets/tinixai/vietnam-real-estates">TiniX AI</a>, '
        "CC BY-NC 4.0 · "
        '<a href="https://github.com/HongTin2104/soi-gia-nha">Mã nguồn</a></footer>',
        unsafe_allow_html=True,
    )


main()
