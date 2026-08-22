import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "backend" / "docker-entrypoint.py"
    spec = importlib.util.spec_from_file_location("eytan_backend_entry", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_ver_and_sync_when_image_newer(tmp_path):
    mod = _load()
    image = tmp_path / "image"
    dest = tmp_path / "live"
    (image / "app").mkdir(parents=True)
    (image / "app" / "main.py").write_text("new")
    (image / "VERSION").write_text("1.2.2\n")
    (dest / "app").mkdir(parents=True)
    (dest / "app" / "main.py").write_text("old")
    (dest / "VERSION").write_text("1.1.0\n")
    mod.IMAGE = image
    mod.DEST = dest
    mod.sync_image()
    assert (dest / "app" / "main.py").read_text() == "new"
    assert (dest / "VERSION").read_text().strip() == "1.2.2"


def test_sync_skips_when_live_is_newer(tmp_path):
    mod = _load()
    image = tmp_path / "image"
    dest = tmp_path / "live"
    (image / "app").mkdir(parents=True)
    (image / "app" / "main.py").write_text("image")
    (image / "VERSION").write_text("1.2.0\n")
    (dest / "app").mkdir(parents=True)
    (dest / "app" / "main.py").write_text("zip-applied")
    (dest / "VERSION").write_text("1.2.2\n")
    mod.IMAGE = image
    mod.DEST = dest
    mod.sync_image()
    assert (dest / "app" / "main.py").read_text() == "zip-applied"
