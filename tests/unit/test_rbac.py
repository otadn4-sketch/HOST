from app.models.entities import FileObject, FilePermission, User
from app.security.rbac import can_see_dashboard, can_upload, evaluate_file_access


def _user(role, uid="u1", gid="g1"):
    return User(id=uid, username=uid, full_name=uid, email=f"{uid}@x.local", password_hash="x", role=role, group_id=gid, status="active")


def _file(**kwargs):
    data = dict(
        id="f1",
        title="t",
        original_name="a.pdf",
        stored_name="abc",
        storage_relpath="abc",
        topic="t",
        group_id="g1",
        uploader_id="u1",
        size_bytes=10,
        mime_type="application/pdf",
        detected_mime="application/pdf",
        extension="pdf",
        classification="internal",
        scan_status="clean",
        sha256="a" * 64,
    )
    data.update(kwargs)
    return FileObject(**data)


def test_viewer_cannot_upload():
    assert not can_upload(_user("viewer"))
    assert can_upload(_user("user"))


def test_dashboard_admin_only():
    assert can_see_dashboard(_user("system_admin"))
    assert not can_see_dashboard(_user("group_admin"))
    assert not can_see_dashboard(_user("user"))


def test_quarantine_not_downloadable():
    admin = _user("system_admin", "admin")
    f = _file(scan_status="quarantined", uploader_id="u2", quarantine_reason="شناسایی بدافزار: Eicar-Test-Signature")
    access = evaluate_file_access(admin, f, [])
    assert access.can_view
    assert not access.can_download


def test_unscanned_file_not_treated_safe():
    admin = _user("system_admin", "admin")
    f = _file(scan_status="quarantined", uploader_id="u2", quarantine_reason="پویش بدافزار در دسترس نبود؛ فایل امن تلقی نشد")
    access = evaluate_file_access(admin, f, [])
    assert access.can_view
    assert not access.can_download


def test_explicit_permission():
    viewer = _user("viewer", "v1", "g2")
    f = _file(classification="confidential", group_id="g1", uploader_id="u9")
    perm = FilePermission(
        file_id="f1",
        target_type="user",
        target_id="v1",
        can_view=True,
        can_download=True,
        can_upload=False,
        can_manage=False,
        granted_by="admin",
    )
    access = evaluate_file_access(viewer, f, [perm])
    assert access.can_view
    assert access.can_download
    assert not access.can_upload
