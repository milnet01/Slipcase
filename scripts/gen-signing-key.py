#!/usr/bin/env python3
"""Make the Ed25519 keypair that signs Slipcase's release downloads (SLIP-0030).

Run it once, by hand, in your own terminal:

    python3 scripts/gen-signing-key.py

It writes the private key's 32-byte seed, as one line of base64, to
release/slipcase-signing.key (git-ignored, owner-only). It prints only the
public key, as the line to paste into core/update_key.py. Then load the
secret, keep a copy in your password manager and delete the file:

    gh secret set SLIPCASE_SIGNING_KEY < release/slipcase-signing.key

Losing the key means no installed copy can be updated again, so keep that
copy. Ported from finbreak's script of the same name, which writes a PEM key
instead; one base64 line is what the GitHub secret holds.

Usage: python3 scripts/gen-signing-key.py [--out PATH]
Exits 0 after writing the key, 1 when the key file already exists.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

DEFAULT_KEY_PATH = Path("release/slipcase-signing.key")


def generate_keypair(dest: Path) -> str:
    """Write a new private key's seed to `dest` and return its public key in
    base64. Refuses an existing file: a new key would orphan every copy
    already installed."""
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; refusing to replace a signing key")
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Owner-only from the moment it exists, never a readable window.
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(base64.b64encode(seed).decode("ascii") + "\n")
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(public).decode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_KEY_PATH,
                        help=f"where to write the private key (default {DEFAULT_KEY_PATH})")
    args = parser.parse_args(argv)
    try:
        public_b64 = generate_keypair(args.out)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Private key written to {args.out} (owner-only, git-ignored).")
    print("Keep a copy in your password manager, load it into GitHub, then delete it:")
    print(f"    gh secret set SLIPCASE_SIGNING_KEY < {args.out}\n")
    print("Paste this line into core/update_key.py:\n")
    print(f'RELEASE_PUBLIC_KEY_B64 = "{public_b64}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
