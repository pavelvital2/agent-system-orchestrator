#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

FORBIDDEN_ROOTS_REGEX='^(project-input|project-runtime|project-archive)(/|$)'
PYTHON_CACHE_REGEX='(^|/)__pycache__/|\.py[co]$'
ROOT_DUPLICATE_PACKAGE_REGEX='^(00_start|01_roles|02_runtime|03_templates|04_state|05_gap_flow|06_logs|07_lifecycle|08_profiles|09_validators|10_examples|11_release|scripts|tools|tests)(/|$)|^(GOVERNANCE_CHANGELOG|PACKAGE_VERSIONING)\.md$'

fail_with_paths() {
  local reason="$1"
  local paths="$2"

  if [[ -n "$paths" ]]; then
    printf 'FAIL: %s\n%s\n' "$reason" "$paths" >&2
    exit 1
  fi
}

matching_paths() {
  local pattern="$1"
  grep -E "$pattern" || true
}

cd "$REPO_ROOT"

tracked_paths="$(git ls-files)"
staged_paths="$(git diff --cached --name-only)"

fail_with_paths \
  "tracked forbidden roots are not publishable" \
  "$(printf '%s\n' "$tracked_paths" | matching_paths "$FORBIDDEN_ROOTS_REGEX")"
fail_with_paths \
  "staged forbidden roots are not publishable" \
  "$(printf '%s\n' "$staged_paths" | matching_paths "$FORBIDDEN_ROOTS_REGEX")"

fail_with_paths \
  "tracked Python cache artifacts are not publishable" \
  "$(printf '%s\n' "$tracked_paths" | matching_paths "$PYTHON_CACHE_REGEX")"
fail_with_paths \
  "staged Python cache artifacts are not publishable" \
  "$(printf '%s\n' "$staged_paths" | matching_paths "$PYTHON_CACHE_REGEX")"

fail_with_paths \
  "root duplicate package layout paths must stay under agent-system/" \
  "$(printf '%s\n' "$tracked_paths" | matching_paths "$ROOT_DUPLICATE_PACKAGE_REGEX")"
fail_with_paths \
  "staged root duplicate package layout paths must stay under agent-system/" \
  "$(printf '%s\n' "$staged_paths" | matching_paths "$ROOT_DUPLICATE_PACKAGE_REGEX")"

archive_paths="$(git archive --format=tar HEAD | tar -tf -)"
fail_with_paths \
  "git archive HEAD contains forbidden roots" \
  "$(printf '%s\n' "$archive_paths" | matching_paths "$FORBIDDEN_ROOTS_REGEX")"
fail_with_paths \
  "git archive HEAD contains Python cache artifacts" \
  "$(printf '%s\n' "$archive_paths" | matching_paths "$PYTHON_CACHE_REGEX")"
fail_with_paths \
  "git archive HEAD contains root duplicate package layout paths" \
  "$(printf '%s\n' "$archive_paths" | matching_paths "$ROOT_DUPLICATE_PACKAGE_REGEX")"

printf 'SOURCE_HYGIENE_RESULT: passed\n'
