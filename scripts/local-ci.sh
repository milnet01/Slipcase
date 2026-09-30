#!/usr/bin/env bash
# The project's gate: the one list of checks that must pass.
#
# .github/workflows/ci.yml runs this same script, so what passes locally and
# what passes on GitHub cannot drift apart. The machine-wide pre-push hook
# discovers this path by name and runs it before every push.
#
# Usage: ./scripts/local-ci.sh [--docs]
#
# --docs is for a push that changes documentation only (the hook decides
# that, from the repository's ants.gate.docsGlob). It runs the checks a
# document can reach and no others. Today that is one: the link check. ruff
# reads no Markdown and no test opens a document -- both probed when this
# mode was added (SLIP-0096). A check that starts reading documents belongs
# in both lists below.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

mode=full
case "${1-}" in
    "") ;;
    --docs) mode=docs ;;
    *) printf 'usage: %s [--docs]\n' "$0" >&2; exit 2 ;;
esac

status=0

step() {
    printf '\n=== %s ===\n' "$1"
    shift
    "$@" || status=1
}

if [[ $mode == full ]]; then
    step "ruff" ruff check .
    step "pytest" python3 -m pytest tests/ -q
fi
step "doc links" python3 scripts/check-doc-links.py

label=gate
[[ $mode == docs ]] && label='gate (documentation mode: lint and tests not run)'
if [[ $status -eq 0 ]]; then
    printf '\n%s: PASS\n' "$label"
else
    printf '\n%s: FAIL\n' "$label"
fi
exit "$status"
