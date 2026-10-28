# Listing checks on the test month

`scripts/eval_checks.py` on the 160,891 listings published in March 2026.

| Verdict | Listings |
|---|---:|
| Rẻ hơn mặt bằng (cheap) | 11.5% |
| Hợp lý (fair) | 77.5% |
| Đắt hơn mặt bằng (expensive) | 11.0% |

**0.22%** of listings are more than 2.5x outside the fair range and get a warning that the price itself looks wrong.

## Do the words in the listing match the price?

Median of asking price vs. predicted price, for listings with and without a phrase. The model already uses these flags, so this is what is left after accounting for them.

| Phrase | With | Without | Share flagged cheap (with) |
|---|---:|---:|---:|
| "bán gấp", "cắt lỗ", "ngộp" | -0.5% | -0.1% | 13.7% |
| sổ chung, vi bằng, HĐMB | -0.1% | -0.2% | 11.3% |
| sổ hồng, sổ đỏ | -0.5% | +0.1% | 11.8% |
