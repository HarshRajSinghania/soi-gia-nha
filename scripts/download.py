"""Download the raw listings (~1.7 GB, 10 parquet shards) into data/raw/.

python scripts/download.py            # everything
python scripts/download.py --shards 1 # one shard (~350k rows), enough to try things out
"""

import argparse

from soi_gia_nha.data import N_SHARDS, download


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shards", type=int, default=N_SHARDS, help="number of shards to fetch")
    args = ap.parse_args()

    for p in download(args.shards):
        print(f"{p.stat().st_size / 1e6:7.1f} MB  {p.name}")


if __name__ == "__main__":
    main()
