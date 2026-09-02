#!/usr/bin/env bash
# The project's gate: the one list of checks that must pass.
#
# .github/workflows/ci.yml runs this same script, so what passes locally and
# what passes on GitHub cannot drift apart. The machine-wide pre-push hook
# discovers this path by name and runs it before every push.
#
# Usage: ./scripts/local-ci.sh
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

status=0

step() {
    printf '\n=== %s ===\n' "$1"
    shift
    "$@" || status=1
}

step "ruff" ruff check .
step "pytest" python3 -m pytest tests/ -q

if [[ $status -eq 0 ]]; then
    printf '\ngate: PASS\n'
else
    printf '\ngate: FAIL\n'
fi
exit "$status"
