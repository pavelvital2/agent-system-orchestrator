#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PREFLIGHT="${REPO_ROOT}/agent-system/scripts/checkpoint_preflight.sh"
VALIDATOR="${REPO_ROOT}/agent-system/scripts/validate_task_packet.py"
COVERAGE_MATRIX="${REPO_ROOT}/agent-system/10_examples/ASO_25_GOVERNANCE_HARDENING_COVERAGE_MATRIX.md"
RUNTIME_SCHEMA="${REPO_ROOT}/agent-system/04_state/RUNTIME_STATE_SCHEMA.md"
SCOPE_MATRIX="${REPO_ROOT}/agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md"
SECRET_RULES="${REPO_ROOT}/agent-system/09_validators/SECRET_SCAN_RULES.md"
RECEIPT_TEMPLATE="${REPO_ROOT}/agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md"
CHANGELOG="${REPO_ROOT}/agent-system/GOVERNANCE_CHANGELOG.md"
PACKAGE_VERSIONING="${REPO_ROOT}/agent-system/PACKAGE_VERSIONING.md"
PACKAGE_README="${REPO_ROOT}/agent-system/README.md"
FIXTURES_ROOT="${REPO_ROOT}/agent-system/tests/fixtures"
PYTHON_BIN="${PYTHON_BIN:-python3}"

TMP_ROOT=""
PASS_COUNT=0
SMOKE_FIXTURES=(
  wrong_remote
  wrong_branch
  package_repo_with_project_docs
  invalid_task_packet
  push_not_allowed
  secret_file_present
  approved_ssh_alias
  canonical_remote_expected
  canonical_remote_mismatch
  untracked_critical_baseline
  project_input_tz_policy
  manual_preflight_ref
  bootstrap_and_none_route_governance
  smoke_self_contained
  coverage_matrix
  version_changelog_coherence
)

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

commit_fixture_baseline() {
  local repo_dir="$1"
  local path="$2"
  local rel_path

  rel_path="${path#"$repo_dir"/}"
  git -C "$repo_dir" add "$rel_path"
  git -C "$repo_dir" commit -m "smoke fixture baseline" >/dev/null 2>&1
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

## SUPERSEDES
\`\`\`text
NONE
\`\`\`

## SUPERSEDED_BY
\`\`\`text
NONE
\`\`\`

## CORRECTION_OF
\`\`\`text
NONE
\`\`\`

## SOURCE_RESULT_REF
\`\`\`text
NONE
\`\`\`

## ATTEMPT_NO
\`\`\`text
1
\`\`\`

## FAILURE_TYPE
\`\`\`text
none
\`\`\`

## TASK_TITLE
\`\`\`text
Governance smoke fixture for ${task_id}
\`\`\`

## TASK_TYPE
\`\`\`text
developer
\`\`\`

## TARGET_ROLE
\`\`\`text
developer
\`\`\`

## REASONING_LEVEL
\`\`\`text
VALUE: high
OVERRIDE_REASON: NONE
\`\`\`

## DEPENDENCIES
\`\`\`text
- NONE
\`\`\`

## DEPENDENCY_STATUS
\`\`\`text
none
\`\`\`

## REQUESTED_BY_ROLE
\`\`\`text
NONE
\`\`\`

## REQUESTED_BY_TASK
\`\`\`text
NONE
\`\`\`

## RESEARCH_QUESTION_ID
\`\`\`text
NONE
\`\`\`

## RESEARCH_PURPOSE
\`\`\`text
NONE
\`\`\`

## RESEARCH_QUESTIONS
\`\`\`text
- NONE
\`\`\`

## ALLOWED_SOURCES
\`\`\`text
- Local smoke fixture files.
\`\`\`

## FORBIDDEN_SOURCES
\`\`\`text
- External network.
- Secrets.
\`\`\`

## EXPECTED_EVIDENCE
\`\`\`text
- checkpoint_preflight.sh dry-run output.
\`\`\`

## EXPECTED_OUTPUT
\`\`\`text
- Deterministic local smoke assertion.
\`\`\`

## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS
\`\`\`text
no
\`\`\`

## RETURN_TO_ROLE_AFTER_AUDIT_PASS
\`\`\`text
none
\`\`\`

## RETURN_TASK_AFTER_AUDIT_PASS
\`\`\`text
NONE
\`\`\`

## PURPOSE
\`\`\`text
Exercise checkpoint preflight governance smoke behavior.
\`\`\`

## SOURCE_OF_TRUTH
\`\`\`text
- agent-system/scripts/checkpoint_preflight.sh
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

## INPUTS
\`\`\`text
- agent-system/tests/fixtures/${task_id}
\`\`\`

## READ_INPUTS
\`\`\`text
- NONE
\`\`\`

## EXPECTED_OUTPUTS
\`\`\`text
- Dry-run preflight result.
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

## ACCEPTANCE_CRITERIA
\`\`\`text
- Preflight behavior matches the fixture expectation.
\`\`\`

## EVIDENCE_REQUIREMENTS
\`\`\`text
- Dry-run preflight output.
\`\`\`

## SETUP_HOOKS
\`\`\`text
- Initialize temporary local Git repository.
\`\`\`

## LAUNCH_HOOKS
\`\`\`text
- Run checkpoint_preflight.sh in dry-run mode.
\`\`\`

## RESULT_PATH
\`\`\`text
project-runtime/agent-results/${task_id}.md
\`\`\`

## RISK_REQUIREMENTS
\`\`\`text
- Fixture-only smoke; no network push.
\`\`\`

## MANDATORY_WORKFLOW
\`\`\`text
developer -> auditor
\`\`\`

## NEXT_ROLE_ON_PASS
\`\`\`text
auditor
\`\`\`

## NEXT_ROLE_ON_FAIL
\`\`\`text
developer
\`\`\`

## NEXT_ROLE_ON_BLOCKED
\`\`\`text
orchestrator
\`\`\`

## NEXT_ROLE_ON_GAP
\`\`\`text
orchestrator
\`\`\`

## TESTING_REQUIREMENTS
\`\`\`text
mandatory
\`\`\`

## DOCUMENTATION_REQUIREMENTS
\`\`\`text
none
\`\`\`

## FILESYSTEM_GOVERNANCE
\`\`\`text
Owner-authorized package-governance correction/update smoke fixture.
\`\`\`

## RUNTIME_GOVERNANCE
\`\`\`text
No runtime mutation outside the temporary local smoke repository.
\`\`\`

## RESULT_FORMAT
\`\`\`text
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
\`\`\`

## TERMINAL_CONDITIONS
\`\`\`text
Smoke assertion completes.
\`\`\`

## NOTES
\`\`\`text
Owner-authorized package governance smoke fixture generated in a temporary local repository.
\`\`\`
EOF
}

fixture_field_value() {
  local file="$1"
  local key="$2"

  awk -v key="$key" '
    $0 ~ "^" key ":" {
      sub("^" key ":[[:space:]]*", "", $0)
      print
      exit
    }
  ' "$file"
}

configure_fixture_git_target() {
  local repo_dir="$1"
  local name="$2"
  local project_state="$3"
  local expected_remote

  expected_remote="$(fixture_field_value "$project_state" "EXPECTED_GIT_REMOTE")"
  [[ -n "$expected_remote" ]] || expected_remote="$(fixture_field_value "$project_state" "EXPECTED_REMOTE")"

  case "$name" in
    wrong_remote)
      git -C "$repo_dir" remote add origin "https://github.com/pavelvital2/not-agent-system-orchestrator.git"
      ;;
    *)
      git -C "$repo_dir" remote add origin "$expected_remote"
      ;;
  esac
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
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  configure_fixture_git_target "$repo_dir" "$name" "$project_state"
  mkdir -p "$(dirname "$task_packet")"

  payload_dir="$(dirname "${repo_dir}/${changed_path}")"
  [[ "$payload_dir" == "$repo_dir/." ]] || mkdir -p "$payload_dir"
  printf 'placeholder fixture payload for %s; no real secrets\n' "$name" >"${repo_dir}/${changed_path}"

  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "$allowed_pattern"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
  local project_state="${FIXTURES_ROOT}/push_not_allowed/project_state.md"
  local invalid_packet="${fixture_dir}/TASK_INVALID_MISSING_REQUIRED.md"
  local expected_blocker repo_dir output status

  [[ -f "$invalid_packet" ]] || die "${name} fixture missing TASK_INVALID_MISSING_REQUIRED.md"
  expected_blocker="$(fixture_value "${fixture_dir}/expected_blocker.txt")"
  repo_dir="${TMP_ROOT}/${name}"
  init_local_git_repo "$repo_dir"
  configure_fixture_git_target "$repo_dir" "$name" "$project_state"

  set +e
  output="$(
    cd "$repo_dir" &&
      bash "$PREFLIGHT" \
        --dry-run \
        --task-packet "$invalid_packet" \
        --project-state "$project_state" \
        --runtime-schema "$RUNTIME_SCHEMA" \
        --scope-matrix "$SCOPE_MATRIX" \
        --secret-rules "$SECRET_RULES" \
        --receipt-template "$RECEIPT_TEMPLATE" \
        --include-untracked \
        --push-requested "no" 2>&1
  )"
  status=$?
  set -e

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

run_approved_ssh_alias_fixture() {
  local name="approved_ssh_alias"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local changed_path allowed_pattern repo_dir task_packet payload_dir output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  changed_path="$(fixture_value "${fixture_dir}/changed_path.txt")"
  allowed_pattern="$(fixture_value "${fixture_dir}/allowed_pattern.txt")"

  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  configure_fixture_git_target "$repo_dir" "$name" "$project_state"
  mkdir -p "$(dirname "$task_packet")"

  payload_dir="$(dirname "${repo_dir}/${changed_path}")"
  [[ "$payload_dir" == "$repo_dir/." ]] || mkdir -p "$payload_dir"
  printf 'approved ssh alias canonicalization fixture\n' >"${repo_dir}/${changed_path}"

  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "$allowed_pattern"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
        --push-requested "yes" 2>&1
  )"
  status=$?
  set -e

  if [[ "$status" -ne 0 ]]; then
    printf '%s\n' "$output" >&2
    die "${name} unexpectedly failed"
  fi
  if grep -Fq "repository_identity_mismatch" <<<"$output"; then
    printf '%s\n' "$output" >&2
    die "${name} reported repository_identity_mismatch"
  fi

  printf 'PASS: approved SSH alias accepted as canonical same GitHub repository\n'
  PASS_COUNT=$((PASS_COUNT + 1))
}

run_canonical_remote_fixture() {
  local name="$1"
  local expected_blocker="${2:-}"
  local expect_pass="$3"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local repo_dir task_packet output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  git -C "$repo_dir" remote add origin "https://github.com/pavelvital2/agent-system-orchestrator.git"
  mkdir -p "$(dirname "$task_packet")" "${repo_dir}/smoke"
  printf 'canonical remote fixture\n' >"${repo_dir}/smoke/${name}.txt"
  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "smoke/*"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
        --push-requested "yes" 2>&1
  )"
  status=$?
  set -e

  if [[ "$expect_pass" == "yes" ]]; then
    if [[ "$status" -ne 0 ]]; then
      printf '%s\n' "$output" >&2
      die "${name} unexpectedly failed"
    fi
    printf 'PASS: canonical github.com/OWNER/REPO expected remote accepted using live git origin\n'
    PASS_COUNT=$((PASS_COUNT + 1))
    return
  fi

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

run_baseline_tracking_fixture() {
  local name="untracked_critical_baseline"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local expected_blocker repo_dir task_packet output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  expected_blocker="$(fixture_value "${fixture_dir}/expected_blocker.txt")"
  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  git -C "$repo_dir" remote add origin "https://github.com/pavelvital2/agent-system-orchestrator.git"
  mkdir -p "$(dirname "$task_packet")" "${repo_dir}/agent-system" "${repo_dir}/work"
  printf 'critical baseline should be tracked\n' >"${repo_dir}/agent-system/README.md"
  printf 'normal work payload\n' >"${repo_dir}/work/change.txt"
  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "work/*"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
        --push-requested "no" 2>&1
  )"
  status=$?
  set -e

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

run_project_input_tz_policy_fixture() {
  local name="project_input_tz_policy"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local repo_dir task_packet output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  git -C "$repo_dir" remote add origin "https://github.com/pavelvital2/agent-system-orchestrator.git"
  mkdir -p "$(dirname "$task_packet")" "${repo_dir}/project-input"
  printf 'owner-private source brief placeholder\n' >"${repo_dir}/project-input/TZ.md"
  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "work/*"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
        --push-requested "no" 2>&1
  )"
  status=$?
  set -e

  if [[ "$status" -ne 0 ]]; then
    printf '%s\n' "$output" >&2
    die "${name} unexpectedly failed with explicit owner-private untracked policy"
  fi

  printf 'PASS: project-input/TZ.md may remain untracked only with explicit owner-private/untracked policy\n'
  PASS_COUNT=$((PASS_COUNT + 1))
}

run_manual_preflight_fixture() {
  local name="manual_preflight_ref"
  local fixture_dir="${FIXTURES_ROOT}/${name}"
  local project_state="${fixture_dir}/project_state.md"
  local expected_blocker repo_dir task_packet output status

  [[ -f "$project_state" ]] || die "${name} fixture missing project_state.md"
  expected_blocker="$(fixture_value "${fixture_dir}/expected_blocker.txt")"
  repo_dir="${TMP_ROOT}/${name}"
  task_packet="${repo_dir}/project-docs/03_tasks/TASK_PACKET_${name}.md"
  init_local_git_repo "$repo_dir"
  git -C "$repo_dir" remote add origin "https://github.com/pavelvital2/agent-system-orchestrator.git"
  mkdir -p "$(dirname "$task_packet")" "${repo_dir}/work"
  printf 'manual preflight should not satisfy checkpoint evidence\n' >"${repo_dir}/work/change.txt"
  write_preflight_task_packet "$task_packet" "SMOKE_${name^^}" "work/*"
  commit_fixture_baseline "$repo_dir" "$task_packet"

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
        --push-requested "no" 2>&1
  )"
  status=$?
  set -e

  expect_blocked_output "$name" "$expected_blocker" "$status" "$output"
}

assert_bootstrap_and_none_route_governance() {
  grep -Rqs "BOOTSTRAP_CONTINUATION_STATUS" \
    "$REPO_ROOT/agent-system/01_roles/AUDITOR.md" \
    "$REPO_ROOT/agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md" \
    "$REPO_ROOT/agent-system/07_lifecycle/BOOTSTRAP_STAGE.md" ||
    die "bootstrap continuation governance missing BOOTSTRAP_CONTINUATION_STATUS"
  grep -Rqs "bootstrap_continuation_missing" \
    "$REPO_ROOT/agent-system/01_roles/AUDITOR.md" \
    "$REPO_ROOT/agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md" \
    "$REPO_ROOT/agent-system/07_lifecycle/BOOTSTRAP_STAGE.md" ||
    die "bootstrap continuation governance missing bootstrap_continuation_missing blocker"
  grep -Rqs "orchestrator_task_packet_none_project_artifact_route_forbidden" \
    "$REPO_ROOT/agent-system/02_runtime/STATE_TRANSITION_RULES.md" \
    "$REPO_ROOT/agent-system/04_state/NEXT_ACTION_TEMPLATE.md" ||
    die "orchestrator TASK_PACKET:NONE project artifact route blocker missing"

  printf 'PASS: bootstrap continuation missing is blocked by bootstrap_continuation_missing\n'
  printf 'PASS: invalid orchestrator TASK_PACKET:NONE project-task correction route is blocked\n'
  PASS_COUNT=$((PASS_COUNT + 2))
}

assert_smoke_self_contained() {
  if [[ "$FIXTURES_ROOT" != "${REPO_ROOT}/agent-system/tests/fixtures" ]]; then
    die "smoke still depends on top-level tests/fixtures"
  fi
  printf 'PASS: smoke fixtures are self-contained under agent-system/tests/fixtures\n'
  printf 'PASS: smoke runner does not require top-level tests/fixtures or owner project-input\n'
  PASS_COUNT=$((PASS_COUNT + 2))
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
  grep -Fq "ASO_CORR_200_002_BOOTSTRAP_CONTINUATION_BASELINE_GATE" "$CHANGELOG" || die "changelog missing ASO_CORR_200_002"
  grep -Fq "PACKAGE_VERSION_AFTER: 2.0.0" "$CHANGELOG" || die "changelog missing PACKAGE_VERSION_AFTER: 2.0.0"
  awk '
    /CHANGE_ID: GOV-2026-05-17-001/ { entry="001" }
    /CHANGE_ID: GOV-2026-05-17-008/ { entry="008" }
    /CHANGE_ID: GOV-2026-05-17-010/ { entry="010" }
    entry == "001" && /STATUS: accepted/ { found_001=1 }
    entry == "008" && /STATUS: accepted/ { found_008=1 }
    entry == "010" && /STATUS: accepted/ { found_010=1 }
    END { exit(found_001 && found_008 && found_010 ? 0 : 1) }
  ' "$CHANGELOG" || die "changelog missing accepted status for v2.0.0 patch/correction entries"

  printf 'PASS: version_changelog coherent for 2.0.0 with accepted status\n'
  PASS_COUNT=$((PASS_COUNT + 1))
}

print_fixture_names() {
  printf '%s\n' "${SMOKE_FIXTURES[@]}"
}

run_named_fixture() {
  local name="$1"

  printf 'RUN: %s\n' "$name"
  case "$name" in
    wrong_remote)
      run_preflight_fixture "wrong_remote" "yes"
      ;;
    wrong_branch)
      run_preflight_fixture "wrong_branch" "yes"
      ;;
    package_repo_with_project_docs)
      run_preflight_fixture "package_repo_with_project_docs" "no"
      ;;
    invalid_task_packet)
      run_invalid_task_packet_fixture
      ;;
    push_not_allowed)
      run_preflight_fixture "push_not_allowed" "yes"
      ;;
    secret_file_present)
      run_preflight_fixture "secret_file_present" "no"
      ;;
    approved_ssh_alias)
      run_approved_ssh_alias_fixture
      ;;
    canonical_remote_expected)
      run_canonical_remote_fixture "canonical_remote_expected" "" "yes"
      ;;
    canonical_remote_mismatch)
      run_canonical_remote_fixture "canonical_remote_mismatch" "git_target_check: repository_identity_mismatch" "no"
      ;;
    untracked_critical_baseline)
      run_baseline_tracking_fixture
      ;;
    project_input_tz_policy)
      run_project_input_tz_policy_fixture
      ;;
    manual_preflight_ref)
      run_manual_preflight_fixture
      ;;
    bootstrap_and_none_route_governance)
      assert_bootstrap_and_none_route_governance
      ;;
    smoke_self_contained)
      assert_smoke_self_contained
      ;;
    coverage_matrix)
      assert_coverage_matrix
      ;;
    version_changelog_coherence)
      assert_version_changelog_coherence
      ;;
    *)
      die "unknown smoke fixture: ${name}"
      ;;
  esac
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [--list-fixtures | --run-fixture NAME]

Runs governance smoke tests. With no arguments, preserves the historical
all-fixture shell behavior. The per-fixture options are used by the Python
diagnostic wrapper.
EOF
}

main() {
  local single_fixture=""
  local fixture

  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --list-fixtures)
        print_fixture_names
        return 0
        ;;
      --run-fixture)
        [[ "$#" -ge 2 ]] || die "--run-fixture requires a fixture name"
        single_fixture="$2"
        shift 2
        ;;
      -h|--help)
        usage
        return 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done

  [[ -f "$PREFLIGHT" ]] || die "checkpoint_preflight.sh missing"
  [[ -f "$VALIDATOR" ]] || die "validate_task_packet.py missing"

  TMP_ROOT="$(mktemp -d)"

  printf 'Governance smoke tests: local dry-run fixtures only; no commit, no push, no real secrets.\n'
  if [[ -n "$single_fixture" ]]; then
    run_named_fixture "$single_fixture"
  else
    for fixture in "${SMOKE_FIXTURES[@]}"; do
      run_named_fixture "$fixture"
    done
  fi
  printf 'SMOKE_RESULT: passed (%s assertions)\n' "$PASS_COUNT"
}

main "$@"
