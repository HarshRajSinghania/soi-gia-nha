"""Run the listing check over the March 2026 test month, write reports/checks.md.

python scripts/eval_checks.py   # needs models/v0.1 from scripts/train.py
"""

import numpy as np
import pandas as pd

from soi_gia_nha.data import PROCESSED_DIR, ROOT
from soi_gia_nha.explain import SUSPICIOUS_RATIO, VERDICTS_VI
from soi_gia_nha.model import PriceModel, time_split

MODEL_DIR = ROOT / "models" / "v0.1"


def main() -> None:
    _, _, test = time_split(pd.read_parquet(PROCESSED_DIR / "listings.parquet"))
    pred = PriceModel.load(MODEL_DIR).predict(test)
    price = test["price"]
    verdict = np.select([price < pred["low"], price > pred["high"]], ["cheap", "expensive"], "fair")
    test = test.assign(
        verdict=verdict,
        diff=price / pred["mid"] - 1,
        suspicious=(price < pred["low"] / SUSPICIOUS_RATIO)
        | (price > pred["high"] * SUSPICIOUS_RATIO),
    )

    share = test["verdict"].value_counts(normalize=True)
    lines = [
        "# Listing checks on the test month",
        "",
        f"`scripts/eval_checks.py` on the {len(test):,} listings published in March 2026.",
        "",
        "| Verdict | Listings |",
        "|---|---:|",
    ]
    for key, label in VERDICTS_VI.items():
        lines.append(f"| {label} ({key}) | {share.get(key, 0):.1%} |")
    lines += [
        "",
        f"**{test['suspicious'].mean():.2%}** of listings are more than {SUSPICIOUS_RATIO}x "
        "outside the fair range and get a warning that the price itself looks wrong.",
        "",
        "## Do the words in the listing match the price?",
        "",
        "Median of asking price vs. predicted price, for listings with and without a phrase. "
        "The model already uses these flags, so this is what is left after accounting for them.",
        "",
        "| Phrase | With | Without | Share flagged cheap (with) |",
        "|---|---:|---:|---:|",
    ]
    for flag, label in [
        ("urgent", '"bán gấp", "cắt lỗ", "ngộp"'),
        ("legal_weak", "sổ chung, vi bằng, HĐMB"),
        ("legal_book", "sổ hồng, sổ đỏ"),
    ]:
        with_ = test[test[flag]]
        without = test[~test[flag]]
        lines.append(
            f"| {label} | {with_['diff'].median():+.1%} | {without['diff'].median():+.1%} | "
            f"{(with_['verdict'] == 'cheap').mean():.1%} |"
        )

    out = ROOT / "reports" / "checks.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
