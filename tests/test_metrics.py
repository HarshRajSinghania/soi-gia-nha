import pandas as pd
import pytest

from soi_gia_nha.metrics import by_group, summary


def test_summary():
    s = summary([100, 100, 100, 100], [100, 105, 115, 150], low=[90] * 4, high=[110] * 4)
    assert s["n"] == 4
    assert s["median_ape"] == pytest.approx(0.10)
    assert s["within_10"] == 0.5
    assert s["within_20"] == 0.75
    assert s["range_coverage"] == 1.0


def test_by_group():
    df = pd.DataFrame({"city": ["a", "a", "b"], "y": [100, 100, 100], "p": [100, 120, 100]})
    out = by_group(df, ["city"], y_true="y", y_pred="p").set_index("city")
    assert out.loc["a", "median_ape"] == pytest.approx(0.10)
    assert out.loc["b", "within_10"] == 1.0
