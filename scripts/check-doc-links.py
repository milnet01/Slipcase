#!/usr/bin/env python3
"""Check that every relative link in the project's Markdown files resolves.

The one check in the gate that reads documentation, and so the whole of its
documentation mode (scripts/local-ci.sh --docs). A link to a file that was
moved or renamed is the defect it finds. Links to web addresses are not
fetched: a gate must not fail because someone else's site is down.

Usage: python3 scripts/check-doc-links.py
Exits 0 when every link resolves, 1 otherwise, naming each broken one.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    """The tracked Markdown files, or every one under the root without git."""
    try:
        listed = subprocess.run(  # noqa: S603 -- fixed arguments
            ["git", "ls-files", "*.md"],  # noqa: S607 -- git from PATH
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split("\n")
        return [ROOT / name for name in listed if name]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]


def broken_links(path: Path) -> list[tuple[int, str]]:
    found = []
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
        if fenced:
            continue
        for target in LINK.findall(line):
            if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue        # a web address, a mail link, or an anchor on this page
            if not (path.parent / target.split("#", 1)[0]).exists():
                found.append((number, target))
    return found


def main() -> int:
    files = markdown_files()
    if not files:
        print("doc links: found no Markdown files; the search has gone stale")
        return 1
    bad = 0
    for path in files:
        for number, target in broken_links(path):
            print(f"{path.relative_to(ROOT)}:{number}: link target does not exist: {target}")
            bad += 1
    print(f"doc links: {len(files)} files checked, {bad} broken")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
