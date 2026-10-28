# Changelog

## Unreleased

## 0.2.0 - 2026-10-28

Listing history and market context.

- Reposts of the same property are linked across 2.2 million posts: 35% of posts repeat an
  earlier property, 74,497 properties changed their asking price
- The demo shows when a listing was first posted, how often, and every price change, with a
  warning when the "history" is really several units sharing one text
- Monthly price per m² for the ward, and the five closest similar properties
- "Lấy một tin có thật để thử" button with 2,000 real listings that have a history
- Property data for the demo packaged by `scripts/build_app_data.py` for release `data-v0.2`
- Redesigned demo: two columns, Be Vietnam Pro, no Plotly

## 0.1.0 - 2026-10-28

First release, Hanoi and Ho Chi Minh City.

- Cleaning pipeline for the TiniX listings: impossible prices, repost removal, data card
- Floors, widths, legal papers and other flags read from the listing text
- Old addresses mapped to the wards in force since 1 July 2025
- LightGBM price model with a conformally calibrated fair range: 11.6% median error on
  March 2026 listings, against 20.1% for the ward median
- TreeSHAP reasons and a plain Vietnamese summary for each listing
- Streamlit demo and Dockerfile; trained model published as release `model-v0.1`
