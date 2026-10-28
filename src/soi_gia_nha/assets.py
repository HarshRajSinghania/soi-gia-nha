"""Fetch the trained model from the GitHub release when it is not on disk."""

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


def ensure_model(dest: Path = MODEL_DIR, url: str = MODEL_URL) -> Path:
    """Return the model directory, downloading and unpacking the release asset if needed."""
    if all((dest / f).exists() for f in REQUIRED):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r:
        zipfile.ZipFile(io.BytesIO(r.read())).extractall(dest)
    missing = [f for f in REQUIRED if not (dest / f).exists()]
    if missing:
        raise RuntimeError(f"model archive from {url} is missing {missing}")
    return dest
