"""Package what the app needs into data/app/: one row per property, the post history for
matching and price steps, and monthly ward trends.

    python scripts/build_app_data.py   # needs data/processed/posts.parquet
"""

import zipfile

import pandas as pd

from soi_gia_nha.assets import DATA_DIR, DATA_FILES, DATA_VERSION
from soi_gia_nha.data import PROCESSED_DIR
from soi_gia_nha.history import summarize
from soi_gia_nha.market import monthly_pulse
from soi_gia_nha.text import extract

CATEGORIES = ["province_name", "district_name", "ward_name", "property_type_name"]


def main() -> None:
    posts = pd.read_parquet(PROCESSED_DIR / "posts.parquet")
    summary = summarize(posts)

    last = posts.sort_values("published_at").groupby("property_id").last()
    props = last[[*CATEGORIES, "area", "floor_count", "bedroom_count", "name"]].join(summary)
    # Many listings leave the floor field empty but say "5 tầng" in the title.
    from_title = extract(props["name"].fillna("").str.lower())["txt_floors"]
    props["floor_count"] = props["floor_count"].fillna(from_title)
    props = props.drop(columns=["name", "min_price", "max_price"]).astype(
        {
            **{c: "category" for c in CATEGORIES},
            "floor_count": "float32",
            "bedroom_count": "float32",
            "posts": "int32",
            "price_changes": "int32",
            "returns": "int32",
            "days_listed": "int32",
            "change": "float32",
        }
    )

    # 32-bit hashes are enough: a match also needs the same ward, type and exact area.
    hist = posts[["property_id", "published_at", "price", "desc_hash", "title_hash"]].copy()
    for col in ("desc_hash", "title_hash"):
        hist[col] = (hist[col] & 0xFFFFFFFF).astype("uint32")

    pulse = monthly_pulse(props.reset_index())
    samples = pd.read_parquet(PROCESSED_DIR / "samples.parquet")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    props.to_parquet(DATA_DIR / "properties.parquet", compression="zstd")
    hist.to_parquet(DATA_DIR / "posts.parquet", compression="zstd", index=False)
    pulse.to_parquet(DATA_DIR / "pulse.parquet", compression="zstd", index=False)
    samples.to_parquet(DATA_DIR / "samples.parquet", compression="zstd", index=False)

    archive = DATA_DIR.parent / f"soi-gia-nha-data-{DATA_VERSION}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:  # parquet is compressed already
        for f in DATA_FILES:
            z.write(DATA_DIR / f, f)
    for f in DATA_FILES:
        print(f"{(DATA_DIR / f).stat().st_size / 1e6:6.1f} MB  {f}")
    print(f"{archive.stat().st_size / 1e6:6.1f} MB  {archive.name}")
    print(f"{len(props):,} properties, {len(hist):,} posts, {len(pulse):,} trend rows")


if __name__ == "__main__":
    main()
