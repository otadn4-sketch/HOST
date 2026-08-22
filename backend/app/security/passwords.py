from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

# Dummy hash used only to equalize login timing when the username is unknown.
# This is not a credential and cannot be used to log in.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=2$"
    "dGhlZHVtbXlzb2RpZXMxMjM0NQ$uV0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0m0"
)

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash, Exception):
        return False


def dummy_verify(password: str) -> None:
    try:
        _ph.verify(_DUMMY_HASH, password)
    except Exception:
        return


_SPECIAL = re.compile(r"[^A-Za-z0-9]")
_DIGIT = re.compile(r"\d")
_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")


def validate_password_policy(
    password: str, *, min_length: int = 12, require_special: bool = True
) -> str | None:
    if len(password) < min_length:
        return f"گذرواژه باید حداقل {min_length} نویسه باشد."
    if len(password) > 200:
        return "گذرواژه بیش از حد طولانی است."
    if not _LOWER.search(password) or not _UPPER.search(password) or not _DIGIT.search(password):
        return "گذرواژه باید شامل حروف بزرگ، حروف کوچک و رقم باشد."
    if require_special and not _SPECIAL.search(password):
        return "گذرواژه باید حداقل یک نویسه ویژه داشته باشد."
    return None
