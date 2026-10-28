"""Streamlit demo: paste a listing, get a verdict and the reasons behind it.

streamlit run app/app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from soi_gia_nha.admin import attach_new_units, build_map
from soi_gia_nha.assets import ensure_model
from soi_gia_nha.explain import check, format_vnd, summary_vi
from soi_gia_nha.listing import build, parse_area, parse_price
from soi_gia_nha.model import PriceModel
from soi_gia_nha.text import extract, prepare_text

EXAMPLE = (
    "Bán nhà riêng Cầu Giấy, ngõ ô tô đỗ cửa, 5 tầng, 4 phòng ngủ, sổ đỏ chính chủ. "
    "Diện tích 45m2, mặt tiền 4,2m. Giá 9,5 tỷ có thương lượng."
)
VERDICT_COLOR = {"cheap": "#1a7f37", "fair": "#9a6700", "expensive": "#cf222e"}

st.set_page_config(page_title="Soi giá nhà", page_icon="🏠", layout="centered")


@st.cache_resource(show_spinner="Đang tải mô hình (lần đầu mất khoảng 1 phút)...")
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


def range_chart(result) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[result.high - result.low],
            base=[result.low],
            y=["Giá"],
            orientation="h",
            marker_color="rgba(120,120,120,0.25)",
            hoverinfo="skip",
            name="Khoảng hợp lý",
        )
    )
    for value, label, color in [
        (result.mid, "Dự đoán", "#57606a"),
        (result.asked, "Giá rao", VERDICT_COLOR[result.verdict]),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[value],
                y=["Giá"],
                mode="markers+text",
                marker={"size": 16, "color": color, "symbol": "diamond"},
                text=[f"{label}<br>{format_vnd(value)}"],
                textposition="top center",
                name=label,
                hovertemplate=f"{label}: {format_vnd(value)}<extra></extra>",
            )
        )
    lo = min(result.low, result.asked) * 0.9
    hi = max(result.high, result.asked) * 1.1
    fig.update_layout(
        height=170,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        showlegend=False,
        xaxis={"range": [lo, hi], "tickformat": ".3s", "title": "VND"},
        yaxis={"visible": False},
    )
    return fig


def reasons_chart(result) -> go.Figure:
    reasons = list(reversed(result.reasons))
    fig = go.Figure(
        go.Bar(
            x=[r.effect * 100 for r in reasons],
            y=[r.label for r in reasons],
            orientation="h",
            marker_color=["#cf222e" if r.effect > 0 else "#1a7f37" for r in reasons],
            text=[f"{r.effect:+.0%}" for r in reasons],
            textposition="outside",
            hovertemplate="%{y}: %{x:+.0f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=60 + 40 * len(reasons),
        margin={"l": 10, "r": 40, "t": 10, "b": 10},
        xaxis={"title": "% giá/m² so với tin trung bình", "zeroline": True},
    )
    return fig


def main() -> None:
    st.title("Soi giá nhà")
    st.caption(
        "Tin này đắt hay rẻ? Dán nội dung tin rao bán ở Hà Nội hoặc TP.HCM, "
        "mô hình so với 1,5 triệu tin đã đăng và giải thích vì sao."
    )

    model = load_model()
    wards = wards_by_district(model)

    text = st.text_area("Nội dung tin đăng", value=EXAMPLE, height=140)
    feats = extract(prepare_text(pd.Series([""]), pd.Series([text]))).iloc[0]

    c1, c2 = st.columns(2)
    province = c1.selectbox("Tỉnh / thành", ["Hà Nội", "Hồ Chí Minh"])
    types = model.categories["property_type_name"]
    property_type = c2.selectbox("Loại", types, index=types.index("Nhà"))
    districts = districts_for(province, model)
    default_d = districts.index("Cầu Giấy") if "Cầu Giấy" in districts else 0
    district = c1.selectbox(
        "Quận / huyện (tên cũ, trước 1/7/2025)",
        districts,
        index=default_d,
        format_func=district_label,
    )
    ward_options = ["(không rõ)"] + wards.get((property_type, district), [])
    ward = c2.selectbox("Phường / xã (tên cũ)", ward_options)
    project = None
    if property_type == "Căn hộ chung cư":
        project = st.selectbox("Dự án (nếu có)", ["(không có)"] + model.categories["project_name"])
        project = None if project == "(không có)" else project

    st.markdown("**Thông tin đọc được từ tin** (sửa nếu sai)")
    c1, c2, c3 = st.columns(3)
    price_bn = c1.number_input(
        "Giá rao (tỷ)", min_value=0.0, value=round((parse_price(text) or 0) / 1e9, 3), step=0.1
    )
    area = c2.number_input("Diện tích (m²)", min_value=0.0, value=float(parse_area(text) or 0))
    floors = c3.number_input(
        "Số tầng",
        min_value=0,
        value=int(feats["txt_floors"] or 0) if pd.notna(feats["txt_floors"]) else 0,
    )

    if not st.button("Soi giá", type="primary", width="stretch"):
        return
    if price_bn <= 0 or area <= 0:
        st.error("Cần có giá và diện tích. Nhập vào ô bên trên nếu tin không ghi rõ.")
        return

    row = build(
        text,
        province=province,
        district=district,
        ward=None if ward == "(không rõ)" else ward,
        project=project,
        property_type=property_type,
        price=price_bn * 1e9,
        area=area,
        floor_count=floors or None,
    )
    result = check(model, row)

    color = VERDICT_COLOR[result.verdict]
    st.markdown(
        f"<h3 style='color:{color};margin-bottom:0'>{result.verdict_vi} "
        f"<small>({result.diff:+.0%} so với dự đoán)</small></h3>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(range_chart(result), width="stretch")
    st.write(summary_vi(result).replace("\n", "  \n"))
    if result.reasons:
        st.markdown("**Vì sao mô hình ra mức giá này**")
        st.plotly_chart(reasons_chart(result), width="stretch")

    admin_map = load_admin_map()
    if admin_map is not None and ward != "(không rõ)":
        new = attach_new_units(row, admin_map).iloc[0]
        if pd.notna(new["new_ward"]):
            note = (
                " (phường cũ bị chia, có thể thuộc một trong các phường này)"
                if new["ambiguous"]
                else ""
            )
            st.info(
                f"Địa chỉ sau sắp xếp 1/7/2025: **{new['new_ward']}**, {new['new_province']}{note}"
            )

    with st.expander("Mô hình làm gì, và không làm gì"):
        st.markdown(
            "- So với **giá rao** của các tin khác từ 6/2025 đến 3/2026, không phải giá giao dịch "
            "thật và không phải thẩm định giá.\n"
            "- Sai số trung vị khoảng 12% trên tin tháng 3/2026 (căn hộ khoảng 7%). "
            "Khoảng hợp lý chứa giá rao của khoảng 78% số tin.\n"
            '- "Vì sao" là giá trị SHAP: mỗi yếu tố làm giá/m² cao hay thấp hơn tin trung bình '
            "trong dữ liệu bao nhiêu phần trăm.\n"
            "- Dữ liệu: [TiniX AI, CC BY-NC 4.0]"
            "(https://huggingface.co/datasets/tinixai/vietnam-real-estates). "
            "Mã nguồn: [GitHub](https://github.com/HongTin2104/soi-gia-nha)."
        )


main()
