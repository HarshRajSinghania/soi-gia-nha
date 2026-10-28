"""Download and load the TiniX Vietnam real estate listings."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ID = "tinixai/vietnam-real-estates"
# Pinned so that everyone trains on exactly the same snapshot.
REVISION = "ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f"
N_SHARDS = 10

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

COLUMNS = [
    "name",
    "description",
    "property_type_name",
    "province_name",
    "district_name",
    "ward_name",
    "street_name",
    "project_name",
    "price",
    "area",
    "floor_count",
    "frontage_width",
    "house_depth",
    "road_width",
    "bedroom_count",
    "bathroom_count",
    "house_direction",
    "balcony_direction",
    "published_at",
]


def shard_names(n: int = N_SHARDS) -> list[str]:
    return [f"shard_{i:04d}.parquet" for i in range(n)]


def download(shards: int = N_SHARDS, dest: Path = RAW_DIR) -> list[Path]:
    """Fetch the parquet shards into ``dest``. Already downloaded files are reused."""
    from huggingface_hub import hf_hub_download

    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in shard_names(shards):
        p = hf_hub_download(REPO_ID, name, repo_type="dataset", revision=REVISION, local_dir=dest)
        paths.append(Path(p))
    return paths


def load_raw(
    columns: list[str] | None = None,
    shards: int | None = None,
    src: Path = RAW_DIR,
) -> pd.DataFrame:
    """Read the downloaded shards. Pass ``columns`` to keep memory down on the full 3.5M rows."""
    files = sorted(src.glob("shard_*.parquet"))
    if shards is not None:
        files = files[:shards]
    if not files:
        raise FileNotFoundError(f"no shards in {src}, run `python scripts/download.py` first")
    return pd.concat((pd.read_parquet(f, columns=columns) for f in files), ignore_index=True)
