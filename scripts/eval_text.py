"""Check the text extraction against the structured columns sellers filled in themselves.

python scripts/eval_text.py   # writes reports/text_extraction.md
"""

from soi_gia_nha.clean import DEFAULT_PROVINCES, clean
from soi_gia_nha.data import COLUMNS, ROOT, load_raw
from soi_gia_nha.text import FLAGS, extract, prepare_text

PAIRS = [
    ("floor_count", "txt_floors", "Floors", 0),
    ("bedroom_count", "txt_bedrooms", "Bedrooms", 0),
    ("frontage_width", "txt_frontage", "Frontage width (m)", 0.5),
    ("road_width", "txt_road", "Road / alley width (m)", 0.5),
]


def main() -> None:
    df = clean(load_raw(columns=COLUMNS), DEFAULT_PROVINCES)
    feats = extract(prepare_text(df["name"], df["description"]))
    n = len(df)

    lines = [
        "# Text extraction",
        "",
        f"Measured on the {n:,} cleaned listings by `scripts/eval_text.py`.",
        "",
        "**Agreement** compares the value read from the text with the value the seller entered "
        "in the structured field, on listings that have both. **Missing** is the share of "
        "listings with no value, before and after reading the text.",
        "",
        "| Field | Listings with both | Agreement | Missing before | Missing after |",
        "|---|---:|---:|---:|---:|",
    ]
    for col, txt, label, tol in PAIRS:
        both = df[col].notna() & feats[txt].notna()
        agree = ((df.loc[both, col] - feats.loc[both, txt]).abs() <= tol).mean()
        before = df[col].isna().mean()
        after = (df[col].isna() & feats[txt].isna()).mean()
        tol_note = f" (±{tol} m)" if tol else ""
        lines.append(
            f"| {label} | {both.sum():,} | {agree:.1%}{tol_note} | {before:.1%} | {after:.1%} |"
        )

    lines += ["", "Flags found in the text:", "", "| Flag | Listings |", "|---|---:|"]
    for flag in FLAGS:
        lines.append(f"| `{flag}` | {feats[flag].mean():.1%} |")

    out = ROOT / "reports" / "text_extraction.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
