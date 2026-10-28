import numpy as np
import pandas as pd
import pytest

from soi_gia_nha.model import PriceModel, time_split
from soi_gia_nha.text import FLAGS


def fake_listings(n: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    district = rng.choice(["Cầu Giấy", "Hà Đông"], n)
    area = rng.uniform(30, 150, n)
    base = np.where(district == "Cầu Giấy", 200e6, 100e6)
    ppm = base * (area / 60) ** -0.2 * rng.lognormal(0, 0.05, n)
    df = pd.DataFrame(
        {
            "province_name": "Hà Nội",
            "property_type_name": "Nhà",
            "district_name": district,
            "ward_name": rng.choice(["A", "B", "C"], n),
            "project_name": None,
            "house_direction": None,
            "balcony_direction": None,
            "area": area,
            "floor_count": rng.integers(2, 6, n).astype(float),
            "bedroom_count": np.nan,
            "bathroom_count": np.nan,
            "frontage_width": np.nan,
            "house_depth": np.nan,
            "road_width": np.nan,
            "published_at": pd.Timestamp("2025-07-01")
            + pd.to_timedelta(rng.integers(0, 270, n), unit="D"),
            "price_per_m2": ppm,
        }
    )
    for flag in FLAGS:
        df[flag] = False
    df["price"] = df["price_per_m2"] * df["area"]
    return df


@pytest.fixture(scope="session")
def trained():
    df = fake_listings(3000)
    train, valid, test = time_split(df)
    model = PriceModel().fit(train, valid, rounds=200)
    return model, test
