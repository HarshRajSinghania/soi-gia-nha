import pandas as pd

from soi_gia_nha.history import add_ids, fingerprint, match, price_steps, summarize

DESC = "Nhà 4 tầng ngõ ô tô đỗ cửa, sổ đỏ chính chủ, gần trường học, chợ và bệnh viện. "


def post(when, price, **kw):
    row = {
        "name": "Bán nhà Cầu Giấy ngõ ô tô, sổ đỏ chính chủ, giá tốt",
        "description": DESC + f"Giá {price / 1e9:g} tỷ.",
        "district_name": "Cầu Giấy",
        "ward_name": "Dịch Vọng",
        "property_type_name": "Nhà",
        "area": 50.0,
        "price": price,
        "published_at": pd.Timestamp(when),
    }
    row.update(kw)
    return row


def test_fingerprint_ignores_numbers_case_and_punctuation():
    a = fingerprint("Nhà 4 TẦNG, ngõ ô tô!! Giá 9,5 tỷ. Liên hệ chính chủ để xem nhà")
    b = fingerprint("nhà 5 tầng ngõ ô tô giá 9 tỷ liên hệ chính chủ để xem nhà")
    assert a == b


def test_fingerprint_drops_generic_text():
    assert fingerprint("Bán nhà gấp") == ""
    assert fingerprint(None) == ""


def test_price_cut_stays_the_same_property():
    df = add_ids(pd.DataFrame([post("2025-07-01", 11e9), post("2025-09-01", 9.5e9)]))
    assert df["property_id"].nunique() == 1


def test_title_alone_links_when_the_description_changes():
    df = add_ids(
        pd.DataFrame(
            [
                post("2025-07-01", 11e9),
                post(
                    "2025-08-01",
                    11e9,
                    description="Mô tả viết lại hoàn toàn khác so với lần đầu tiên",
                ),
            ]
        )
    )
    assert df["property_id"].nunique() == 1


def test_links_are_transitive():
    # first and last share nothing, but each shares something with the middle one
    df = add_ids(
        pd.DataFrame(
            [
                post("2025-07-01", 11e9, name="Tiêu đề thứ nhất khá dài để đủ điều kiện"),
                post("2025-08-01", 11e9, name="Tiêu đề thứ hai cũng đủ dài để so sánh"),
                post(
                    "2025-09-01",
                    10e9,
                    name="Tiêu đề thứ hai cũng đủ dài để so sánh",
                    description="Mô tả mới hoàn toàn, không còn giống lần đăng đầu nữa",
                ),
            ]
        )
    )
    assert df["property_id"].nunique() == 1


def test_different_area_or_ward_is_a_different_property():
    df = add_ids(
        pd.DataFrame(
            [
                post("2025-07-01", 11e9),
                post("2025-07-02", 11e9, area=52.0),
                post("2025-07-03", 11e9, ward_name="Quan Hoa"),
            ]
        )
    )
    assert df["property_id"].nunique() == 3


def test_summarize_and_steps():
    df = add_ids(
        pd.DataFrame(
            [
                post("2025-07-01", 11e9),
                post("2025-07-15", 11e9),
                post("2025-09-01", 10e9),
                post("2025-12-01", 9.5e9),
            ]
        )
    )
    s = summarize(df).iloc[0]
    assert s["posts"] == 4
    assert s["price_changes"] == 2
    assert s["days_listed"] == 153
    assert round(s["change"], 3) == round(9.5 / 11 - 1, 3)

    steps = price_steps(df)
    assert steps["price"].tolist() == [11e9, 10e9, 9.5e9]
    assert steps["posts"].tolist() == [2, 1, 1]


def test_match_finds_the_property():
    index = add_ids(pd.DataFrame([post("2025-07-01", 11e9), post("2025-09-01", 10e9)]))
    pasted = pd.Series(post("2026-10-01", 9e9))
    assert match(pasted, index) == index["property_id"].iloc[0]
    assert match(pd.Series(post("2026-10-01", 9e9, area=60.0)), index) is None
