"""Clean the raw listings and attach the post-2025 administrative units.

python scripts/prepare.py   # writes data/processed/listings.parquet
"""

import argparse

from soi_gia_nha.admin import attach_new_units, build_map, save_map
from soi_gia_nha.clean import DEFAULT_PROVINCES, clean
from soi_gia_nha.data import COLUMNS, PROCESSED_DIR, load_raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shards", type=int, default=None, help="only read the first N shards")
    args = ap.parse_args()

    raw = load_raw(columns=COLUMNS, shards=args.shards)
    print(f"raw        {len(raw):>10,}")

    df = clean(raw, DEFAULT_PROVINCES)
    print(f"clean      {len(df):>10,}")

    admin_map = build_map(DEFAULT_PROVINCES)
    save_map(admin_map)
    df = attach_new_units(df, admin_map)
    print(f"new ward   {df['new_ward'].notna().mean():>10.1%}")

    out = PROCESSED_DIR / "listings.parquet"
    df.to_parquet(out, index=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
