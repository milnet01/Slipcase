"""The public half of the key that signs Slipcase's release downloads (SLIP-0030).

scripts/sign-release.py checks each new signature against it before a
release uploads anything, and the updater (SLIP-0031) refuses a download
whose signature it does not verify. The private half lives only in the
repository secret SLIPCASE_SIGNING_KEY and the maintainer's own backup;
scripts/gen-signing-key.py made the pair on 2026-10-29. Replacing this key
stops every installed copy accepting updates.
"""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

RELEASE_PUBLIC_KEY_B64 = "lA1YTXnLVq0a2NtXanL6W7Gvior79fp+Cu8mpAc4G7U="


def public_key() -> Ed25519PublicKey:
    """The committed release public key."""
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(RELEASE_PUBLIC_KEY_B64, validate=True))
