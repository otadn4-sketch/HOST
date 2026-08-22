#!/usr/bin/env python3
"""Generate an Ed25519 keypair for signing release bundles.

The private key must stay offline with the release team. Only the public key
is copied to the server as UPDATE_PUBLIC_KEY.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nacl.signing import SigningKey


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="./release-keys")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sk = SigningKey.generate()
    (out / "ed25519.secret").write_bytes(sk.encode())
    (out / "ed25519.secret").chmod(0o600)
    (out / "ed25519.pub").write_text(sk.verify_key.encode().hex() + "\n", encoding="utf-8")
    print(f"wrote {out/'ed25519.secret'} (KEEP OFFLINE)")
    print(f"wrote {out/'ed25519.pub'} -> set UPDATE_PUBLIC_KEY to this hex value")


if __name__ == "__main__":
    main()
