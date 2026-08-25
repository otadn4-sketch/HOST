from __future__ import annotations

import argparse
import getpass
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.models.entities import Group, User
from app.security.passwords import hash_password, validate_password_policy
from app.services.backup import create_backup, restore_database_backup, restore_vault_backup
from app.services.bootstrap import bootstrap_schema
from app.services.policy import get_or_create_policy


def create_admin(username: str, full_name: str, email: str, password: str, group_code: str = "SEC-IT") -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    Session = make_session_factory(engine)
    db = Session()
    try:
        bootstrap_schema(db)
        policy = get_or_create_policy(db)
        err = validate_password_policy(
            password, min_length=policy.password_min_length, require_special=policy.require_special_chars
        )
        if err:
            raise SystemExit(err)
        if db.query(User).filter(User.username == username).one_or_none():
            raise SystemExit("این نام کاربری موجود است.")
        group = db.query(Group).filter(Group.code == group_code).one_or_none()
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="system_admin",
            group_id=group.id if group else None,
            status="active",
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        print(f"admin created: {username}")
    finally:
        db.close()


def _sqlite_path(url: str) -> Path | None:
    if not url.startswith("sqlite"):
        return None
    raw = url.split("://", 1)[-1]
    if raw.startswith("///"):
        return Path(raw[3:])
    parsed = urlparse(url.replace("sqlite+pysqlite", "sqlite"))
    if parsed.path:
        return Path(parsed.path)
    return None


def dump_database_bytes(settings) -> bytes:
    sqlite_path = _sqlite_path(settings.database_url)
    if sqlite_path and sqlite_path.is_file():
        return sqlite_path.read_bytes()
    pg_dump = shutil.which("pg_dump")
    if pg_dump:
        url = settings.database_url.replace("postgresql+psycopg", "postgresql")
        proc = subprocess.run([pg_dump, "--no-owner", "--format=custom", url], check=True, capture_output=True)
        return proc.stdout
    raise SystemExit("no local database dump method available (sqlite file missing and pg_dump not found)")


def run_backup(note: str = "") -> None:
    settings = get_settings()
    dump = dump_database_bytes(settings)
    pair = create_backup(settings, dump, note=note)
    print(f"encrypted database backup: {pair.db_archive}")
    print(f"encrypted vault backup: {pair.vault_archive}")
    extra = settings.backup_external_path
    if extra:
        extra = Path(extra)
        if extra.exists() and extra.is_dir():
            shutil.copy2(pair.db_archive, extra / pair.db_archive.name)
            shutil.copy2(pair.vault_archive, extra / pair.vault_archive.name)
            print(f"copied encrypted backups to {extra}")
        else:
            print(f"BACKUP_EXTERNAL_PATH is not an existing directory; local copies kept at {settings.backup_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Eytan admin CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-admin")
    p.add_argument("--username", required=True)
    p.add_argument("--full-name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", default="")
    p.add_argument("--group-code", default="SEC-IT")
    b = sub.add_parser("backup", help="Write separate encrypted database and vault backups")
    b.add_argument("--note", default="")
    rd = sub.add_parser("restore-db", help="Decrypt a database backup to a file (does not load into live DB)")
    rd.add_argument("--archive", required=True)
    rd.add_argument("--out", required=True)
    rv = sub.add_parser("restore-vault", help="Decrypt a vault backup into a destination directory")
    rv.add_argument("--archive", required=True)
    rv.add_argument("--dest", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "create-admin":
        password = args.password or getpass.getpass("password: ")
        create_admin(args.username, args.full_name, args.email, password, args.group_code)
        return
    settings = get_settings()
    if args.cmd == "backup":
        run_backup(note=args.note)
        return
    if args.cmd == "restore-db":
        dump = restore_database_backup(settings, Path(args.archive))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(dump)
        print(f"wrote decrypted database dump to {out}")
        return
    if args.cmd == "restore-vault":
        dest = Path(args.dest)
        live = settings.vault_path.resolve()
        if dest.resolve() == live:
            raise SystemExit("refusing to restore into the live vault; choose a separate --dest directory")
        restore_vault_backup(settings, Path(args.archive), dest)
        print(f"restored vault files into {dest}")


if __name__ == "__main__":
    main(sys.argv[1:])
