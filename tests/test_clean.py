import pandas as pd

from soi_gia_nha.clean import clean


def listing(**kw):
    row = {
        "name": "Bán nhà Cầu Giấy",
        "description": "Nhà 4 tầng, sổ hồng chính chủ, ngõ ô tô đỗ cửa, gần trường học và chợ.",
        "property_type_name": "Nhà",
        "province_name": "Hà Nội",
        "district_name": "Cầu Giấy",
        "ward_name": "Dịch Vọng",
        "price": "9000000000",
        "area": 50.0,
        "published_at": "2025-08-01T10:00:00",
    }
    row.update(kw)
    return row


def test_keeps_a_normal_listing():
    out = clean(pd.DataFrame([listing()]))
    assert len(out) == 1
    assert out["price"].iloc[0] == 9e9
    assert out["price_per_m2"].iloc[0] == 9e9 / 50


def test_drops_impossible_prices_and_other_cities():
    rows = [
        listing(price="0"),
        listing(price=None),
        listing(price="150000000"),  # below the 200M floor
        listing(price="400000000"),  # 8M/m2, below the house floor of 15M/m2
        listing(area=5.0),
        listing(province_name="Đà Nẵng"),
        listing(district_name=None),
        listing(property_type_name="Kho xưởng"),
    ]
    assert clean(pd.DataFrame(rows)).empty


def test_land_has_its_own_bounds():
    out = clean(pd.DataFrame([listing(property_type_name="Đất", price="400000000")]))
    assert len(out) == 1


def test_reposts_keep_the_earliest():
    rows = [
        listing(published_at="2025-09-01", name="BÁN  NHÀ Cầu Giấy"),
        listing(published_at="2025-07-01"),
        listing(published_at="2025-08-01", name="Khác hẳn"),  # same description, same price
        listing(published_at="2025-10-01", price="9500000000"),  # price changed, keep
    ]
    out = clean(pd.DataFrame(rows))
    assert out["published_at"].dt.strftime("%Y-%m").tolist() == ["2025-07", "2025-10"]


def test_can_keep_reposts_for_the_history():
    rows = [listing(published_at="2025-09-01"), listing(published_at="2025-07-01")]
    out = clean(pd.DataFrame(rows), drop_reposts=False)
    assert out["published_at"].dt.strftime("%Y-%m").tolist() == ["2025-07", "2025-09"]
