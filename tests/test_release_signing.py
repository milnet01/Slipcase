"""Tests for release signing (SLIP-0030, docs/specs/SLIP-0030-release-signing.md).

They run offline, make a throwaway key per test and never read the real
secret.
"""

import base64
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _script(name: str):
    """Load scripts/<name>.py as a module; the dashes keep it from importing."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestKeyCustody(unittest.TestCase):

    def test_no_private_key_tracked(self):
        """INV-3: no tracked path ends in .key or lies under release/, and no
        tracked file holds a PEM private-key block. The marker is assembled
        here so this file does not trip its own scan."""
        tracked = subprocess.run(  # noqa: S603 -- fixed arguments
            ["git", "ls-files"],  # noqa: S607 -- git from PATH
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        marker = re.compile(("-----BEGIN [A-Z ]*" + "PRIVATE KEY-----").encode())
        for rel in tracked:
            self.assertFalse(rel.endswith(".key"), f"key file tracked: {rel}")
            self.assertFalse(rel.startswith("release/"), f"release/ file tracked: {rel}")
            path = ROOT / rel
            if path.is_file():
                self.assertIsNone(marker.search(path.read_bytes()),
                                  f"PEM private key tracked in: {rel}")


class TestKeygen(unittest.TestCase):
    """INV-7, the half that needs no signing script: the key file is made
    once, owner-only, and holds a seed the signer can read."""

    def setUp(self):
        self.keygen = _script("gen-signing-key")
        self.dir = tempfile.TemporaryDirectory()
        self.key = Path(self.dir.name) / "release" / "slipcase-signing.key"

    def tearDown(self):
        self.dir.cleanup()

    def test_writes_a_seed_line_and_returns_its_public_key(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        public_b64 = self.keygen.generate_keypair(self.key)
        seed = base64.b64decode(self.key.read_text().strip(), validate=True)
        self.assertEqual(len(seed), 32)
        public = Ed25519PrivateKey.from_private_bytes(seed).public_key()
        self.assertEqual(base64.b64encode(public.public_bytes(Encoding.Raw, PublicFormat.Raw)),
                         public_b64.encode())

    def test_refuses_to_overwrite(self):
        self.keygen.generate_keypair(self.key)
        before = self.key.read_bytes()
        with self.assertRaises(FileExistsError):
            self.keygen.generate_keypair(self.key)
        self.assertEqual(self.key.read_bytes(), before)

    @unittest.skipIf(os.name == "nt", "Windows has no permission bits")
    def test_key_file_is_owner_only(self):
        self.keygen.generate_keypair(self.key)
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
