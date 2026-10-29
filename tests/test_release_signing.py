"""Tests for release signing (SLIP-0030, docs/specs/SLIP-0030-release-signing.md).

They run offline, make a throwaway key per test and never read the real
secret.
"""

import base64
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _script(name: str):
    """Load scripts/<name>.py as a module; the dashes keep it from importing."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _throwaway_key() -> tuple[str, str]:
    """A fresh (seed, public key) pair, both base64."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(seed).decode(), base64.b64encode(public).decode()


class TestSign(unittest.TestCase):
    """INV-1 and INV-2: scripts/sign-release.py."""

    def setUp(self):
        self.signer = _script("sign-release")
        self.dir = tempfile.TemporaryDirectory()
        self.file = Path(self.dir.name) / "Slipcase-x86_64.AppImage"
        self.file.write_bytes(os.urandom(4096))
        self.sig = Path(f"{self.file}.sig")
        self.seed, self.public = _throwaway_key()

    def tearDown(self):
        self.dir.cleanup()

    def _sign(self, seed: str | None, public: str):
        env = {k: v for k, v in os.environ.items() if k != "SLIPCASE_SIGNING_KEY"}
        if seed is not None:
            env["SLIPCASE_SIGNING_KEY"] = seed
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, env, clear=True), \
                patch("core.update_key.RELEASE_PUBLIC_KEY_B64", public), \
                redirect_stdout(out), redirect_stderr(err):
            code = self.signer.main([str(self.file)])
        return code, out.getvalue() + err.getvalue()

    def test_round_trip_and_tamper(self):
        from cryptography.exceptions import InvalidSignature

        import core.update_key as update_key

        code, _ = self._sign(self.seed + "\n", self.public)
        self.assertEqual(code, 0)
        signature = self.sig.read_bytes()
        self.assertEqual(len(signature), 64)
        with patch("core.update_key.RELEASE_PUBLIC_KEY_B64", self.public):
            key = update_key.public_key()
        data = self.file.read_bytes()
        key.verify(signature, data)
        with self.assertRaises(InvalidSignature):
            key.verify(signature, data[:-1] + bytes([data[-1] ^ 1]))
        with self.assertRaises(InvalidSignature):
            key.verify(bytes([signature[0] ^ 1]) + signature[1:], data)

    def test_refuses_bad_key(self):
        other_seed, _ = _throwaway_key()
        for label, seed in (("unset", None), ("not base64", "not-base64!"),
                            ("not the committed key", other_seed)):
            with self.subTest(label):
                code, output = self._sign(seed, self.public)
                self.assertNotEqual(code, 0)
                self.assertFalse(self.sig.exists())
                if seed:
                    self.assertNotIn(seed, output)


class TestWorkflow(unittest.TestCase):
    """INV-4 and INV-5, read from release.yml as text."""

    ASSETS = {"linux": ["Slipcase-x86_64.AppImage"],
              "windows": ["Slipcase-windows-x64.exe"],
              "macos": ["Slipcase-macos-${{ matrix.arch }}.dmg", "Slipcase-macos-$ARCH.dmg"]}

    @classmethod
    def setUpClass(cls):
        text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        cls.jobs = {}
        jobs = text.split("\njobs:\n", 1)[1]
        for name, body in re.findall(r"^  (\w+):\n(.*?)(?=^  \w+:\n|\Z)", jobs, re.M | re.S):
            cls.jobs[name] = re.split(r"^      - (?=name:|uses:)", body, flags=re.M)[1:]

    def test_secret_only_in_sign_steps(self):
        self.assertEqual(sorted(self.jobs), sorted(self.ASSETS))
        for job, steps in self.jobs.items():
            with self.subTest(job):
                holders = [s for s in steps if "secrets.SLIPCASE_SIGNING_KEY" in s]
                signers = [s for s in steps if s.startswith("name: Sign the download")]
                self.assertEqual(len(signers), 1)
                self.assertEqual(holders, signers)

    def test_sig_uploaded(self):
        for job, steps in self.jobs.items():
            with self.subTest(job):
                artifact = next(s for s in steps if "actions/upload-artifact" in s)
                release = next(s for s in steps if "gh release upload" in s)
                self.assertIn(f"dist/{self.ASSETS[job][0]}.sig", artifact)
                self.assertIn(f"dist/{self.ASSETS[job][-1]}.sig", release)


class TestKeyCustody(unittest.TestCase):

    def test_public_key_loads(self):
        """INV-6: the committed public key is 32 bytes of base64."""
        import core.update_key as update_key

        raw = base64.b64decode(update_key.RELEASE_PUBLIC_KEY_B64, validate=True)
        self.assertEqual(len(raw), 32)
        update_key.public_key()

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

    def test_its_key_signs_what_the_signer_accepts(self):
        public = self.keygen.generate_keypair(self.key)
        target = Path(self.dir.name) / "Slipcase-windows-x64.exe"
        target.write_bytes(b"build")
        seed = self.key.read_text()
        with patch.dict(os.environ, {"SLIPCASE_SIGNING_KEY": seed}), \
                patch("core.update_key.RELEASE_PUBLIC_KEY_B64", public), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(_script("sign-release").main([str(target)]), 0)
        self.assertEqual(len(Path(f"{target}.sig").read_bytes()), 64)


if __name__ == "__main__":
    unittest.main()
