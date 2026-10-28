"""Streamlit demo: paste a listing, get a verdict, its posting history and the market around it.

streamlit run app/app.py
"""

from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from soi_gia_nha import ui
from soi_gia_nha.admin import attach_new_units, build_map
from soi_gia_nha.assets import ensure_data, ensure_model
from soi_gia_nha.explain import check
from soi_gia_nha.history import BLOCK, match, price_steps
from soi_gia_nha.listing import build, parse_area, parse_price
from soi_gia_nha.market import pulse_for, similar
from soi_gia_nha.model import PriceModel
from soi_gia_nha.text import extract, prepare_text

EXAMPLE = (
    "Bán nhà riêng Cầu Giấy, ngõ ô tô đỗ cửa, 5 tầng, 4 phòng ngủ, sổ đỏ chính chủ. "
    "Diện tích 45m2, mặt tiền 4,2m. Giá 9,5 tỷ có thương lượng."
)
NO_WARD = "Không rõ"
NO_PROJECT = "Không thuộc dự án"

st.set_page_config(page_title="Soi giá nhà", layout="wide")
st.markdown(
    f"<style>{(Path(__file__).parent / 'style.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Đang tải mô hình, lần đầu mất khoảng một phút...")
def load_model() -> PriceModel:
    return PriceModel.load(ensure_model())


@st.cache_resource(show_spinner="Đang tải dữ liệu 1,4 triệu căn...")
def load_market():
    """Property tables for the history and market sections. ``None`` if unavailable: the
    price check still works without them."""
    try:
        d = ensure_data()
    except OSError:
        return None
    props = pd.read_parquet(d / "properties.parquet")
    posts = pd.read_parquet(d / "posts.parquet")
    index = posts.join(props[BLOCK], on="property_id")
    return {
        "props": props,
        "posts": posts,
        "index": index,
        "pulse": pd.read_parquet(d / "pulse.parquet"),
        "samples": pd.read_parquet(d / "samples.parquet"),
    }


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


def split_listing(text: str) -> tuple[str, str]:
    """Title and body of a pasted listing: the first line is usually the title."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) > 1:
        return lines[0], " ".join(lines[1:])
    return text, text


def text_tag(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:8]


def default(key: str, value) -> dict:
    """Widget arguments: the parsed value, unless the sample button already set one."""
    return {"key": key} if key in st.session_state else {"key": key, "value": value}


def load_sample() -> None:
    market = load_market()
    s = market["samples"].sample(1).iloc[0]
    text = f"{s['name']}\n\n{s['description']}"
    # Use the seller's own price and area: reading them back from the text is less exact.
    tag = text_tag(text)
    st.session_state[f"price_{tag}"] = round(s["price"] / 1e9, 3)
    st.session_state[f"area_{tag}"] = float(s["area"])
    st.session_state.update(
        text=text,
        province=s["province_name"],
        ptype=s["property_type_name"],
        district=s["district_name"],
        ward=s["ward_name"] if isinstance(s["ward_name"], str) else NO_WARD,
        project=NO_PROJECT,
        run=True,
    )


def new_address_for(row: pd.DataFrame, ward: str | None) -> str | None:
    admin_map = load_admin_map()
    if admin_map is None or ward is None:
        return None
    new = attach_new_units(row, admin_map).iloc[0]
    if pd.isna(new["new_ward"]):
        return None
    wards = " hoặc ".join(escape(w) for w in new["new_ward"].split(" / "))
    return f"<b>{wards}</b>, {escape(new['new_province'])}"


def market_sections(market, listing: pd.Series, asked: float) -> str:
    props, pulse = market["props"], market["pulse"]
    ppm = asked / listing["area"]
    html = []
    pid = match(listing, market["index"])
    if pid is None:
        html.append(ui.history_missing())
    else:
        steps = price_steps(market["posts"][market["posts"]["property_id"] == pid])
        html.append(ui.history_card(props.loc[pid], steps))
    p = pulse_for(
        pulse, listing["district_name"], listing.get("ward_name"), listing["property_type_name"]
    )
    if p is not None:
        html.append(ui.pulse_card(p, ppm))
    html.append(ui.comps_card(similar(listing, props, exclude=pid), ppm))
    return "".join(html)


def keep_valid(key: str, options: list[str], default: str) -> None:
    """Session values set by the sample button may not exist in the current option list."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = default if default in options else options[0]


def main() -> None:
    st.markdown(
        '<header class="sg-top"><div class="sg-brand">Soi giá nhà</div>'
        '<div class="sg-tag">Tin này đắt hay rẻ, đã rao bao lâu, giá đổi mấy lần? '
        "Tra trên 2,2 triệu tin rao bán ở Hà Nội và TP.HCM.</div></header>",
        unsafe_allow_html=True,
    )

    model = load_model()
    market = load_market()
    wards = wards_by_district(model)
    st.session_state.setdefault("text", EXAMPLE)
    left, right = st.columns([5, 6], gap="large")

    with left:
        if market is not None:
            st.button("Lấy một tin có thật để thử", on_click=load_sample, width="stretch")
        text = st.text_area("Nội dung tin đăng", key="text", height=170)
        feats = extract(prepare_text(pd.Series([""]), pd.Series([text]))).iloc[0]

        c1, c2 = st.columns(2)
        keep_valid("province", ["Hà Nội", "Hồ Chí Minh"], "Hà Nội")
        province = c1.selectbox("Thành phố", ["Hà Nội", "Hồ Chí Minh"], key="province")
        types = model.categories["property_type_name"]
        keep_valid("ptype", types, "Nhà")
        property_type = c2.selectbox("Loại", types, key="ptype")
        districts = districts_for(province, model)
        keep_valid("district", districts, "Cầu Giấy")
        district = c1.selectbox(
            "Quận, huyện", districts, key="district", format_func=district_label
        )
        ward_options = [NO_WARD] + wards.get((property_type, district), [])
        keep_valid("ward", ward_options, NO_WARD)
        ward = c2.selectbox("Phường, xã", ward_options, key="ward")
        ward = None if ward == NO_WARD else ward
        project = None
        if property_type == "Căn hộ chung cư":
            projects = [NO_PROJECT] + model.categories["project_name"]
            keep_valid("project", projects, NO_PROJECT)
            project = st.selectbox("Dự án", projects, key="project")
            project = None if project == NO_PROJECT else project
        st.caption("Dùng tên quận, phường cũ như trong tin đăng (trước 1/7/2025).")

        # Keyed by the text so the parsed values refresh when a new listing is pasted.
        tag = text_tag(text)
        c1, c2, c3 = st.columns([4, 4, 3])
        price_bn = c1.number_input(
            "Giá rao, tỷ",
            min_value=0.0,
            step=0.1,
            **default(f"price_{tag}", round((parse_price(text) or 0) / 1e9, 3)),
        )
        area = c2.number_input(
            "Diện tích, m²", min_value=0.0, **default(f"area_{tag}", float(parse_area(text) or 0))
        )
        floors = c3.number_input(
            "Số tầng",
            min_value=0,
            value=int(feats["txt_floors"]) if pd.notna(feats["txt_floors"]) else 0,
            key=f"floors_{tag}",
        )
        st.caption("Ba ô trên được đọc tự động từ tin, sửa lại nếu chưa đúng.")
        if st.button("Soi giá", type="primary", width="stretch"):
            st.session_state["run"] = True

    with right:
        if not st.session_state.get("run"):
            st.markdown(ui.empty_state(), unsafe_allow_html=True)
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
            html = ui.price_card(result, area)
            if market is not None:
                title, body = split_listing(text)
                listing = row.iloc[0].copy()
                listing["name"], listing["description"] = title, body
                html += market_sections(market, listing, result.asked)
            html += ui.reasons_block(result) + ui.notes_block(result, new_address_for(row, ward))
            st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        '<footer class="sg-foot">So với <b>giá rao</b> của các tin đăng từ 6/2025 đến 3/2026, '
        "không phải giá giao dịch và không thay cho thẩm định. Sai số trung vị khoảng 12% "
        "(căn hộ khoảng 7%). Một căn được coi là đăng lại khi trùng phường, loại, diện tích và "
        "nội dung hoặc tiêu đề. Dữ liệu: "
        '<a href="https://huggingface.co/datasets/tinixai/vietnam-real-estates">TiniX AI</a>, '
        "CC BY-NC 4.0 · "
        '<a href="https://github.com/HongTin2104/soi-gia-nha">Mã nguồn</a></footer>',
        unsafe_allow_html=True,
    )


main()
