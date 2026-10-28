# Changelog

## Unreleased

## 0.1.0 - 2026-10-28

First release, Hanoi and Ho Chi Minh City.

- Cleaning pipeline for the TiniX listings: impossible prices, repost removal, data card
- Floors, widths, legal papers and other flags read from the listing text
- Old addresses mapped to the wards in force since 1 July 2025
- LightGBM price model with a conformally calibrated fair range: 11.6% median error on
  March 2026 listings, against 20.1% for the ward median
- TreeSHAP reasons and a plain Vietnamese summary for each listing
- Streamlit demo and Dockerfile; trained model published as release `model-v0.1`
