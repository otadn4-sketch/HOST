from __future__ import annotations

import argparse
import getpass
import sys

from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.models.entities import Group, User
from app.security.passwords import hash_password, validate_password_policy
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Eytan admin CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-admin")
    p.add_argument("--username", required=True)
    p.add_argument("--full-name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", default="")
    p.add_argument("--group-code", default="SEC-IT")
    args = parser.parse_args(argv)
    password = args.password or getpass.getpass("password: ")
    create_admin(args.username, args.full_name, args.email, password, args.group_code)


if __name__ == "__main__":
    main(sys.argv[1:])
