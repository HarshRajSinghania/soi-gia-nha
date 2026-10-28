import unicodedata

import pandas as pd
import pytest

from soi_gia_nha.admin import attach_new_units, canon


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Phường 07", "7"),
        ("Quận Cầu Giấy", "cầu giấy"),
        ("Trung Hòa", "trung hoà"),
        ("Trung Hoà", "trung hoà"),
        ("Thụy Lâm", "thuỵ lâm"),
        ("Hoàng Mai", "hoàng mai"),
        ("  Thành phố   Hồ Chí Minh ", "hồ chí minh"),
        (None, None),
        (float("nan"), None),
    ],
)
def test_canon(raw, expected):
    assert canon(raw) == expected


def test_canon_handles_decomposed_input():
    nfd = unicodedata.normalize("NFD", "Phường Trung Hòa")
    assert nfd != "Phường Trung Hòa"
    assert canon(nfd) == "trung hoà"


def test_attach_new_units():
    admin_map = pd.DataFrame(
        {
            "province_key": ["hồ chí minh", "hồ chí minh"],
            "district_key": ["7", "1"],
            "ward_key": ["tân quy", "7"],
            "new_province": ["Thành phố Hồ Chí Minh"] * 2,
            "new_ward": ["Phường Tân Hưng", "Phường A / Phường B"],
            "ambiguous": [False, True],
        }
    )
    listings = pd.DataFrame(
        {
            "province_name": ["Hồ Chí Minh", "Hồ Chí Minh", "Hồ Chí Minh"],
            "district_name": ["7", "1", "7"],
            "ward_name": ["Tân Quy", "07", None],
        },
        index=[10, 11, 12],
    )
    out = attach_new_units(listings, admin_map)
    assert out.index.tolist() == [10, 11, 12]
    assert out["new_ward"].tolist()[:2] == ["Phường Tân Hưng", "Phường A / Phường B"]
    assert pd.isna(out["new_ward"].iloc[2])
    assert out["ambiguous"].tolist() == [False, True, False]
