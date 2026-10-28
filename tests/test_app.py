"""Smoke test for the Streamlit app. Needs the trained model, so CI skips it."""

from pathlib import Path

import pytest

from soi_gia_nha.assets import DATA_DIR, DATA_FILES, MODEL_DIR, REQUIRED

pytestmark = pytest.mark.skipif(
    not all((MODEL_DIR / f).exists() for f in REQUIRED), reason="trained model not available"
)
APP = str(Path(__file__).resolve().parents[1] / "app" / "app.py")


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()


def test_example_listing_gets_a_verdict():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=300).run()
    click(at, "Soi giá")
    assert not at.exception
    assert any("Khoảng giá hợp lý" in m.value for m in at.markdown)


def test_missing_price_is_reported():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=300).run()
    at.number_input[0].set_value(0.0).run()
    click(at, "Soi giá")
    assert at.error


DATA_READY = all((DATA_DIR / f).exists() for f in DATA_FILES)


@pytest.mark.skipif(not DATA_READY, reason="app data not available")
def test_real_listing_shows_its_history():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=300).run()
    click(at, "Lấy một tin có thật để thử")
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Thời gian trên sàn" in html
    assert "Căn giống nhất đã rao" in html
