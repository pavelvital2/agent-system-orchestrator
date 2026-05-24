#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

FORBIDDEN_ROOTS_REGEX='^(project-input|project-runtime|project-archive)(/|$)'
PYTHON_CACHE_REGEX='(^|/)__pycache__/|\.py[co]$'
PYTHON_BUILD_ARTIFACT_REGEX='(^|/)(__pycache__|build|dist|\.eggs)(/|$)|(^|/)[^/]+\.(egg-info|dist-info)(/|$)|\.py[co]$'
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

untracked_paths_from_status() {
  local entry

  while IFS= read -r -d '' entry; do
    if [[ "$entry" == '?? '* ]]; then
      printf '%s\n' "${entry:3}"
    fi
  done < <(git status --porcelain=v1 -z --untracked-files=all)
}

filesystem_python_build_artifacts() {
  find . \
    \( -path './.git' -o -path './.venv' -o -path './project-input' -o -path './project-runtime' -o -path './project-archive' -o -path './tmp' -o -path './.tmp' \) -prune \
    -o \( \
      -type d \( -name '__pycache__' -o -name 'build' -o -name 'dist' -o -name '.eggs' -o -name '*.egg-info' -o -name '*.dist-info' \) \
      -o -type f \( -name '*.pyc' -o -name '*.pyo' \) \
    \) -print | sed 's#^\./##'
}

cd "$REPO_ROOT"

tracked_paths="$(git ls-files)"
staged_paths="$(git diff --cached --name-only)"
untracked_paths="$(untracked_paths_from_status)"
filesystem_artifact_paths="$(filesystem_python_build_artifacts)"

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
  "untracked Python build artifacts contaminate source checkout" \
  "$(printf '%s\n' "$untracked_paths" | matching_paths "$PYTHON_BUILD_ARTIFACT_REGEX")"
fail_with_paths \
  "filesystem Python build artifacts contaminate source checkout" \
  "$filesystem_artifact_paths"

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
