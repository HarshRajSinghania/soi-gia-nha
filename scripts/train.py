"""Train the price model, compare it with simple baselines, write reports/model.md.

python scripts/train.py                 # full data, ~10 min on a 16-thread laptop
python scripts/train.py --sample 0.1    # quick run
"""

import argparse
import time

import numpy as np
import pandas as pd

from soi_gia_nha.data import PROCESSED_DIR, ROOT
from soi_gia_nha.metrics import by_group, summary
from soi_gia_nha.model import PriceModel, time_split

MODEL_DIR = ROOT / "models" / "v0.1"


def median_baseline(train: pd.DataFrame, test: pd.DataFrame, keys: list[str]) -> np.ndarray:
    """Median price per m2 of the same group in training, times the area."""
    med = train.groupby(keys)["price_per_m2"].median().rename("m")
    fallback = train.groupby("property_type_name")["price_per_m2"].median().rename("f")
    t = test[keys].join(med, on=keys).join(fallback, on="property_type_name")
    return (t["m"].fillna(t["f"]) * test["area"]).to_numpy()


def pct(x: float) -> str:
    return f"{x:.1%}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", type=float, default=None, help="fraction of rows to use")
    args = ap.parse_args()

    df = pd.read_parquet(PROCESSED_DIR / "listings.parquet")
    if args.sample:
        df = df.sample(frac=args.sample, random_state=0)
    train, valid, test = time_split(df)
    print(f"train {len(train):,}  valid {len(valid):,}  test {len(test):,}")

    t0 = time.time()
    model = PriceModel().fit(train, valid)
    print(
        f"trained in {time.time() - t0:.0f}s, rounds:",
        {k: b.best_iteration for k, b in model.boosters.items()},
    )

    pred = model.predict(test)
    y = test["price"].to_numpy()
    rows = {
        "District median": summary(
            y, median_baseline(train, test, ["property_type_name", "district_name"])
        ),
        "Ward median": summary(
            y, median_baseline(train, test, ["property_type_name", "district_name", "ward_name"])
        ),
        "LightGBM": summary(y, pred["mid"], pred["low"], pred["high"]),
    }

    scored = test.assign(pred=pred["mid"], low=pred["low"], high=pred["high"])
    groups = by_group(
        scored,
        ["province_name", "property_type_name"],
        y_true="price",
        y_pred="pred",
        low="low",
        high="high",
    )

    imp = pd.Series(
        model.boosters["mid"].feature_importance("gain"),
        index=model.boosters["mid"].feature_name(),
    )
    imp = (imp / imp.sum()).sort_values(ascending=False)

    lines = [
        "# Price model",
        "",
        "Produced by `scripts/train.py`. Listings are split by publish date: train on "
        f"June 2025 to January 2026 ({len(train):,}), early stopping on February 2026 "
        f"({len(valid):,}), test on March 2026 ({len(test):,}). The test month is never seen "
        "during training, the same situation as checking a new listing.",
        "",
        "Errors are on the asking price. *Median error* is the median of |predicted − asked| / "
        "asked. *Within 10% / 20%* is the share of test listings predicted that close.",
        "",
        "| Model | Median error | Mean error | Within 10% | Within 20% |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, s in rows.items():
        lines.append(
            f"| {name} | {pct(s['median_ape'])} | {pct(s['mape'])} | "
            f"{pct(s['within_10'])} | {pct(s['within_20'])} |"
        )
    s = rows["LightGBM"]
    lines += [
        "",
        "The fair range comes from 10th and 90th percentile models, widened on the February "
        "validation month until it covers 80% there. On the March test month it contains "
        "the asking price for "
        f"**{pct(s['range_coverage'])}** of test listings (80% expected) and is "
        f"{pct(s['range_width'])} of the predicted price wide (median).",
        "",
        "## By city and property type",
        "",
        "| City | Type | Listings | Median error | Within 20% | Range coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in groups.sort_values(["province_name", "n"], ascending=[True, False]).iterrows():
        lines.append(
            f"| {r['province_name']} | {r['property_type_name']} | {r['n']:,} | "
            f"{pct(r['median_ape'])} | {pct(r['within_20'])} | {pct(r['range_coverage'])} |"
        )
    lines += [
        "",
        "## Most useful features (share of total gain)",
        "",
        "| Feature | Gain |",
        "|---|---:|",
    ]
    for f, v in imp.head(12).items():
        lines.append(f"| `{f}` | {pct(v)} |")

    report = "\n".join(lines) + "\n"
    if args.sample:
        print(report)
        return
    model.save(MODEL_DIR)
    out = ROOT / "reports" / "model.md"
    out.write_text(report, encoding="utf-8", newline="\n")
    print(report)
    print("saved", MODEL_DIR)


if __name__ == "__main__":
    main()
