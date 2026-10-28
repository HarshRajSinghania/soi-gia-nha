"""Smoke test for the Streamlit app. Needs the trained model, so CI skips it."""

from pathlib import Path

import pytest

from soi_gia_nha.assets import MODEL_DIR, REQUIRED

pytestmark = pytest.mark.skipif(
    not all((MODEL_DIR / f).exists() for f in REQUIRED), reason="trained model not available"
)
APP = str(Path(__file__).resolve().parents[1] / "app" / "app.py")


def test_example_listing_gets_a_verdict():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=300).run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Khoảng giá hợp lý" in m.value for m in at.markdown)


def test_missing_price_is_reported():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=300).run()
    at.number_input[0].set_value(0.0).run()
    at.button[0].click().run()
    assert at.error
