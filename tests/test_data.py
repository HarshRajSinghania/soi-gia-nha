import pandas as pd
import pytest

from soi_gia_nha.data import load_raw, shard_names


def test_shard_names():
    assert shard_names(3) == ["shard_0000.parquet", "shard_0001.parquet", "shard_0002.parquet"]


def test_load_raw_without_download(tmp_path):
    with pytest.raises(FileNotFoundError, match="scripts/download.py"):
        load_raw(src=tmp_path)


def test_load_raw_reads_shards_in_order(tmp_path):
    for i in range(3):
        pd.DataFrame({"price": [str(i)], "area": [float(i)]}).to_parquet(
            tmp_path / f"shard_{i:04d}.parquet"
        )
    df = load_raw(columns=["price"], shards=2, src=tmp_path)
    assert df["price"].tolist() == ["0", "1"]
    assert list(df.columns) == ["price"]
