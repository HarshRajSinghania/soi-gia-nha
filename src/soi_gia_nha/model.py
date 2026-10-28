"""Price model: LightGBM on log price per m2.

Three boosters share the same features:

- ``mid`` (L2 on log price per m2) gives the point estimate and the SHAP explanations,
- ``low`` and ``high`` (quantile 0.1 and 0.9) give the "fair range".

Quantile boosters are usually too confident on data from a later month, so the range is
widened afterwards on the validation month (conformalized quantile regression) until it
holds ``COVERAGE`` of the asking prices there.

Predicting price per m2 instead of total price keeps the target on one scale across a
30 m2 flat and a 300 m2 plot, and area stays in as a feature for the size discount.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from .text import FLAGS

CATEGORICAL = [
    "province_name",
    "property_type_name",
    "district_name",
    "ward_name",
    "project_name",
    "house_direction",
    "balcony_direction",
]
NUMERIC = [
    "log_area",
    "floor_count",
    "bedroom_count",
    "bathroom_count",
    "frontage_width",
    "house_depth",
    "road_width",
    "ward_median",
    "district_median",
    "month",
]
FEATURES = CATEGORICAL + NUMERIC + list(FLAGS)
# Projects with fewer listings than this in training are treated as "no project".
MIN_PROJECT_LISTINGS = 30
WARD_SHRINK = 50
COVERAGE = 0.8
EPOCH = pd.Timestamp("2025-06-01")

PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 255,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "cat_smooth": 20,
    "max_cat_to_onehot": 8,
    "verbose": -1,
}


def time_split(df: pd.DataFrame, valid_from="2026-02-01", test_from="2026-03-01"):
    """Train on the older listings and test on the newest, the way the tool is used."""
    t = df["published_at"]
    return (
        df[t < valid_from],
        df[(t >= valid_from) & (t < test_from)],
        df[t >= test_from],
    )


@dataclass
class PriceModel:
    boosters: dict[str, lgb.Booster] = field(default_factory=dict)
    categories: dict[str, list[str]] = field(default_factory=dict)
    ward_medians: pd.Series | None = None
    district_medians: pd.Series | None = None
    range_adjust: float = 0.0  # added to both ends of the range, in log price per m2

    # -- features ---------------------------------------------------------------------

    def _fit_encodings(self, train: pd.DataFrame) -> None:
        y = np.log(train["price_per_m2"])
        self.district_medians = y.groupby(
            [train["property_type_name"], train["district_name"]]
        ).median()
        ward = y.groupby(
            [train["property_type_name"], train["district_name"], train["ward_name"]]
        ).agg(["median", "size"])
        # A ward with a handful of listings would hand the model its own targets back.
        # Pull small wards toward their district.
        district = self.district_medians.reindex(ward.index.droplevel(2)).to_numpy()
        n = ward["size"].to_numpy()
        self.ward_medians = pd.Series(
            (n * ward["median"].to_numpy() + WARD_SHRINK * district) / (n + WARD_SHRINK),
            index=ward.index,
        )
        projects = train["project_name"].value_counts()
        keep_projects = set(projects[projects >= MIN_PROJECT_LISTINGS].index)
        for col in CATEGORICAL:
            values = train[col].dropna().unique().tolist()
            if col == "project_name":
                values = [v for v in values if v in keep_projects]
            self.categories[col] = sorted(values)

    def features(self, df: pd.DataFrame) -> pd.DataFrame:
        X = pd.DataFrame(index=df.index)
        for col in CATEGORICAL:
            cats = self.categories[col]
            known = df[col].where(df[col].isin(cats))  # unseen values become missing
            X[col] = pd.Categorical(known, categories=cats)
        X["log_area"] = np.log(df["area"])
        for col in [
            "floor_count",
            "bedroom_count",
            "bathroom_count",
            "frontage_width",
            "house_depth",
            "road_width",
        ]:
            X[col] = pd.to_numeric(df[col], errors="coerce")
        keys_w = pd.MultiIndex.from_frame(
            df[["property_type_name", "district_name", "ward_name"]].astype(object)
        )
        keys_d = pd.MultiIndex.from_frame(
            df[["property_type_name", "district_name"]].astype(object)
        )
        X["ward_median"] = self.ward_medians.reindex(keys_w).to_numpy()
        X["district_median"] = self.district_medians.reindex(keys_d).to_numpy()
        X["month"] = (pd.to_datetime(df["published_at"]) - EPOCH).dt.days / 30.44
        for flag in FLAGS:
            X[flag] = df[flag].astype(float)
        return X[FEATURES]

    # -- training ---------------------------------------------------------------------

    def fit(self, train: pd.DataFrame, valid: pd.DataFrame, rounds: int = 3000) -> PriceModel:
        # Encodings come from the training rows only, so the medians never see the
        # listings they are evaluated on.
        self._fit_encodings(train)
        X_tr, X_va = self.features(train), self.features(valid)
        y_tr, y_va = np.log(train["price_per_m2"]), np.log(valid["price_per_m2"])
        objectives = {
            "mid": {"objective": "regression"},
            "low": {"objective": "quantile", "alpha": 0.1},
            "high": {"objective": "quantile", "alpha": 0.9},
        }
        for name, obj in objectives.items():
            d_tr = lgb.Dataset(X_tr, y_tr, free_raw_data=False)
            d_va = lgb.Dataset(X_va, y_va, reference=d_tr)
            self.boosters[name] = lgb.train(
                {**PARAMS, **obj},
                d_tr,
                num_boost_round=rounds,
                valid_sets=[d_va],
                callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
            )
        low, _, high = self._predict_log(X_va)
        score = np.maximum(low - y_va.to_numpy(), y_va.to_numpy() - high)
        n = len(score)
        self.range_adjust = float(np.quantile(score, min(1.0, COVERAGE * (n + 1) / n)))
        return self

    # -- inference --------------------------------------------------------------------

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predicted total price (VND): low, mid, high."""
        low, mid, high = self._predict_log(self.features(df))
        low = np.minimum(low - self.range_adjust, mid)
        high = np.maximum(high + self.range_adjust, mid)
        area = df["area"].to_numpy()
        return pd.DataFrame(
            {"low": np.exp(low) * area, "mid": np.exp(mid) * area, "high": np.exp(high) * area},
            index=df.index,
        )

    def _predict_log(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return tuple(
            self.boosters[k].predict(X, num_iteration=self.boosters[k].best_iteration)
            for k in ("low", "mid", "high")
        )

    # -- persistence ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for name, b in self.boosters.items():
            b.save_model(path / f"{name}.txt", num_iteration=b.best_iteration)
        meta = {"categories": self.categories, "range_adjust": self.range_adjust}
        (path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.ward_medians.rename("v").reset_index().to_parquet(path / "ward_medians.parquet")
        self.district_medians.rename("v").reset_index().to_parquet(
            path / "district_medians.parquet"
        )

    @classmethod
    def load(cls, path: Path) -> PriceModel:
        m = cls()
        for name in ("low", "mid", "high"):
            m.boosters[name] = lgb.Booster(model_file=str(path / f"{name}.txt"))
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        m.categories, m.range_adjust = meta["categories"], meta["range_adjust"]
        w = pd.read_parquet(path / "ward_medians.parquet")
        m.ward_medians = w.set_index(["property_type_name", "district_name", "ward_name"])["v"]
        d = pd.read_parquet(path / "district_medians.parquet")
        m.district_medians = d.set_index(["property_type_name", "district_name"])["v"]
        return m
