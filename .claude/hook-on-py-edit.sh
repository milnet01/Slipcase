#!/usr/bin/env bash
#
# hook-on-py-edit.sh — PostToolUse hook for Slipcase.
#
# When Claude edits a Python file under core/, ui/, or api/, run
# `python3 -m py_compile` on it. This catches syntax errors in the
# same turn as the edit, before the model decides everything is fine
# and moves on. Cheap (<100 ms per file). For full test runs, the user
# invokes pytest manually or the bump skill's post_check runs the suite.
#
# Wired in via .claude/settings.json:
#     PostToolUse → matcher Edit|Write → command bash <this script>
#
# Stdin: PostToolUse JSON.
# Stdout: nothing on pass / non-Python / out-of-scope, or
#         {systemMessage:"…"} containing the py_compile error.
# Exit: always 0.

set -u

# Derive the project root from this script's own location, so the hook works
# from any checkout. CLAUDE_PROJECT_DIR wins when the harness supplies it.
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

file=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)
case "$file" in
    "$PROJECT_ROOT"/core/*.py|*/core/*.py) ;;
    "$PROJECT_ROOT"/ui/*.py|*/ui/*.py) ;;
    "$PROJECT_ROOT"/api/*.py|*/api/*.py) ;;
    *) exit 0 ;;
esac

# Run py_compile and capture stderr. Success = silent. Failure = surface.
err=$(cd "$PROJECT_ROOT" && python3 -m py_compile "$file" 2>&1 >/dev/null)
if [ -n "$err" ]; then
    jq -n --arg e "$err" --arg f "$file" \
        '{systemMessage: ("⚠ py_compile failed for " + $f + ":\n" + $e)}'
fi
exit 0
