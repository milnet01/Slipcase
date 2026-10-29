<!-- ants-spec-format: 1 -->
# SLIP-0030 — Sign every release download with Ed25519

**Status:** accepted (2026-10-29).
**Kind:** security.
**Source:** ROADMAP SLIP-0030 (user-request-2026-08-27).
**Blocker for:** SLIP-0031 (the updater verifies these signatures;
[`SLIP-0031-auto-update.md`](SLIP-0031-auto-update.md)).
**Pairs with:** SLIP-0031.

Each download on a release page gets a tamper-proof seal, so the app can
later tell a real Slipcase release from a fake one; nothing changes for
someone downloading by hand.

## 1. Goal

Every packaged download a release carries has a signature file beside it.
The signature is made in the GitHub Actions job that built the file, with a
private key held only in a GitHub Actions secret. The matching public key is
committed in the app. No private key material is ever tracked in the
repository, and a test proves it.

## 2. Problem

1. **A checksum proves no origin.** Each job in
   `.github/workflows/release.yml` uploads its file and a `.sha256` beside
   it. Both sit on the same host. Anyone able to replace one can replace the
   other, so the pair detects a damaged download but not a forged one.
2. **The updater has nothing to check.** SLIP-0031 installs a download only
   if it can prove the maintainer made it. Without a signature it can only
   trust the host.
3. **No Ed25519 implementation is installed.** `requirements.txt` and
   `requirements.lock` carry no cryptography library.

## 3. Scope decisions (agreed with the user)

- **Built now, with SLIP-0031.** User, 2026-10-29. This lifts the user's
  2026-09-30 deferral recorded on the roadmap item.
- **Key custody: a GitHub Actions secret.** User, 2026-10-29. The release
  workflow signs each file in the job that builds it and uploads
  `<asset>.sig` beside it.
- **The private key is never committed.** User, 2026-10-29. finbreak's
  test that scans the tree for private-key material is ported.
- **Two specs, not one.** Author, 2026-10-29. The request was one spec
  covering SLIP-0030 and SLIP-0031. `spec-format.md` § 2 allows one spec
  per roadmap id and withdrew the umbrella form. So this spec carries the
  signing contract and SLIP-0031's carries the updater; SLIP-0031 cites
  § 4 here for every format it reads.

Every other choice below is the author's and is open to review.

## 4. Design

### 4.1 Signature format

```
<asset>.sig    the raw 64-byte Ed25519 signature over the exact bytes of <asset>
```

No header, no encoding, no hash step. finbreak uses the same form
(`scripts/sign-release.py::sign_artifact` in finbreak).

| Asset (built by)                                  | Signature                            |
|---------------------------------------------------|--------------------------------------|
| `Slipcase-x86_64.AppImage` (`linux` job)          | `Slipcase-x86_64.AppImage.sig`       |
| `Slipcase-windows-x64.exe` (`windows` job)        | `Slipcase-windows-x64.exe.sig`       |
| `Slipcase-macos-<arch>.dmg` (`macos` job, each arch) | `Slipcase-macos-<arch>.dmg.sig`   |

The `.sha256` files are not signed. They stay for people checking a
download by hand.

The disk images are signed although SLIP-0031 never downloads one. The
user's decision covers every file a job builds, and a signature costs one
step.

### 4.2 The key and where it lives

- **Private key:** the 32-byte Ed25519 private seed, base64-encoded, on one
  line. It lives in the repository secret `SLIPCASE_SIGNING_KEY`. One line
  is chosen so a log that echoed it would be masked whole; whether GitHub
  masks a multi-line secret line by line is unverified.
- **Public key:** `core/update_key.py`, new:

```python
RELEASE_PUBLIC_KEY_B64 = "<base64 of the 32 raw public-key bytes>"

def public_key() -> Ed25519PublicKey:
    """The committed release public key."""
```

It lives in `core/` because both the signing script (§ 4.4) and the
updater (SLIP-0031) import it.

### 4.3 Making the key — once, by the user

`scripts/gen-signing-key.py`, new, ported from finbreak's script of the
same name:

1. Refuses if `release/slipcase-signing.key` exists.
2. Generates a keypair. Writes the base64 seed line to
   `release/slipcase-signing.key`, created with mode `0o600` and
   `O_EXCL`.
3. Prints the `RELEASE_PUBLIC_KEY_B64` line to paste into
   `core/update_key.py`. Never prints the private key.

`.gitignore` gains `release/`.

**The user runs it, by hand, in their own terminal.** No agent session
runs it, reads the key file, or sees the secret. The user then loads the
secret with `gh secret set SLIPCASE_SIGNING_KEY < release/slipcase-signing.key`,
keeps a copy off this machine (§ 14 Q1), and deletes the file.

**Landing order.** The real public key exists only once the user has run
this script. So the change lands in two commits. The first carries this
script, § 4.6's `requirements.txt`, `requirements.lock` and `STANDARDS.md`
changes, and the `.gitignore` line. The user then runs the script. The
second carries `core/update_key.py` with the real key, the `_smoke` check,
and the rest of this spec.
`public_key()` has no path for a missing key.

### 4.4 Signing — `scripts/sign-release.py`

New. Usage: `sign-release.py <file>`.

1. Read the seed from the environment variable `SLIPCASE_SIGNING_KEY`,
   with surrounding whitespace stripped. Missing, not base64, or not 32
   bytes → exit 1 with a message that never contains the value.
2. Sign the file's bytes. Write `<file>.sig`.
3. **Verify the new signature with `core.update_key.public_key()`.** A
   failure deletes `<file>.sig` and exits 1. This catches a secret that
   does not match the committed public key before anything is uploaded.

It never writes the key to disk and never logs it.

### 4.5 The workflow

Each of the `linux`, `windows` and `macos` jobs in
`.github/workflows/release.yml` gains one step, between **Build and
self-check** and the artifact upload:

```yaml
      - name: Sign the download
        env:
          SLIPCASE_SIGNING_KEY: ${{ secrets.SLIPCASE_SIGNING_KEY }}
        run: build/venv/bin/python scripts/sign-release.py dist/<asset>
```

The Windows step runs `build\venv\Scripts\python.exe` under `pwsh`. The
build venv is used because the build scripts already install
`requirements.lock` into it, and that now includes `cryptography`.

- **The secret reaches this step only.** The build step's environment
  never holds it. Code the build step ran can still change the runner, the
  venv included, before this step runs. Signing in the job that builds the
  file accepts that (§ 3).
- **Both uploads gain the `.sig`:** the `upload-artifact` paths and the
  `gh release upload` file list.
- **No secret, no release.** An empty `SLIPCASE_SIGNING_KEY` fails the step,
  so the job stops before uploading. This holds for a hand-started run too.

### 4.6 The dependency

- `requirements.txt` gains `cryptography`, with a minimum version; which
  minimum is unverified (§ 14 Q2).
- `requirements.lock` is regenerated per its own header. The new pins are
  whatever that regeneration installs, transitive ones included.
  Built (2026-10-29): the minimum is `cryptography>=48`. The lock pins
  50.0.2, and 48.0.1 on Intel Macs only. From 49 on there is no Intel Mac
  wheel; the source build there loaded the wrong OpenSSL and failed
  `--smoke` on `macos-15-intel`. The lock's header records why.
- `STANDARDS.md` § 14 gains a row.
- **The packaged build must carry it.** `main.py::_smoke` gains one check:
  `core.update_key.public_key()` loads. A bundle missing the library's
  native part then fails its self-check, and the release job stops.

## 5. Invariants

- **INV-1** — `sign-release.py` writes a 64-byte `<file>.sig` that verifies
  against the key it was given, and a one-byte change to the file or the
  signature makes verification fail.
  *Test:* `tests/test_release_signing.py::TestSign::test_round_trip_and_tamper`,
  with a throwaway key monkeypatched over `RELEASE_PUBLIC_KEY_B64`.
  *Breaks when:* the script signs a hash, a prefix or a re-encoded copy of
  the file, or writes the signature base64-encoded.

- **INV-2** — `sign-release.py` exits non-zero and leaves no `<file>.sig`
  when the key is missing, malformed, or does not match
  `RELEASE_PUBLIC_KEY_B64`, and its output never contains the key.
  *Test:* `tests/test_release_signing.py::TestSign::test_refuses_bad_key`
  — three cases: unset, `not-base64!`, and a valid key that is not the
  committed one.
  *Breaks when:* the self-verify of § 4.4 step 3 is dropped (the third case
  then writes a `.sig`), or an error message formats the variable's value.

- **INV-3** — No private key material is tracked: no `git ls-files` path
  ends in `.key` or lies under `release/`, and no tracked file contains a
  PEM `PRIVATE KEY` block.
  *Test:* `tests/test_release_signing.py::TestKeyCustody::test_no_private_key_tracked`,
  ported from finbreak's
  `test_INV14_no_private_key_material_is_tracked`, with the PEM marker
  assembled at run time so the test file does not trip itself.
  *Breaks when:* `release/slipcase-signing.key` or any `*.key` file is
  committed. A raw base64 seed pasted into some other tracked file is not
  caught; § 10 says so.

- **INV-4** — In `release.yml`, `secrets.SLIPCASE_SIGNING_KEY` appears only
  inside steps named `Sign the download`, and each of the three jobs has
  exactly one such step.
  *Test:* `tests/test_release_signing.py::TestWorkflow::test_secret_only_in_sign_steps`
  — splits the file into steps at each `- name:` or `- uses:` line and
  checks which steps mention the secret.
  *Breaks when:* the secret is moved into a job-level `env:` or the build
  step's `env:`.

- **INV-5** — Each job's artifact upload and release upload both name the
  `.sig` of the file the job built.
  *Test:* `tests/test_release_signing.py::TestWorkflow::test_sig_uploaded`
  — for each asset in § 4.1's table, its `.sig` appears in that job's
  `upload-artifact` `path:` block and in its `gh release upload` command.
  *Breaks when:* a job signs but uploads only the asset and `.sha256`.

- **INV-6** — `RELEASE_PUBLIC_KEY_B64` decodes to a valid 32-byte Ed25519
  public key, and `--smoke` does not report OK when it cannot be loaded.
  *Test:* `tests/test_release_signing.py::TestKeyCustody::test_public_key_loads`;
  and `tests/test_smoke.py` gains a case that runs `--smoke` with
  `core.update_key` made to raise on import. It expects a non-zero exit and
  no `slipcase smoke OK` line. The build scripts check for that line, so
  this holds whether the import fails at start-up or inside `_smoke`.
  *Breaks when:* the constant is truncated or not base64, or `_smoke`
  skips the key check. A well-formed 32-byte placeholder passes, since
  `Ed25519PublicKey.from_public_bytes` accepts any 32 bytes (`cryptography`
  50.0.1, 2026-10-29). § 4.4 step 3 then stops every release job.

- **INV-7** — `gen-signing-key.py` refuses to overwrite an existing key
  file, creates it with mode `0o600`, and its key signs a file that
  `sign-release.py`'s verification accepts once its printed public key is
  monkeypatched in.
  *Test:* `tests/test_release_signing.py::TestKeygen` (the mode check is
  skipped on Windows, which has no such bits).
  *Breaks when:* the script opens without `O_EXCL`, or writes a key format
  `sign-release.py` cannot read.

## 6. Failure modes

- **Secret missing or empty.** The sign step fails; that job uploads
  nothing. The release then lacks that platform's file. SLIP-0031 offers no
  update without a `.sig`, so no user is harmed.
- **Secret does not match the committed public key.** `sign-release.py`'s
  self-verify fails the job (INV-2).
- **Private key lost.** No new release can be signed with it. Installed
  copies trust only the committed public key, so a new key means every
  installed copy must be replaced by hand once. § 14 Q1 is the backup.
- **Private key leaked.** Anyone holding it can sign a file every installed
  copy accepts. The response is a new key, a release, and a notice in
  `SECURITY.md`; a rotation procedure is out of scope (§ 9).
- **A rerun with `--clobber`.** `gh release upload` replaces each file in
  turn, so for a moment the new asset can sit beside the old `.sig`. An
  updater downloading in that window fails verification and installs
  nothing.
- **Pull requests.** `release.yml` runs on `release` and
  `workflow_dispatch` only, so code from a fork never runs with the secret.

## 7. Tests

All in a new `tests/test_release_signing.py`, as `unittest.TestCase`
classes (`STANDARDS.md` § 9). They run offline, generate a throwaway key per
test, and never read the real secret. Each must be seen failing against the
unchanged tree before the change lands: `sign-release.py` and
`core/update_key.py` do not exist yet, so every case fails on import first. The breaking case
each one names under *Breaks when* is the second run.

| Test | Locks |
|------|-------|
| `TestSign::test_round_trip_and_tamper` | INV-1 |
| `TestSign::test_refuses_bad_key` | INV-2 |
| `TestKeyCustody::test_no_private_key_tracked` | INV-3 |
| `TestWorkflow::test_secret_only_in_sign_steps` | INV-4 |
| `TestWorkflow::test_sig_uploaded` | INV-5 |
| `TestKeyCustody::test_public_key_loads`, `tests/test_smoke.py` new case | INV-6 |
| `TestKeygen` | INV-7 |

INV-4 and INV-5 read the workflow as text. They prove what the file says,
not that GitHub runs it that way. The first real release is that check
(§ 7.1).

### 7.1 Manual check, once, on the first signed release

1. `gh release download <tag> --pattern '*.sig' --pattern 'Slipcase-*'`.
2. For each file, verify its `.sig` with `core.update_key.public_key()` in a
   Python shell.

Expected: every one verifies.

## 8. Alternatives considered (and rejected)

- **Sign on the maintainer's machine, as finbreak does.** Rejected by the
  user's 2026-10-29 decision. It also means downloading each built file,
  signing and re-uploading by hand for every release.
- **A signed `SHA256SUMS` for the whole release** (finbreak FIBR-0169).
  Each file is built in its own job, so no job holds every file. It needs a
  further job after all builds. SLIP-0031 § 15 Q1 asks whether it is wanted.
- **Sigstore / GitHub artifact attestations.** No new secret, but the app
  would have to verify a Sigstore bundle and its certificate chain. That is
  a far larger verifier than one Ed25519 check.
- **minisign or signify.** A new binary on three runner types, and the app
  still needs its own verifier.
- **GPG.** No verifier in the Python standard library, and a larger
  dependency than `cryptography`.

## 9. Out of scope

- A test that verifies a real, already-shipped signature against the
  committed key, catching a silent key change (finbreak FIBR-0301). It
  needs a signed release to exist first. Deferred; not yet queued.
- A key rotation procedure. Deferred; not yet queued.
- Windows Authenticode and Apple code signing. `scripts/build-macos.sh`
  records the user's 2026-09-02 decision not to sign the Mac app; nothing
  in this spec changes it.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_release_signing.py::TestSign::test_round_trip_and_tamper` |
| INV-2 | `tests/test_release_signing.py::TestSign::test_refuses_bad_key` |
| INV-3 | **Partial:** `tests/test_release_signing.py::TestKeyCustody::test_no_private_key_tracked` catches a `.key` file, anything under `release/` and a PEM block; a bare base64 seed in another file is not caught |
| INV-4 | `tests/test_release_signing.py::TestWorkflow::test_secret_only_in_sign_steps` |
| INV-5 | **Partial:** `tests/test_release_signing.py::TestWorkflow::test_sig_uploaded` reads the file; that GitHub uploads it is the manual check in § 7.1 |
| INV-6 | `tests/test_release_signing.py::TestKeyCustody::test_public_key_loads`, `tests/test_smoke.py` |
| INV-7 | `tests/test_release_signing.py::TestKeygen` |
| § 4.3 no agent sees the key | **nothing** — a working practice, not code |

## 11. Cross-doc impact

- `STANDARDS.md` § 14: a `cryptography` row. § 9's test table: a
  `test_release_signing.py` row.
- `SECURITY.md` § What is in scope: release signatures, and that a way to
  get an unsigned or wrongly signed file accepted is a finding.
- `CONTRIBUTING.md` § How a release gets its downloads: each file now gets a
  `.sig`, and a release fails without the secret.
- `README.md` § Getting it running: unchanged; the `.sig` is for the app.
- `.gitignore`: `release/`.
- `CHANGELOG.md`: an entry.

## 12. Cold-eyes loop log

Rows live in `../reviews/SLIP-0030-release-signing-loop-log.md`.

## 13. Resource cost

One new runtime dependency, `cryptography`, and whatever it pulls in. It
grows each packaged download by its compiled library; by how much is
unverified until a build runs. Signing reads each file into memory once,
on the runner.

## 14. Open questions

- **Q1 — Where does the offline copy of the private key live?** A GitHub
  secret cannot be read back. Losing it strands every installed copy (§ 6).
  Decided (2026-10-29, user): the user keeps the key file in their password
  manager before deleting it.
- **Q2 — The minimum `cryptography` version.** Recommended: the major
  version the lock regeneration installs, since that is what CI and the
  builds test.
