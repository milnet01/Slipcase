#!/usr/bin/env python3
"""Sign one release download with the key in SLIPCASE_SIGNING_KEY (SLIP-0030).

Writes <file>.sig, the raw 64-byte Ed25519 signature over the file's exact
bytes, then checks it against the public key committed in
core/update_key.py. A key that does not match, or is missing or malformed,
leaves no .sig and fails the release job before anything is uploaded. The
key is read from the environment only: never written, never printed.

Usage: python scripts/sign-release.py <file>
Exits 0 when <file>.sig is written and verifies, 1 otherwise.
"""

import base64
import binascii
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cryptography.exceptions import InvalidSignature  # noqa: E402 -- after the path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from core import update_key  # noqa: E402


def _fail(message: str) -> int:
    print(f"sign-release: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return _fail("usage: sign-release.py <file>")
    target = Path(args[0])
    sig = Path(f"{target}.sig")

    # The messages below name the problem, never the value.
    encoded = os.environ.get("SLIPCASE_SIGNING_KEY", "").strip()
    if not encoded:
        return _fail("SLIPCASE_SIGNING_KEY is not set")
    try:
        seed = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return _fail("SLIPCASE_SIGNING_KEY is not base64")
    if len(seed) != 32:
        return _fail("SLIPCASE_SIGNING_KEY is not a 32-byte Ed25519 seed")

    data = target.read_bytes()
    signature = Ed25519PrivateKey.from_private_bytes(seed).sign(data)
    sig.write_bytes(signature)
    try:
        update_key.public_key().verify(signature, data)
    except InvalidSignature:
        sig.unlink()
        return _fail("the key does not match core/update_key.py; nothing signed")
    print(f"signed {target.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
