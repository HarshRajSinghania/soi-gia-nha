# Text extraction

Measured on the 1,515,980 cleaned listings by `scripts/eval_text.py`.

**Agreement** compares the value read from the text with the value the seller entered in the structured field, on listings that have both. **Missing** is the share of listings with no value, before and after reading the text.

| Field | Listings with both | Agreement | Missing before | Missing after |
|---|---:|---:|---:|---:|
| Floors | 311,873 | 88.9% | 76.4% | 40.7% |
| Bedrooms | 671,912 | 87.8% | 39.8% | 33.3% |
| Frontage width (m) | 207,053 | 94.9% (±0.5 m) | 51.8% | 49.4% |
| Road / alley width (m) | 50,271 | 88.7% (±0.5 m) | 84.8% | 76.7% |

Flags found in the text:

| Flag | Listings |
|---|---:|
| `legal_book` | 49.3% |
| `legal_weak` | 1.7% |
| `car_access` | 30.4% |
| `main_street` | 17.4% |
| `alley` | 36.0% |
| `corner` | 13.8% |
| `elevator` | 11.5% |
| `furnished` | 21.0% |
| `business` | 36.2% |
| `urgent` | 13.2% |
