# Listing history

Produced by `scripts/build_history.py` on 2,210,716 cleaned posts from Hanoi and Ho Chi Minh City, June 2025 to March 2026, reposts included.

Two posts are the same property when district, ward, type and exact area match, and the description or the title matches with numbers, punctuation and case ignored.

| | |
|---|---:|
| Posts | 2,210,716 |
| Distinct properties | 1,434,716 |
| Posts that repeat an earlier property | 35.1% |
| Properties posted more than once | 611,122 (42.6%) |
| Most posts for one property | 125 |
| Properties whose asking price changed | 74,497 |
| … of which the last price is lower | 51.1% |
| … of which the last price is higher | 45.1% |
| Median change when lowered | -2.8% |
| Median change when raised | 4.2% |
| Listed for 60 days or more | 69,665 |
| Price goes back to an earlier value (likely several units merged) | 4,815 (6.5% of repriced) |

## Is it really the same property?

There is no ground truth, so the check uses details the seller typed into separate fields: a repost of the same property should repeat them. *Linked* compares each repost with the first post of its property. *Same block, not linked* compares different properties that share district, ward, type and area, the closest thing to a false link.

| Field | Linked reposts agree | Same block, not linked |
|---|---:|---:|
| Floors | 99.1% (270,523) | 43.2% (291,293) |
| Bedrooms | 98.5% (475,338) | 55.4% (759,656) |
| Frontage | 96.7% (396,294) | 35.5% (556,868) |

Agents also reuse one text for several units of the same size in a project, and those get merged. The table above bounds how often that happens; it does not rule it out.
