from app.security.passwords import hash_password, validate_password_policy, verify_password


def test_argon2id_roundtrip():
    h = hash_password("Str0ng-Passw0rd!")
    assert h.startswith("$argon2id$")
    assert verify_password("Str0ng-Passw0rd!", h)
    assert not verify_password("wrong", h)


def test_policy():
    assert validate_password_policy("short") is not None
    assert validate_password_policy("NoSpecial1234") is not None
    assert validate_password_policy("Str0ng-Passw0rd!") is None
