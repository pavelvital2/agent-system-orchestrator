#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASK_PACKET=""
PROJECT_STATE_FILE="${PROJECT_STATE_FILE:-project-runtime/PROJECT_STATE.md}"
RUNTIME_SCHEMA_FILE="${RUNTIME_SCHEMA_FILE:-agent-system/04_state/RUNTIME_STATE_SCHEMA.md}"
SCOPE_MATRIX_FILE="${SCOPE_MATRIX_FILE:-agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md}"
SECRET_RULES_FILE="${SECRET_RULES_FILE:-agent-system/09_validators/SECRET_SCAN_RULES.md}"
RECEIPT_TEMPLATE_FILE="${RECEIPT_TEMPLATE_FILE:-agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md}"
TASK_PACKET_VALIDATOR_FILE="${TASK_PACKET_VALIDATOR_FILE:-${SCRIPT_DIR}/validate_task_packet.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RECEIPT_PATH=""
TARGET_ROLE=""
WORKSPACE_TYPE_OVERRIDE=""
EXPECTED_REMOTE_OVERRIDE=""
ACTUAL_REMOTE_OVERRIDE=""
EXPECTED_BRANCH_OVERRIDE=""
ACTUAL_BRANCH_OVERRIDE=""
PUSH_REQUESTED="auto"
INCLUDE_UNTRACKED=0
WRITE_RECEIPT=0

failures=()
notes=()
changed_files=()
allowed_patterns=()
forbidden_patterns=()

usage() {
  cat <<'USAGE'
Usage:
  checkpoint_preflight.sh --task-packet PATH [options]

Options:
  --dry-run                         Run checks without staging, committing, or pushing (default).
  --task-packet PATH                Active audited task packet.
  --project-state PATH              Runtime PROJECT_STATE.md path.
  --runtime-schema PATH             Runtime schema doc path.
  --scope-matrix PATH               Changed files scope matrix path.
  --secret-rules PATH               Secret scan rules path.
  --task-packet-validator PATH      Full TASK_PACKET validator path.
  --receipt-template PATH           Checkpoint eligibility receipt template path.
  --receipt PATH                    Receipt output path.
  --write-receipt                   Write receipt to --receipt path.
  --role ROLE                       Expected target role override.
  --workspace-type TYPE             Workspace type override.
  --expected-remote REMOTE          Expected remote override.
  --actual-remote REMOTE            Deprecated compatibility option; live git origin is used.
  --expected-branch BRANCH          Expected branch override.
  --actual-branch BRANCH            Deprecated compatibility option; live git branch is used.
  --push-requested yes|no|auto      Validate push target and lock.
  --include-untracked               Include untracked files in file-scope and secret checks.
  --help                            Show this help.
USAGE
}

add_failure() {
  failures+=("$1")
}

add_note() {
  notes+=("$1")
}

field_value() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 0
  awk -v key="$key" '
    $0 ~ "^" key ":" {
      sub("^" key ":[[:space:]]*", "", $0)
      print
      exit
    }
  ' "$file"
}

section_text() {
  local file="$1"
  local section="$2"
  awk -v section="$section" '
    $0 == section { in_section=1; next }
    in_section && /^---$/ { exit }
    in_section && /^## / { exit }
    in_section { print }
  ' "$file"
}

extract_list_section() {
  local file="$1"
  local section="$2"
  section_text "$file" "$section" |
    sed -e '/^```/d' -e 's/^[[:space:]]*- //' -e '/^[[:space:]]*$/d'
}

trim() {
  sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' <<<"$1"
}

alias_is_approved() {
  local candidate="$1"
  local aliases
  local evidence
  local alias

  aliases="$(field_value "$PROJECT_STATE_FILE" "APPROVED_SSH_HOST_ALIASES")"
  evidence="$(field_value "$PROJECT_STATE_FILE" "SSH_ALIAS_EVIDENCE")"

  IFS=', ' read -r -a alias_values <<<"$aliases"
  for alias in "${alias_values[@]}"; do
    [[ -n "$alias" && "$alias" != "NONE" ]] || continue
    [[ "$alias" == "$candidate" ]] && return 0
  done

  [[ "$evidence" == *"hostname github.com"* ]] && return 0

  return 1
}

canonical_github_path() {
  local path="$1"
  local owner
  local repo

  path="${path%.git}"
  [[ "$path" == */* ]] || return 1

  owner="${path%%/*}"
  repo="${path#*/}"

  [[ -n "$owner" ]] || return 1
  [[ -n "$repo" ]] || return 1
  [[ "$repo" != */* ]] || return 1

  printf 'github.com/%s/%s\n' "${owner,,}" "${repo,,}"
}

canonical_remote() {
  local raw
  local host
  local path

  raw="$(trim "$1")"
  [[ -n "$raw" ]] || return 2

  if [[ "$raw" =~ ^https://([^/]+)/(.+)$ ]]; then
    host="${BASH_REMATCH[1],,}"
    path="${BASH_REMATCH[2]}"
    [[ "$host" == "github.com" ]] || return 2
    canonical_github_path "$path" || return 2
    return 0
  fi

  if [[ "$raw" =~ ^github\.com/([^/]+)/([^/]+)(\.git)?$ ]]; then
    canonical_github_path "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}" || return 2
    return 0
  fi

  if [[ "$raw" =~ ^git@([^:]+):(.+)$ ]]; then
    host="${BASH_REMATCH[1]}"
    path="${BASH_REMATCH[2]}"

    if [[ "${host,,}" == "github.com" ]]; then
      canonical_github_path "$path" || return 2
      return 0
    fi

    if alias_is_approved "$host"; then
      canonical_github_path "$path" || return 2
      return 0
    fi

    return 3
  fi

  return 2
}

matches_any_pattern() {
  local path="$1"
  shift
  local pattern
  for pattern in "$@"; do
    [[ -n "$pattern" && "$pattern" != "NONE" ]] || continue
    case "$path" in
      $pattern) return 0 ;;
    esac
  done
  return 1
}

task_packet_check() {
  local output
  local status
  local line

  [[ -f "$TASK_PACKET" ]] || {
    add_failure "task_packet_schema_check: task_packet_missing"
    return
  }

  if [[ ! -f "$TASK_PACKET_VALIDATOR_FILE" ]]; then
    add_failure "task_packet_schema_check: validator_missing:${TASK_PACKET_VALIDATOR_FILE}"
    return
  fi

  set +e
  output="$(
    "$PYTHON_BIN" "$TASK_PACKET_VALIDATOR_FILE" \
      --mode checkpoint \
      --allow-first-bootstrap \
      --allow-system-package-correction \
      "$TASK_PACKET" 2>&1
  )"
  status=$?
  set +e

  if [[ "$status" -ne 0 ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      case "$line" in
        ERROR:*) add_failure "task_packet_schema_check: ${line#ERROR: }" ;;
      esac
    done <<<"$output"
    if ! grep -Fq "invalid_task_packet_schema" <<<"$output"; then
      add_failure "task_packet_schema_check: invalid_task_packet_schema"
    fi
  fi

  mapfile -t allowed_patterns < <(extract_list_section "$TASK_PACKET" "## ALLOWED_FILE_CHANGES")
  mapfile -t forbidden_patterns < <(extract_list_section "$TASK_PACKET" "## FORBIDDEN_FILE_CHANGES")

  [[ ${#allowed_patterns[@]} -gt 0 ]] || add_failure "task_packet_schema_check: allowed_file_changes_missing"
}

runtime_schema_check() {
  local required_schema_fields=(
    "AUDIT_STATUS"
    "CHECKPOINT_ELIGIBILITY_STATUS"
    "CHECKPOINT_PREFLIGHT_STATUS"
    "CHECKPOINT_RECEIPT_REF"
    "COMMIT_STATUS"
    "PUSH_STATUS"
    "LAST_PUSH_TARGET_STATUS"
    "PROJECT_CHECKPOINT_STATUS"
  )
  local field
  local audit_status
  local preflight_ref

  [[ -f "$RUNTIME_SCHEMA_FILE" ]] || {
    add_failure "runtime_schema_check: runtime_schema_missing"
    return
  }

  for field in "${required_schema_fields[@]}"; do
    grep -q "$field" "$RUNTIME_SCHEMA_FILE" || add_failure "runtime_schema_check: missing_${field}"
  done

  [[ -f "$PROJECT_STATE_FILE" ]] || {
    add_failure "runtime_schema_check: project_state_missing"
    return
  }

  for field in "${required_schema_fields[@]}"; do
    grep -q "^${field}:" "$PROJECT_STATE_FILE" || add_failure "runtime_schema_check: project_state_missing_${field}"
  done

  audit_status="$(field_value "$PROJECT_STATE_FILE" "AUDIT_STATUS")"
  [[ "$audit_status" == "passed" ]] || add_failure "runtime_schema_check: audit_status_not_passed"

  preflight_ref="$(field_value "$PROJECT_STATE_FILE" "CHECKPOINT_PREFLIGHT_REF")"
  if [[ "${preflight_ref,,}" == *"manual preflight"* ]]; then
    add_failure "checkpoint_preflight_evidence_check: manual_preflight_ref_insufficient"
  fi
}

identity_and_git_target_check() {
  local git_top=""
  local expected_git_top=""
  local expected_remote=""
  local actual_remote=""
  local expected_branch=""
  local actual_branch=""
  local expected_canonical=""
  local actual_canonical=""
  local workspace_type=""
  local identity_status=""
  local lock_status=""
  local push_allowed=""

  git_top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "$git_top" ]] || {
    add_failure "identity_check: not_inside_git_worktree"
    return
  }
  expected_git_top="$(field_value "$PROJECT_STATE_FILE" "PROJECT_ROOT_EXPECTED")"
  if [[ -n "$expected_git_top" && "$expected_git_top" != "NONE" ]]; then
    if [[ "$(cd "$git_top" && pwd -P)" != "$(cd "$expected_git_top" 2>/dev/null && pwd -P)" ]]; then
      add_failure "identity_check: git_toplevel_mismatch"
    fi
  fi

  expected_remote="${EXPECTED_REMOTE_OVERRIDE:-$(field_value "$PROJECT_STATE_FILE" "EXPECTED_GIT_REMOTE")}"
  [[ -n "$expected_remote" ]] || expected_remote="$(field_value "$PROJECT_STATE_FILE" "EXPECTED_REMOTE")"
  actual_remote="$(git config --get remote.origin.url 2>/dev/null || true)"

  expected_branch="${EXPECTED_BRANCH_OVERRIDE:-$(field_value "$PROJECT_STATE_FILE" "EXPECTED_BRANCH")}"
  actual_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"

  if [[ -n "$ACTUAL_REMOTE_OVERRIDE" || -n "$ACTUAL_BRANCH_OVERRIDE" ]]; then
    add_note "identity_check: deprecated_actual_overrides_ignored_live_git_used"
  fi

  workspace_type="${WORKSPACE_TYPE_OVERRIDE:-$(field_value "$PROJECT_STATE_FILE" "WORKSPACE_TYPE")}"
  identity_status="$(field_value "$PROJECT_STATE_FILE" "IDENTITY_VALIDATION_STATUS")"
  lock_status="$(field_value "$PROJECT_STATE_FILE" "REPOSITORY_LOCK_STATUS")"
  push_allowed="$(field_value "$PROJECT_STATE_FILE" "PUSH_ALLOWED")"

  case "$workspace_type" in
    package_repo|project_workspace|implementation_repo|test_fixture) ;;
    *) add_failure "identity_check: invalid_or_missing_workspace_type" ;;
  esac

  [[ "$identity_status" == "passed" ]] || add_failure "identity_check: identity_validation_not_passed"
  [[ -n "$expected_remote" ]] || add_failure "git_target_check: expected_remote_missing"
  [[ -n "$actual_remote" ]] || add_failure "git_target_check: actual_remote_missing"
  [[ -n "$expected_branch" ]] || add_failure "git_target_check: expected_branch_missing"
  [[ -n "$actual_branch" ]] || add_failure "git_target_check: actual_branch_missing"

  if [[ -n "$expected_remote" && -n "$actual_remote" ]]; then
    expected_canonical="$(canonical_remote "$expected_remote" 2>/dev/null || true)"
    actual_canonical="$(canonical_remote "$actual_remote" 2>/dev/null || true)"
    [[ -n "$expected_canonical" && -n "$actual_canonical" && "$expected_canonical" == "$actual_canonical" ]] || add_failure "git_target_check: repository_identity_mismatch"
  fi

  if [[ -n "$expected_branch" && -n "$actual_branch" ]]; then
    [[ "$expected_branch" == "$actual_branch" ]] || add_failure "git_target_check: repository_branch_mismatch"
  fi

  if [[ "$PUSH_REQUESTED" == "yes" || ( "$PUSH_REQUESTED" == "auto" && "$(field_value "$PROJECT_STATE_FILE" "CHECKPOINT_ELIGIBILITY")" == "push_allowed" ) ]]; then
    [[ "$workspace_type" != "test_fixture" ]] || add_failure "git_target_check: push_forbidden_for_test_fixture"
    [[ "$lock_status" == "accepted" ]] || add_failure "git_target_check: repository_lock_not_accepted"
    [[ "$push_allowed" == "true" ]] || add_failure "git_target_check: push_without_repository_lock"
  fi
}

baseline_policy_allows_untracked_project_input_tz() {
  local policy

  policy="$(field_value "$PROJECT_STATE_FILE" "PROJECT_INPUT_TRACKING_POLICY")"
  [[ "${policy,,}" == *"owner-private"* || "${policy,,}" == *"untracked"* ]]
}

is_untracked_path() {
  local path="$1"
  git ls-files --others --exclude-standard -- "$path" 2>/dev/null | grep -Fxq "$path"
}

baseline_tracking_check() {
  local path
  local untracked=()

  mapfile -t untracked < <(git ls-files --others --exclude-standard 2>/dev/null | sed '/^[[:space:]]*$/d')

  for path in "${untracked[@]}"; do
    case "$path" in
      agent-system|agent-system/*)
        add_failure "baseline_tracking_check: untracked_critical_baseline:${path}"
        ;;
      project-runtime/WORKSPACE_IDENTITY.md|project-runtime/REPOSITORY_LOCK.md|project-runtime/PROJECT_STATE.md|project-runtime/NEXT_ACTION.md|project-runtime/CURRENT_GATE.md|project-runtime/runtime-state/*)
        add_failure "baseline_tracking_check: untracked_critical_baseline:${path}"
        ;;
      .gitignore)
        add_failure "baseline_tracking_check: untracked_critical_baseline:${path}"
        ;;
      project-input/TZ.md)
        if ! baseline_policy_allows_untracked_project_input_tz; then
          add_failure "baseline_tracking_check: untracked_project_input_tz_without_policy:${path}"
        fi
        ;;
    esac
  done
}

collect_changed_files() {
  local tmp
  tmp="$(mktemp)"
  git diff --name-only >"$tmp" 2>/dev/null || true
  git diff --cached --name-only >>"$tmp" 2>/dev/null || true
  if [[ "$INCLUDE_UNTRACKED" -eq 1 ]]; then
    git ls-files --others --exclude-standard >>"$tmp" 2>/dev/null || true
  fi
  mapfile -t changed_files < <(sort -u "$tmp" | sed '/^[[:space:]]*$/d')
  rm -f "$tmp"
}

file_scope_check() {
  local path
  local target_role_effective
  local workspace_type_effective
  local package_governance_task=0

  [[ -f "$SCOPE_MATRIX_FILE" ]] || add_failure "changed_files_scope_check: scope_matrix_missing"
  collect_changed_files
  target_role_effective="${TARGET_ROLE:-$(section_text "$TASK_PACKET" "## TARGET_ROLE" | sed -n '/^```/d; /[[:alnum:]_]/ { p; q; }')}"
  workspace_type_effective="${WORKSPACE_TYPE_OVERRIDE:-$(field_value "$PROJECT_STATE_FILE" "WORKSPACE_TYPE")}"
  if grep -qi "package-governance correction/update\|owner-authorized package" "$TASK_PACKET" 2>/dev/null; then
    package_governance_task=1
  fi

  if [[ ${#changed_files[@]} -eq 0 ]]; then
    add_note "changed_files_scope_check: no_changed_files"
    return
  fi

  for path in "${changed_files[@]}"; do
    if [[ "$path" == "project-input/TZ.md" ]] &&
      is_untracked_path "$path" &&
      baseline_policy_allows_untracked_project_input_tz; then
      add_note "changed_files_scope_check: project_input_tz_owner_private_untracked_policy:${path}"
      continue
    fi
    if matches_any_pattern "$path" "${forbidden_patterns[@]}"; then
      add_failure "changed_files_scope_check: forbidden_path:${path}"
      continue
    fi
    if ! matches_any_pattern "$path" "${allowed_patterns[@]}"; then
      add_failure "changed_files_scope_check: path_not_allowed:${path}"
    fi
    case "$path" in
      project-runtime/*)
        [[ "$target_role_effective" == "orchestrator" ]] || add_failure "changed_files_scope_check: role_matrix_runtime_forbidden:${path}"
        ;;
      project-input/*|project-archive/*)
        add_failure "changed_files_scope_check: role_matrix_source_or_archive_forbidden:${path}"
        ;;
      project-docs/*)
        if [[ "$workspace_type_effective" == "package_repo" ]]; then
          add_failure "changed_files_scope_check: package_repo_project_doc_pollution:${path}"
        fi
        ;;
      agent-system/*)
        if [[ "$workspace_type_effective" != "package_repo" && "$package_governance_task" -ne 1 ]]; then
          add_failure "changed_files_scope_check: workspace_matrix_agent_system_forbidden:${path}"
        fi
        ;;
    esac
  done
}

secret_scan_check() {
  local path
  local lower
  local secret_regex

  [[ -f "$SECRET_RULES_FILE" ]] || add_failure "secret_scan_check: secret_rules_missing"

  secret_regex='(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Authorization:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9._-]{16,}|api[_-]?key[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9._-]{16,}|password[[:space:]_:-]*[:=][[:space:]]*[^[:space:]<>]{6,}|session[_-]?token[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9._-]{16,})'

  for path in "${changed_files[@]}"; do
    [[ -e "$path" && ! -d "$path" ]] || continue
    lower="${path,,}"
    case "$lower" in
      .env|.env.*|*/.env|*/.env.*|*.pem|*.key|*.p12|*.pfx|*.kdbx|*.har|*cookie*|*session*|*localstorage*|*"local storage"*|*"login data"*|id_rsa|id_dsa|id_ecdsa|id_ed25519|*/id_rsa|*/id_dsa|*/id_ecdsa|*/id_ed25519|*.npmrc|*.pypirc|*.netrc|.docker/config.json|*/.docker/config.json|*kubeconfig*|*credentials*|*token*)
        add_failure "secret_scan_check: potential_secret_exposure:${path}:sensitive_path"
        continue
        ;;
    esac

    if [[ "$(wc -c <"$path" 2>/dev/null || echo 0)" -gt 1048576 ]]; then
      add_note "secret_scan_check: skipped_large_file:${path}"
      continue
    fi

    if grep -Iq . "$path" 2>/dev/null && LC_ALL=C grep -Eiq "$secret_regex" "$path" 2>/dev/null; then
      add_failure "secret_scan_check: potential_secret_exposure:${path}:content_pattern"
    fi
  done
}

emit_receipt() {
  local task_id
  local attempt_no
  local audit_status
  local eligibility_status="eligible"
  local preflight_status="passed"
  local secret_status="passed"
  local git_target_status="matched"
  local file_scope_status="passed"
  local task_schema_status="passed"
  local runtime_schema_status="passed"
  local project_checkpoint_status="pending"
  local failure_reason="NONE"
  local receipt

  task_id="$(section_text "$TASK_PACKET" "## TASK_ID" | sed -n '/^```/d; /[[:alnum:]_]/ { p; q; }')"
  [[ -n "$task_id" ]] || task_id="UNKNOWN"
  attempt_no="$(section_text "$TASK_PACKET" "## ATTEMPT_NO" | sed -n '/^```/d; /[[:alnum:]_]/ { p; q; }')"
  [[ -n "$attempt_no" ]] || attempt_no="UNKNOWN"
  audit_status="$(field_value "$PROJECT_STATE_FILE" "AUDIT_STATUS")"
  [[ -n "$audit_status" ]] || audit_status="not_applicable"

  if [[ ${#failures[@]} -gt 0 ]]; then
    eligibility_status="blocked"
    preflight_status="failed"
    project_checkpoint_status="blocked"
    failure_reason="$(printf '%s; ' "${failures[@]}")"
  fi
  printf '%s\n' "${failures[@]}" | grep -q "potential_secret_exposure" && secret_status="potential_secret_exposure"
  printf '%s\n' "${failures[@]}" | grep -q "git_target_check" && git_target_status="mismatched"
  printf '%s\n' "${failures[@]}" | grep -q "changed_files_scope_check" && file_scope_status="failed"
  printf '%s\n' "${failures[@]}" | grep -q "task_packet_schema_check" && task_schema_status="failed"
  printf '%s\n' "${failures[@]}" | grep -q "runtime_schema_check" && runtime_schema_status="failed"

  receipt="$(cat <<EOF
RECEIPT_ID: CHECKPOINT_ELIGIBILITY_${task_id}_${attempt_no}
TASK_ID: ${task_id}
ATTEMPT_NO: ${attempt_no}
CREATED_AT: dry_run
CREATED_BY: orchestrator
TASK_PACKET: ${TASK_PACKET}
ACCEPTED_RESULT_REF: UNKNOWN
AUDIT_REF: UNKNOWN
AUDIT_STATUS: ${audit_status}
CHECKPOINT_POLICY: UNKNOWN
CHECKPOINT_ELIGIBILITY_STATUS: ${eligibility_status}
CHECKPOINT_PREFLIGHT_STATUS: ${preflight_status}
CHECKPOINT_PREFLIGHT_REF: agent-system/scripts/checkpoint_preflight.sh
WORKSPACE_TYPE: ${WORKSPACE_TYPE_OVERRIDE:-$(field_value "$PROJECT_STATE_FILE" "WORKSPACE_TYPE")}
IDENTITY_CHECK_STATUS: $([[ "$eligibility_status" == "eligible" ]] && printf 'passed' || printf 'blocked')
GIT_TARGET_CHECK_STATUS: ${git_target_status}
FILE_SCOPE_CHECK_STATUS: ${file_scope_status}
TASK_PACKET_SCHEMA_STATUS: ${task_schema_status}
RUNTIME_SCHEMA_STATUS: ${runtime_schema_status}
SECRET_SCAN_STATUS: ${secret_status}
COMMIT_STATUS: not_attempted
COMMIT_HASH: NONE
COMMIT_BRANCH: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'UNKNOWN')
PUSH_STATUS: not_attempted
PUSH_REMOTE: $(git config --get remote.origin.url 2>/dev/null || printf 'UNKNOWN')
PUSH_BRANCH: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'UNKNOWN')
LAST_PUSH_TARGET_STATUS: ${git_target_status}
PROJECT_CHECKPOINT_STATUS: ${project_checkpoint_status}
ACCEPTED_FILES: $(printf '%s ' "${changed_files[@]:-NONE}")
BLOCKED_BY: $([[ ${#failures[@]} -gt 0 ]] && printf 'checkpoint_preflight' || printf 'NONE')
FAILURE_REASON_REDACTED: ${failure_reason}
RECOVERY_ROUTE: $([[ ${#failures[@]} -gt 0 ]] && printf 'governed_correction_or_owner_handling' || printf 'NONE')
EOF
)"

  printf '%s\n' "$receipt"

  if [[ "$WRITE_RECEIPT" -eq 1 ]]; then
    if [[ -z "$RECEIPT_PATH" ]]; then
      add_failure "receipt_write: receipt_path_missing"
      return
    fi
    if [[ "$RECEIPT_PATH" != project-runtime/checkpoints/* ]]; then
      add_failure "receipt_write: receipt_path_outside_checkpoint_root"
      return
    fi
    mkdir -p "$(dirname "$RECEIPT_PATH")"
    printf '%s\n' "$receipt" >"$RECEIPT_PATH"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) shift ;;
    --task-packet) TASK_PACKET="${2:-}"; shift 2 ;;
    --project-state) PROJECT_STATE_FILE="${2:-}"; shift 2 ;;
    --runtime-schema) RUNTIME_SCHEMA_FILE="${2:-}"; shift 2 ;;
    --scope-matrix) SCOPE_MATRIX_FILE="${2:-}"; shift 2 ;;
    --secret-rules) SECRET_RULES_FILE="${2:-}"; shift 2 ;;
    --task-packet-validator) TASK_PACKET_VALIDATOR_FILE="${2:-}"; shift 2 ;;
    --receipt-template) RECEIPT_TEMPLATE_FILE="${2:-}"; shift 2 ;;
    --receipt) RECEIPT_PATH="${2:-}"; shift 2 ;;
    --write-receipt) WRITE_RECEIPT=1; shift ;;
    --role) TARGET_ROLE="${2:-}"; shift 2 ;;
    --workspace-type) WORKSPACE_TYPE_OVERRIDE="${2:-}"; shift 2 ;;
    --expected-remote) EXPECTED_REMOTE_OVERRIDE="${2:-}"; shift 2 ;;
    --actual-remote) ACTUAL_REMOTE_OVERRIDE="${2:-}"; shift 2 ;;
    --expected-branch) EXPECTED_BRANCH_OVERRIDE="${2:-}"; shift 2 ;;
    --actual-branch) ACTUAL_BRANCH_OVERRIDE="${2:-}"; shift 2 ;;
    --push-requested) PUSH_REQUESTED="${2:-auto}"; shift 2 ;;
    --include-untracked) INCLUDE_UNTRACKED=1; shift ;;
    --help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$TASK_PACKET" ]] || {
  printf 'checkpoint_preflight: --task-packet is required\n' >&2
  usage >&2
  exit 2
}

[[ -f "$RECEIPT_TEMPLATE_FILE" ]] || add_failure "receipt_template_check: receipt_template_missing"

task_packet_check
runtime_schema_check
identity_and_git_target_check
baseline_tracking_check
file_scope_check
secret_scan_check
emit_receipt

if [[ ${#notes[@]} -gt 0 ]]; then
  printf '\nNOTES:\n'
  printf '%s\n' "${notes[@]}"
fi

if [[ ${#failures[@]} -gt 0 ]]; then
  printf '\nPREFLIGHT_RESULT: blocked\n'
  printf 'FAILURES:\n'
  printf '%s\n' "${failures[@]}"
  exit 1
fi

printf '\nPREFLIGHT_RESULT: passed\n'
exit 0
