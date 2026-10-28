"""Fetch the trained model and the app data from GitHub releases when they are not on disk."""

from __future__ import annotations

import io
import os
import urllib.request
import zipfile
from pathlib import Path

from .data import ROOT

MODEL_VERSION = "v0.1"
MODEL_URL = (
    "https://github.com/HongTin2104/soi-gia-nha/releases/download/"
    f"model-{MODEL_VERSION}/soi-gia-nha-model-{MODEL_VERSION}.zip"
)
MODEL_DIR = Path(os.environ.get("SOI_GIA_NHA_MODEL_DIR", ROOT / "models" / MODEL_VERSION))
REQUIRED = ["low.txt", "mid.txt", "high.txt", "meta.json", "ward_medians.parquet"]


DATA_VERSION = "v0.2"
DATA_URL = (
    "https://github.com/HongTin2104/soi-gia-nha/releases/download/"
    f"data-{DATA_VERSION}/soi-gia-nha-data-{DATA_VERSION}.zip"
)
DATA_DIR = Path(os.environ.get("SOI_GIA_NHA_DATA_DIR", ROOT / "data" / "app"))
DATA_FILES = ["properties.parquet", "posts.parquet", "pulse.parquet", "samples.parquet"]


def _ensure(dest: Path, url: str, required: list[str]) -> Path:
    if all((dest / f).exists() for f in required):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r:
        zipfile.ZipFile(io.BytesIO(r.read())).extractall(dest)
    missing = [f for f in required if not (dest / f).exists()]
    if missing:
        raise RuntimeError(f"archive from {url} is missing {missing}")
    return dest


def ensure_model(dest: Path = MODEL_DIR, url: str = MODEL_URL) -> Path:
    """Return the model directory, downloading and unpacking the release asset if needed."""
    return _ensure(dest, url, REQUIRED)


def ensure_data(dest: Path = DATA_DIR, url: str = DATA_URL) -> Path:
    """Return the app data directory (properties, post history, ward trends)."""
    return _ensure(dest, url, DATA_FILES)
