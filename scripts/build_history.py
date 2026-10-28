"""Link reposts of the same property, write data/processed/posts.parquet and reports/history.md.

python scripts/build_history.py
"""

import pandas as pd

from soi_gia_nha.clean import DEFAULT_PROVINCES, clean
from soi_gia_nha.data import COLUMNS, PROCESSED_DIR, RAW_DIR, ROOT
from soi_gia_nha.history import BLOCK, add_ids, summarize

KEEP = [
    "name",
    "description",
    "province_name",
    *BLOCK,
    "price",
    "published_at",
    "floor_count",
    "bedroom_count",
    "frontage_width",
]
CHECK = [
    ("floor_count", 0, "Floors"),
    ("bedroom_count", 0, "Bedrooms"),
    ("frontage_width", 0.1, "Frontage"),
]


def load_posts() -> pd.DataFrame:
    # One shard at a time: the descriptions of all 3.5M posts do not fit in 16 GB at once.
    parts = [
        clean(pd.read_parquet(f, columns=COLUMNS), DEFAULT_PROVINCES, drop_reposts=False)[KEEP]
        for f in sorted(RAW_DIR.glob("shard_*.parquet"))
    ]
    return pd.concat(parts, ignore_index=True).sort_values("published_at", kind="stable")


def agreement(df: pd.DataFrame, group: str, col: str, tol: float) -> tuple[float, int]:
    """Share of later posts in a group whose ``col`` matches the group's first post."""
    first = df.groupby(group)[col].transform("first")
    later = df[group].duplicated(keep="first")
    m = later & df[col].notna() & first.notna()
    return float(((df.loc[m, col] - first[m]).abs() <= tol).mean()), int(m.sum())


def pct(x: float) -> str:
    return f"{x:.1%}"


def main() -> None:
    posts = add_ids(load_posts()).drop(columns=["description"])
    posts["name"] = posts["name"].str.slice(0, 90)
    summary = summarize(posts)

    multi = summary[summary["posts"] > 1]
    changed = summary[summary["price_changes"] > 0]
    long = summary[summary["days_listed"] >= 60]
    cuts = changed.loc[changed["change"] < 0, "change"]
    raises = changed.loc[changed["change"] > 0, "change"]

    # Baseline for the agreement check: posts in the same block that were NOT linked.
    block_id = posts.groupby(BLOCK, dropna=False).ngroup()
    unlinked = posts.assign(block=block_id).drop_duplicates("property_id")

    lines = [
        "# Listing history",
        "",
        f"Produced by `scripts/build_history.py` on {len(posts):,} cleaned posts from Hanoi and "
        "Ho Chi Minh City, June 2025 to March 2026, reposts included.",
        "",
        "Two posts are the same property when district, ward, type and exact area match, and the "
        "description or the title matches with numbers, punctuation and case ignored.",
        "",
        "| | |",
        "|---|---:|",
        f"| Posts | {len(posts):,} |",
        f"| Distinct properties | {len(summary):,} |",
        f"| Posts that repeat an earlier property | {pct(1 - len(summary) / len(posts))} |",
        f"| Properties posted more than once | {len(multi):,} ({pct(len(multi) / len(summary))}) |",
        f"| Most posts for one property | {summary['posts'].max():,} |",
        f"| Properties whose asking price changed | {len(changed):,} |",
        f"| … of which the last price is lower | {pct((changed['change'] < 0).mean())} |",
        f"| … of which the last price is higher | {pct((changed['change'] > 0).mean())} |",
        f"| Median change when lowered | {pct(cuts.median())} |",
        f"| Median change when raised | {pct(raises.median())} |",
        f"| Listed for 60 days or more | {len(long):,} |",
        "",
        "## Is it really the same property?",
        "",
        "There is no ground truth, so the check uses details the seller typed into separate "
        "fields: a repost of the same property should repeat them. *Linked* compares each "
        "repost with the first post of its property. *Same block, not linked* compares "
        "different properties that share district, ward, type and area, the closest thing "
        "to a false link.",
        "",
        "| Field | Linked reposts agree | Same block, not linked |",
        "|---|---:|---:|",
    ]
    for col, tol, label in CHECK:
        a, n = agreement(posts, "property_id", col, tol)
        b, m = agreement(unlinked, "block", col, tol)
        lines.append(f"| {label} | {pct(a)} ({n:,}) | {pct(b)} ({m:,}) |")
    lines += [
        "",
        "Agents also reuse one text for several units of the same size in a project, and "
        "those get merged. The table above bounds how often that happens; it does not rule it out.",
        "",
    ]

    out = ROOT / "reports" / "history.md"
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    posts.to_parquet(PROCESSED_DIR / "posts.parquet", index=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
