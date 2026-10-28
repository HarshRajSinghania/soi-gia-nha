# Dataset card

## Source

| | |
|---|---|
| Listings | [tinixai/vietnam-real-estates](https://huggingface.co/datasets/tinixai/vietnam-real-estates) by [TiniX AI](https://tinix.ai/), revision `ca3fedc` |
| License | **CC BY-NC 4.0**: non-commercial use only, credit TiniX AI |
| Period | 1 June 2025 to 30 March 2026 |
| Size | 3,500,744 listings for sale, 63 provinces, 10 parquet shards (1.7 GB) |
| Old administrative units | [daohoangson/dvhcvn](https://github.com/daohoangson/dvhcvn) `v20250301` (GPL-3.0) |
| Old → new wards | [dvhcvn/20250701](https://github.com/dvhcvn/20250701) (MIT), built from resolutions 1654 to 1687/NQ-UBTVQH15 |

None of these files are committed here. `scripts/download.py` and `scripts/prepare.py` fetch
them, so the licenses of the originals apply to anything you build from them. The code in this
repo is MIT; models trained on the listings inherit the non-commercial restriction.

Phone numbers are already redacted in the source. This project does not collect anything else.

## What `scripts/prepare.py` does

Version 0.1 covers Hanoi and Ho Chi Minh City (71% of all listings).

| Step | Removed | Left |
|---|---:|---:|
| Raw listings | | 3,500,744 |
| Keep Hanoi and Ho Chi Minh City | 1,002,676 | 2,498,068 |
| Missing price, publish date or district | 238,869 | 2,259,199 |
| Price below 200 million VND | 36,245 | 2,222,954 |
| Area or price per m² outside the bounds below | 12,238 | 2,210,716 |
| Repost: same title, price and area | 677,538 | 1,533,178 |
| Repost: same description, price and area | 17,198 | **1,515,980** |

Reposts are removed keeping the **earliest** copy. Almost a third of the listings are reposts,
and leaving them in would put copies of the same property on both sides of a time-based split.

Bounds per property type, chosen from the percentiles in `notebooks/01_eda.ipynb`. They are
loose on purpose and only remove values that cannot be a total price (placeholders such as `0`,
prices typed per m², land in hectares):

| Type | Area (m²) | Price per m² (million VND) |
|---|---|---|
| Căn hộ chung cư (apartment) | 20 – 400 | 15 – 600 |
| Nhà (house) | 10 – 1,000 | 15 – 1,500 |
| Biệt thự / Nhà liền kề (villa, townhouse) | 30 – 2,000 | 20 – 1,500 |
| Shophouse | 20 – 2,000 | 20 – 1,500 |
| Đất (land) | 20 – 10,000 | 1 – 1,000 |

## Result

`data/processed/listings.parquet`, 1,515,980 rows:

| Type | Hà Nội | Hồ Chí Minh |
|---|---:|---:|
| Nhà | 354,079 | 521,325 |
| Căn hộ chung cư | 178,690 | 163,807 |
| Đất | 108,233 | 95,736 |
| Biệt thự / Nhà liền kề | 50,775 | 31,500 |
| Shophouse | 6,539 | 5,296 |

Columns: everything from the source, plus

| Column | Meaning |
|---|---|
| `price` | Asking price in VND, as a number (the source stores it as text) |
| `price_per_m2` | `price / area` |
| `new_province` | Province after 1 July 2025 |
| `new_ward` | Ward or commune after 1 July 2025. Old wards split between several new ones list all of them, separated by ` / ` |
| `ambiguous` | `True` when `new_ward` has more than one candidate |

88.3% of the cleaned listings get a new ward. The rest have no ward in the source listing.
Matching compares names after removing prefixes (`Phường`, `Quận`), leading zeros (`Phường 07`)
and differences in tone mark placement (`Hòa` / `Hoà`), which alone accounted for about 54,000 unmatched raw listings.

## Known limitations

- **Asking prices, not transaction prices.** The data tells you how a listing compares to
  other listings, not what a property will sell for.
- Listings with missing details are common: floors (77% missing), road width (81%),
  bedrooms (46%). Some of this is recovered from the description text later on.
- Agents post the same property with slightly different text. Reposts with edited titles
  and descriptions survive deduplication.
- 39% of the cleaned listings sit in an old ward that was split, so their new ward is a list of
  candidates rather than one name.
