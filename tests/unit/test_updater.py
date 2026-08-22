from pathlib import Path

from app.services.updater import apply_extracted_release, merge_tree


def test_merge_tree_overwrites_without_deleting_extra(tmp_path: Path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    (src / "a").mkdir(parents=True)
    (src / "a" / "new.py").write_text("new")
    (dest / "a").mkdir(parents=True)
    (dest / "a" / "old.py").write_text("old")
    (dest / "keep.txt").write_text("keep")
    merge_tree(src, dest)
    assert (dest / "a" / "new.py").read_text() == "new"
    assert (dest / "a" / "old.py").read_text() == "old"
    assert (dest / "keep.txt").read_text() == "keep"


def test_apply_extracted_release_copies_backend(tmp_path: Path, monkeypatch):
    work = tmp_path / "work"
    (work / "backend" / "app").mkdir(parents=True)
    (work / "backend" / "app" / "mod.py").write_text("ok")
    (work / "VERSION").write_text("9.9.9\n")
    live = tmp_path / "live"
    (live / "app").mkdir(parents=True)
    monkeypatch.setenv("EYTAN_APP_ROOT", str(live))
    monkeypatch.setenv("OVERLAY_FRONTEND_PATH", str(tmp_path / "missing-fe"))
    notes = apply_extracted_release(work)
    assert (live / "app" / "mod.py").read_text() == "ok"
    assert (live / "VERSION").read_text().strip() == "9.9.9"
    assert any("backend/app" in n for n in notes)
