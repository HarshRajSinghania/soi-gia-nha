import numpy as np
import pandas as pd
import pytest

from soi_gia_nha.model import FEATURES, PriceModel, time_split
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


@pytest.fixture(scope="module")
def trained():
    df = fake_listings(3000)
    train, valid, test = time_split(df)
    model = PriceModel().fit(train, valid, rounds=200)
    return model, test


def test_time_split_is_ordered():
    train, valid, test = time_split(fake_listings(500))
    assert train["published_at"].max() < valid["published_at"].min()
    assert valid["published_at"].max() < test["published_at"].min()


def test_features_have_fixed_columns(trained):
    model, test = trained
    assert list(model.features(test).columns) == FEATURES


def test_learns_the_location_premium(trained):
    model, test = trained
    pred = model.predict(test)
    ape = (pred["mid"] - test["price"]).abs() / test["price"]
    assert ape.median() < 0.1
    assert (pred["low"] <= pred["mid"]).all() and (pred["mid"] <= pred["high"]).all()


def test_unknown_categories_do_not_crash(trained):
    model, test = trained
    odd = test.head(3).assign(district_name="Nowhere", ward_name="Z", project_name="X")
    assert model.predict(odd)["mid"].notna().all()


def test_save_and_load_round_trip(trained, tmp_path):
    model, test = trained
    model.save(tmp_path)
    again = PriceModel.load(tmp_path)
    np.testing.assert_allclose(again.predict(test)["mid"], model.predict(test)["mid"], rtol=1e-9)


def test_range_is_widened_on_validation(trained):
    model, test = trained
    assert model.range_adjust >= 0
    pred = model.predict(test)
    inside = (pred["low"] <= test["price"]) & (test["price"] <= pred["high"])
    assert inside.mean() > 0.6
