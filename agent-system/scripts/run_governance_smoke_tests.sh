#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PREFLIGHT="${REPO_ROOT}/agent-system/scripts/checkpoint_preflight.sh"
VALIDATOR="${REPO_ROOT}/agent-system/scripts/validate_task_packet.py"
COVERAGE_MATRIX="${REPO_ROOT}/project-input/PATCH_ASO_25_GOVERNANCE_HARDENING_V2_0_0/COVERAGE_MATRIX.md"
RUNTIME_SCHEMA="${REPO_ROOT}/agent-system/04_state/RUNTIME_STATE_SCHEMA.md"
SCOPE_MATRIX="${REPO_ROOT}/agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md"
SECRET_RULES="${REPO_ROOT}/agent-system/09_validators/SECRET_SCAN_RULES.md"
RECEIPT_TEMPLATE="${REPO_ROOT}/agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md"
CHANGELOG="${REPO_ROOT}/agent-system/GOVERNANCE_CHANGELOG.md"
PACKAGE_VERSIONING="${REPO_ROOT}/agent-system/PACKAGE_VERSIONING.md"
PACKAGE_README="${REPO_ROOT}/agent-system/README.md"
FIXTURES_ROOT="${REPO_ROOT}/tests/fixtures"
PYTHON_BIN="${PYTHON_BIN:-python3}"

TMP_ROOT=""
PASS_COUNT=0

cleanup() {
  if [[ -n "${TMP_ROOT}" && -d "${TMP_ROOT}" && "${ASO_SMOKE_KEEP_TMP:-0}" != "1" ]]; then
    rm -rf "${TMP_ROOT}"
  fi
}
trap cleanup EXIT

die() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

fixture_value() {
  local path="$1"
  sed -n '/^[[:space:]]*$/d; /^[[:space:]]*#/d; { p; q; }' "$path"
}

init_local_git_repo() {
  local repo_dir="$1"
  mkdir -p "$repo_dir"
  if ! git -C "$repo_dir" init -b main >/dev/null 2>&1; then
    git -C "$repo_dir" init >/dev/null 2>&1
    git -C "$repo_dir" checkout -b main >/dev/null 2>&1
  fi
  git -C "$repo_dir" config user.email "smoke@example.invalid"
  git -C "$repo_dir" config user.name "Governance Smoke"
}

write_preflight_task_packet() {
  local packet_path="$1"
  local task_id="$2"
  local allowed_pattern="$3"

  cat >"$packet_path" <<EOF
# TASK PACKET

## TASK_ID
\`\`\`text
${task_id}
\`\`\`

## TASK_STATUS
\`\`\`text
active
\`\`\`

## TASK_KIND
\`\`\`text
correction
\`\`\`

## TARGET_ROLE
\`\`\`text
developer
\`\`\`

## SCOPE_IN
\`\`\`text
- Deterministic governance smoke fixture for ${task_id}.
\`\`\`

## SCOPE_OUT
\`\`\`text
- No commit.
- No push.
- No real secrets.
\`\`\`

## REQUIRED_DOCS
\`\`\`text
- agent-system/scripts/checkpoint_preflight.sh
\`\`\`

## ALLOWED_FILE_CHANGES
\`\`\`text
- ${allowed_pattern}
\`\`\`

## FORBIDDEN_FILE_CHANGES
\`\`\`text
- NONE
\`\`\`

## AUDIT_REQUIREMENTS
\`\`\`text
mandatory
\`\`\`

## NOTES
\`\`\`text
Owner-authorized package governance smoke fixture generated in a temporary local repository.
\`\`\`
EOF
}

expect_blocked_output() {
  local name="$1"
  local expected="$2"
  local status="$3"
  local output="$4"

  if [[ "$status" -eq 0 ]]; then
    printf '%s\n' "$output" >&2
    die "${name} unexpectedly passed"
  fi
  if ! grep -Fq "$expected" <<<"$output"; then
    printf '%s\n' "$output" >&2
    die "${name} did not report expected blocker: ${expected}"
  fi

  printf 'PASS: %s blocked by %s\n' "$name" "$expected"
  PASS_COUNT=$((PASS_COUNT + 1))
}

run_preflight_fixture() {
  local name="$1"
  local push_requested="$2"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local changed_path allowed_pattern expected_blocker repo_dir task_packet payload_dir output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  changed_path="$(fixture_value "${fixture_dir}/changed_path.txt")"
  allowed_pattern="$(fixture_value "${fixture_dir}/allowed_pattern.txt")"
  expected_blocker="$(fixture_value "${fixture_dir}/expected_blocker.txt")"

  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"

  payload_dir="$(dirname "${repo_dir}/${changed_path}")"
  [[ "$payload_dir" == "$repo_dir/." ]] || mkdir -p "$payload_dir"
  printf 'placeholder fixture payload for %s; no real secrets\n' "$name" >"${repo_dir}/${changed_path}"

  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "$allowed_pattern"

  set +e
  output="$(
    cd "$repo_dir" &&
      bash "$PREFLIGHT" \
        --dry-run \
        --task-packet "$task_packet" \
        --project-state "$project_state" \
        --runtime-schema "$RUNTIME_SCHEMA" \
        --scope-matrix "$SCOPE_MATRIX" \
        --secret-rules "$SECRET_RULES" \
        --receipt-template "$RECEIPT_TEMPLATE" \
        --include-untracked \
        --push-requested "$push_requested" 2>&1
  )"
  status=$?
  set -e

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

run_invalid_task_packet_fixture() {
  local name="invalid_task_packet"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local invalid_packet="${fixture_dir}/TASK_INVALID_MISSING_REQUIRED.md"
  local expected_blocker output status

  [[ -f "$invalid_packet" ]] || die "${name} fixture missing TASK_INVALID_MISSING_REQUIRED.md"
  expected_blocker="$(fixture_value "${fixture_dir}/expected_blocker.txt")"

  set +e
  output="$("$PYTHON_BIN" "$VALIDATOR" --mode dispatch "$invalid_packet" 2>&1)"
  status=$?
  set -e

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

assert_coverage_matrix() {
  local fix_rows

  [[ -f "$COVERAGE_MATRIX" ]] || die "coverage matrix missing"
  fix_rows="$(awk '/^\|[[:space:]]*[0-9]+[[:space:]]*\|/ { count++ } END { print count + 0 }' "$COVERAGE_MATRIX")"
  [[ "$fix_rows" == "25" ]] || die "coverage matrix row count is ${fix_rows}, expected 25"
  grep -Fq "TOTAL_FIXES: 25" "$COVERAGE_MATRIX" || die "coverage matrix missing TOTAL_FIXES: 25"
  grep -Fq "REQUIRED_COVERAGE: 25/25" "$COVERAGE_MATRIX" || die "coverage matrix missing REQUIRED_COVERAGE: 25/25"

  printf 'PASS: coverage_matrix asserts 25/25 fixes (%s fix rows)\n' "$fix_rows"
  PASS_COUNT=$((PASS_COUNT + 1))
}

assert_version_changelog_coherence() {
  grep -Fq "CURRENT_PACKAGE_VERSION: 2.0.0" "$PACKAGE_VERSIONING" || die "PACKAGE_VERSIONING missing package 2.0.0"
  grep -Fq "CURRENT_GOVERNANCE_RULESET_VERSION: 2.0.0" "$PACKAGE_VERSIONING" || die "PACKAGE_VERSIONING missing governance 2.0.0"
  grep -Fq "CURRENT_RUNTIME_SCHEMA_VERSION: 2.0.0" "$PACKAGE_VERSIONING" || die "PACKAGE_VERSIONING missing runtime schema 2.0.0"
  grep -Fq "CURRENT_PACKAGE_VERSION: 2.0.0" "$PACKAGE_README" || die "README missing package 2.0.0"
  grep -Fq "TASK_ASO_PATCH_008_GOVERNANCE_SMOKE_TESTS" "$CHANGELOG" || die "changelog missing TASK_ASO_PATCH_008_GOVERNANCE_SMOKE_TESTS"
  grep -Fq "PACKAGE_VERSION_AFTER: 2.0.0" "$CHANGELOG" || die "changelog missing PACKAGE_VERSION_AFTER: 2.0.0"

  printf 'PASS: version_changelog coherent for 2.0.0 smoke coverage\n'
  PASS_COUNT=$((PASS_COUNT + 1))
}

main() {
  [[ -f "$PREFLIGHT" ]] || die "checkpoint_preflight.sh missing"
  [[ -f "$VALIDATOR" ]] || die "validate_task_packet.py missing"

  TMP_ROOT="$(mktemp -d)"

  printf 'Governance smoke tests: local dry-run fixtures only; no commit, no push, no real secrets.\n'
  run_preflight_fixture "wrong_remote" "yes"
  run_preflight_fixture "wrong_branch" "yes"
  run_preflight_fixture "package_repo_with_project_docs" "no"
  run_invalid_task_packet_fixture
  run_preflight_fixture "push_not_allowed" "yes"
  run_preflight_fixture "secret_file_present" "no"
  assert_coverage_matrix
  assert_version_changelog_coherence
  printf 'SMOKE_RESULT: passed (%s assertions)\n' "$PASS_COUNT"
}

main "$@"
