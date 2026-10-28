import pandas as pd

from soi_gia_nha import ui
from soi_gia_nha.explain import Check, Reason
from soi_gia_nha.market import Pulse


def summary(**kw):
    row = {
        "posts": 3,
        "days_listed": 270,
        "first_seen": pd.Timestamp("2025-06-17"),
        "last_seen": pd.Timestamp("2026-03-14"),
        "first_price": 11e9,
        "last_price": 10e9,
        "price_changes": 1,
        "returns": 0,
        "change": 10 / 11 - 1,
    }
    row.update(kw)
    return pd.Series(row)


def steps():
    return pd.DataFrame(
        {
            "since": pd.to_datetime(["2025-06-17", "2025-10-13"]),
            "until": pd.to_datetime(["2025-06-17", "2026-03-14"]),
            "price": [11e9, 10e9],
            "posts": [1, 2],
        }
    )


def test_history_card_tells_the_price_story():
    html = ui.history_card(summary(), steps())
    assert "17/6/2025" in html
    assert "9 tháng" in html
    assert "từ 11 tỷ xuống còn 10 tỷ" in html and "-9%" in html
    assert html.count("<li>") == 2 and "<svg" in html


def test_history_card_warns_about_alternating_prices():
    html = ui.history_card(summary(returns=2, price_changes=3), steps())
    assert "vài căn cùng diện tích" in html
    assert "xuống còn" not in html


def test_history_card_without_price_change():
    s = summary(price_changes=0, last_price=11e9, change=0.0, days_listed=0)
    html = ui.history_card(s, steps().head(1))
    assert "giá giữ nguyên 11 tỷ" in html
    assert "trong một ngày" in html
    assert "<svg" not in html


def test_small_price_changes_stay_small_on_the_chart():
    html = ui._steps_svg(steps(), pd.Timestamp("2026-03-14"))
    ys = [float(p.split(",")[1]) for p in html.split('points="')[1].split('"')[0].split()]
    assert max(ys) - min(ys) < 60  # a 9% cut, not a fall off a cliff


def test_pulse_card_formats_numbers_the_vietnamese_way():
    months = pd.Series(
        [100e6, 104e6, 110e6], index=pd.to_datetime(["2025-06-01", "2025-07-01", "2026-03-01"])
    )
    html = ui.pulse_card(Pulse("phường Linh Chiểu", months, 2228, 0.14), 116e6)
    assert "phường Linh Chiểu" in html
    assert "Giá/m² trung vị, 3/2026" in html
    assert "2.228" in html and "+14%" in html
    assert "116 tr/m²" in html


def test_comps_card_colours_by_price_per_m2():
    comps = pd.DataFrame(
        {
            "area": [86.0, 80.0],
            "floor_count": [4.0, float("nan")],
            "ward_name": ["Linh Chiểu", None],
            "last_price": [12e9, 8e9],
            "last_seen": pd.to_datetime(["2026-02-01", "2026-03-01"]),
            "posts": [3, 1],
        }
    )
    html = ui.comps_card(comps, 116e6)
    assert 'class="sg-up">140 tr/m²' in html
    assert 'class="sg-down">100 tr/m²' in html
    assert "đăng 3 lần" in html and "4 tầng" in html
    assert ui.comps_card(comps.head(0), 116e6) == ""


def test_price_card_and_reasons_escape_labels():
    result = Check(
        asked=10e9,
        low=8e9,
        mid=11.7e9,
        high=15e9,
        verdict="fair",
        diff=-0.15,
        reasons=[Reason("x", "<b>Vị trí</b>", 0.3)],
    )
    assert "Giá hợp lý" in ui.price_card(result, 86)
    assert "&lt;b&gt;" in ui.reasons_block(result)
