# Price model

Produced by `scripts/train.py`. Listings are split by publish date: train on June 2025 to January 2026 (1,298,649), early stopping on February 2026 (56,440), test on March 2026 (160,891). The test month is never seen during training, the same situation as checking a new listing.

Errors are on the asking price. *Median error* is the median of |predicted − asked| / asked. *Within 10% / 20%* is the share of test listings predicted that close.

| Model | Median error | Mean error | Within 10% | Within 20% |
|---|---:|---:|---:|---:|
| District median | 23.2% | 35.0% | 23.1% | 43.9% |
| Ward median | 20.1% | 32.6% | 26.2% | 49.8% |
| LightGBM | 11.6% | 19.5% | 44.7% | 70.1% |

The fair range comes from 10th and 90th percentile models, widened on the February validation month until it covers 80% there. On the March test month it contains the asking price for **77.5%** of test listings (80% expected) and is 48.2% of the predicted price wide (median).

## By city and property type

| City | Type | Listings | Median error | Within 20% | Range coverage |
|---|---|---:|---:|---:|---:|
| Hà Nội | Nhà | 27,876 | 14.6% | 63.2% | 77.7% |
| Hà Nội | Căn hộ chung cư | 20,101 | 6.4% | 90.0% | 79.4% |
| Hà Nội | Đất | 9,651 | 16.5% | 57.9% | 77.5% |
| Hà Nội | Biệt thự/Nhà liền kề | 5,074 | 10.9% | 75.3% | 79.0% |
| Hà Nội | Shophouse | 812 | 16.6% | 56.9% | 68.7% |
| Hồ Chí Minh | Nhà | 58,476 | 13.5% | 65.6% | 76.8% |
| Hồ Chí Minh | Căn hộ chung cư | 22,774 | 7.6% | 83.7% | 78.6% |
| Hồ Chí Minh | Đất | 11,927 | 15.6% | 59.8% | 76.9% |
| Hồ Chí Minh | Biệt thự/Nhà liền kề | 3,576 | 13.8% | 64.8% | 74.3% |
| Hồ Chí Minh | Shophouse | 624 | 17.7% | 54.0% | 68.8% |

## Most useful features (share of total gain)

| Feature | Gain |
|---|---:|
| `district_median` | 54.1% |
| `ward_median` | 17.9% |
| `floor_count` | 6.1% |
| `district_name` | 4.1% |
| `ward_name` | 4.0% |
| `log_area` | 3.3% |
| `project_name` | 2.1% |
| `frontage_width` | 1.1% |
| `month` | 1.1% |
| `main_street` | 0.9% |
| `property_type_name` | 0.9% |
| `bedroom_count` | 0.7% |
