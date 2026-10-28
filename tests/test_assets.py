import zipfile

import pytest

from soi_gia_nha.assets import REQUIRED, ensure_model


def make_archive(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name in files:
            z.writestr(name, "x")
    return path.as_uri()


def test_downloads_and_unpacks(tmp_path):
    url = make_archive(tmp_path / "m.zip", REQUIRED)
    dest = ensure_model(tmp_path / "model", url)
    assert all((dest / f).exists() for f in REQUIRED)


def test_skips_download_when_present(tmp_path):
    dest = tmp_path / "model"
    dest.mkdir()
    for f in REQUIRED:
        (dest / f).write_text("x")
    assert ensure_model(dest, "file:///does/not/exist.zip") == dest


def test_incomplete_archive_is_an_error(tmp_path):
    url = make_archive(tmp_path / "m.zip", REQUIRED[:2])
    with pytest.raises(RuntimeError, match="missing"):
        ensure_model(tmp_path / "model", url)


def test_data_bundle_uses_the_same_mechanism(tmp_path):
    from soi_gia_nha.assets import DATA_FILES, ensure_data

    url = make_archive(tmp_path / "d.zip", DATA_FILES)
    dest = ensure_data(tmp_path / "data", url)
    assert all((dest / f).exists() for f in DATA_FILES)
