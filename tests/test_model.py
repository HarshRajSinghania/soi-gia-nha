import numpy as np
from conftest import fake_listings

from soi_gia_nha.model import FEATURES, PriceModel, time_split


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
