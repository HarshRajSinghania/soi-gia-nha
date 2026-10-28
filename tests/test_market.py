import pandas as pd
import pytest

from soi_gia_nha.market import monthly_pulse, pulse_for, similar


def props(rows):
    df = pd.DataFrame(rows)
    df["first_seen"] = pd.to_datetime(df["first_seen"])
    df["last_seen"] = df["first_seen"]
    df["last_price"] = df["first_price"]
    return df


def growing_ward(ward="Dịch Vọng", per_month=10, start=100e6, step=1e6):
    rows = []
    for m in range(10):
        for _ in range(per_month):
            rows.append(
                {
                    "district_name": "Cầu Giấy",
                    "ward_name": ward,
                    "property_type_name": "Nhà",
                    "area": 50.0,
                    "first_price": (start + step * m) * 50,
                    "first_seen": f"2025-{6 + m:02d}-01" if m < 7 else f"2026-{m - 6:02d}-01",
                }
            )
    return rows


def test_pulse_uses_the_ward_when_it_has_enough_listings():
    table = monthly_pulse(props(growing_ward()))
    p = pulse_for(table, "Cầu Giấy", "Dịch Vọng", "Nhà")
    assert p.area == "phường Dịch Vọng"
    assert len(p.months) == 10
    assert p.listed == 100
    assert p.change == pytest.approx(108 / 101 - 1)


def test_pulse_falls_back_to_the_district():
    rows = growing_ward(ward="Dịch Vọng", per_month=10) + growing_ward(ward="Quan Hoa", per_month=2)
    table = monthly_pulse(props(rows))
    assert pulse_for(table, "Cầu Giấy", "Quan Hoa", "Nhà").area == "quận Cầu Giấy"
    assert pulse_for(table, "Cầu Giấy", "Quan Hoa", "Đất") is None


def test_similar_prefers_same_ward_size_and_floors():
    base = {"district_name": "Cầu Giấy", "property_type_name": "Nhà", "first_seen": "2026-03-01"}
    rows = [
        {**base, "ward_name": "Dịch Vọng", "area": 50.0, "floor_count": 5, "first_price": 1e10},
        {**base, "ward_name": "Quan Hoa", "area": 50.0, "floor_count": 5, "first_price": 2e10},
        {**base, "ward_name": "Dịch Vọng", "area": 60.0, "floor_count": 3, "first_price": 3e10},
        {**base, "ward_name": "Dịch Vọng", "area": 200.0, "floor_count": 5, "first_price": 4e10},
        {**base, "ward_name": "Dịch Vọng", "area": 50.0, "floor_count": 5, "first_price": 1e10},
    ]
    listing = pd.Series({**base, "ward_name": "Dịch Vọng", "area": 50.0, "floor_count": 5})
    out = similar(listing, props(rows), n=5)
    assert out.index.tolist() == [0, 1, 2]  # 200 m2 is too far, row 4 duplicates row 0


def test_similar_can_exclude_the_listing_itself():
    base = {"district_name": "Cầu Giấy", "property_type_name": "Nhà", "first_seen": "2026-03-01"}
    rows = [{**base, "ward_name": "A", "area": 50.0, "floor_count": 5, "first_price": 1e10}]
    listing = pd.Series({**base, "ward_name": "A", "area": 50.0, "floor_count": 5})
    assert similar(listing, props(rows), exclude=0).empty
