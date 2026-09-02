# Contributing to Slipcase

Thanks for looking. This is a small project with one maintainer, so the
process is light. Everything below is written to be *run*, not just read.

## Getting set up

You need **Python 3.12** and a Linux desktop. A virtual environment keeps
Slipcase's libraries out of your system Python:

```bash
git clone https://github.com/milnet01/Slipcase.git
cd Slipcase
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock -r requirements-dev.txt
python3 main.py
```

The app opens a window. If it does not, that is a bug worth reporting.

Two dependency files, on purpose:

- `requirements.txt` — what Slipcase depends on and the minimum it needs.
  Install from this when you want to find out whether a newer library still
  works.
- `requirements.lock` — the exact versions, transitive ones included. CI and
  the packaged builds install from this, so two builds of one release bundle
  the same libraries. `requirements-dev.txt` pins the two tools the checks
  need.

## Before you commit

Run the gate. It is the same script CI runs, so if it passes locally it
passes there:

```bash
./scripts/local-ci.sh
```

That runs `ruff` and the test suite. Everything must be green — `STANDARDS.md`
makes a passing suite the condition for any commit.

Some tests are skipped by default because they contact real services. To
include them:

```bash
SLIPCASE_LIVE_API=1 python3 -m pytest tests/ -v
```

If you are on this machine's setup, a `pre-push` hook runs the gate for you
and refuses a push that fails it.

## What a change should look like

- **One reason per change.** Every line you touch should trace to the thing
  you set out to do. Tidying unrelated code in the same commit makes both
  harder to review and to revert.
- **A fix comes with a test that fails without it.** Write the test first and
  watch it fail, so you know it is testing the fix rather than agreeing with
  the bug.
- **Follow the surrounding code.** `ruff.toml` and `.editorconfig` hold the
  mechanical rules; `STANDARDS.md` section 3 holds the rest.
- **Do not break the invariants.** `CLAUDE.md` lists the security, performance
  and memory rules the code must keep. They are not suggestions — several
  exist because the alternative was measured and was worse.

## Commit messages

Subject line: the roadmap ID, a colon, then what changed.

```
SLIP-0089: try the region-tagged filename libretro actually stores
```

Work with no roadmap item uses a `docs:` or `chore:` prefix instead. The body
is for *why*, in whatever length that takes — the subject already says what.

Nothing enforces this shape automatically; it is a convention, and matching it
keeps the history readable.

## Opening a pull request

Branch, commit, push, open a PR against `main`. CI runs on the PR. Say what
the change is for and how you checked it — "the gate is green" is a fine
answer when the tests cover it, and a description of what you did by hand is
the right answer when they do not.

## Reporting things

- **A bug or an idea:** open an issue.
- **A security problem:** do not open an issue. `SECURITY.md` has the private
  route.

## Files worth knowing about

- `README.md` — what the app is and how to use it.
- `STANDARDS.md` — the rulebook: the rendering pipeline, and the security,
  speed and memory rules a change must not break.
- `CLAUDE.md` — a short orientation, including two sets of deliberate
  exceptions that look like mistakes and are not.
- `docs/subsystems.md` — how the code is divided up.
- `ROADMAP.md` — generated from a shared database. Edit it through the roadmap
  tooling, never by hand; a hand edit is overwritten by the next write.
