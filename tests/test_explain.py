import pandas as pd
import pytest

from soi_gia_nha.explain import (
    Check,
    Reason,
    check,
    contributions,
    format_vnd,
    group_reasons,
    summary_vi,
    verdict,
)


def test_verdict():
    assert verdict(80, 90, 110) == "cheap"
    assert verdict(100, 90, 110) == "fair"
    assert verdict(120, 90, 110) == "expensive"


@pytest.mark.parametrize(
    ("value", "text"),
    [(9.1e9, "9,1 tỷ"), (12e9, "12 tỷ"), (4.15e9, "4,15 tỷ"), (850e6, "850 triệu")],
)
def test_format_vnd(value, text):
    assert format_vnd(value) == text


def test_group_reasons_sums_and_ranks():
    contrib = pd.Series(
        {"district_median": 0.20, "ward_median": 0.05, "log_area": -0.10, "urgent": 0.001}
    )
    reasons = group_reasons(contrib)
    assert [r.group for r in reasons] == ["location", "size"]
    assert reasons[0].effect == pytest.approx(0.284, abs=1e-3)  # exp(0.25) - 1


def test_contributions_add_up_to_the_prediction(trained):
    model, test = trained
    c = contributions(model, test.head(20))
    raw = model.boosters["mid"].predict(model.features(test.head(20)))
    assert (c.sum(axis=1) - raw).abs().max() < 1e-6


def test_check_on_an_overpriced_listing(trained):
    model, test = trained
    row = test.head(1).copy()
    row["price"] = row["price"] * 10
    result = check(model, row)
    assert result.verdict == "expensive"
    assert result.low <= result.mid <= result.high
    assert any("cao bất thường" in w for w in result.warnings)


def test_check_rejects_several_rows(trained):
    model, test = trained
    with pytest.raises(ValueError):
        check(model, test.head(2))


def test_summary_vi():
    result = Check(
        asked=9e9,
        low=7e9,
        mid=7.5e9,
        high=8e9,
        verdict="expensive",
        diff=0.2,
        reasons=[Reason("location", "Vị trí", 0.3), Reason("size", "Diện tích", -0.05)],
    )
    text = summary_vi(result)
    assert text.startswith("Giá rao cao hơn mức dự đoán khoảng 20%")
    assert "7 tỷ – 8 tỷ" in text
    assert "Đẩy giá lên: vị trí (+30%)" in text
    assert "Kéo giá xuống: diện tích (-5%)" in text
