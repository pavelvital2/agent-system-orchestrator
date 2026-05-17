#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<'USAGE'
Usage:
  init_project_workspace.sh --target PATH --project-name NAME --project-slug SLUG \
    --expected-remote REMOTE --expected-branch BRANCH [options]

Required:
  --target PATH                 Project workspace root to initialize.
  --project-name NAME           Human-readable project name.
  --project-slug SLUG           Stable project slug.
  --expected-remote REMOTE      Expected GitHub repository remote.
  --expected-branch BRANCH      Expected Git branch.

Options:
  --source PATH                 Package repository root. Defaults to this script's repo root.
  --workspace-type TYPE         project_workspace, implementation_repo, or test_fixture.
                                Defaults to project_workspace.
  --approved-ssh-host-alias A   Accept git@A:OWNER/REPO.git as a GitHub alias.
  --ssh-alias-evidence TEXT     Bounded evidence such as: ssh -G alias -> hostname github.com
  --accept-repository-lock      Accept the repository lock after validating target .git.
  --push-allowed true|false     Write PUSH_ALLOWED. true requires accepted lock.
  --help                        Show this help.

Behavior:
  Copies only agent-system/ into the target workspace.
  Never copies or reuses the package repository .git directory.
  Blocks if the target inherits an ancestor Git worktree.
  Blocks if an existing target .git origin or branch mismatches expected inputs.
  Creates project-runtime/WORKSPACE_IDENTITY.md and project-runtime/REPOSITORY_LOCK.md.
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_value() {
  local flag="$1"
  local value="${2:-}"

  [[ -n "$value" ]] || die "$flag requires a value"
}

trim() {
  sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' <<<"$1"
}

join_aliases() {
  local joined="NONE"
  local alias

  for alias in "${APPROVED_SSH_HOST_ALIASES[@]}"; do
    if [[ "$joined" == "NONE" ]]; then
      joined="$alias"
    else
      joined="$joined,$alias"
    fi
  done

  printf '%s\n' "$joined"
}

alias_is_approved() {
  local candidate="$1"
  local alias

  for alias in "${APPROVED_SSH_HOST_ALIASES[@]}"; do
    [[ "$alias" == "$candidate" ]] && return 0
  done

  [[ "$SSH_ALIAS_EVIDENCE" == *"hostname github.com"* ]] && return 0

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

  printf 'github.com/%s/%s\n' "$owner" "$repo"
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

canonical_existing_dir() {
  local path="$1"

  [[ -d "$path" ]] || die "directory does not exist: $path"
  (cd "$path" && pwd -P)
}

canonical_target_path() {
  local path="$1"
  local parent
  local base

  if [[ -e "$path" ]]; then
    [[ -d "$path" ]] || die "target exists but is not a directory: $path"
    canonical_existing_dir "$path"
    return 0
  fi

  parent="$(dirname -- "$path")"
  base="$(basename -- "$path")"
  [[ -d "$parent" ]] || die "target parent directory does not exist: $parent"
  printf '%s/%s\n' "$(canonical_existing_dir "$parent")" "$base"
}

copy_agent_system() {
  local destination="$TARGET_ROOT/agent-system"

  [[ -d "$SOURCE_ROOT/agent-system" ]] || die "source agent-system directory not found: $SOURCE_ROOT/agent-system"
  [[ ! -e "$destination" ]] || die "target already has agent-system; use a governed upgrade/correction task instead"

  cp -R "$SOURCE_ROOT/agent-system" "$destination"
  find "$destination" -name .git -prune -exec rm -rf {} +
}

write_workspace_identity() {
  local identity_path="$TARGET_ROOT/project-runtime/WORKSPACE_IDENTITY.md"
  local aliases

  aliases="$(join_aliases)"

  [[ ! -e "$identity_path" ]] || die "refusing to overwrite existing workspace identity: $identity_path"

  cat >"$identity_path" <<EOF
# WORKSPACE_IDENTITY

PROJECT_NAME:
$PROJECT_NAME

PROJECT_SLUG:
$PROJECT_SLUG

WORKSPACE_TYPE:
$WORKSPACE_TYPE

PROJECT_ROOT_EXPECTED:
$TARGET_ROOT

GIT_TOPLEVEL_ACTUAL:
$GIT_TOPLEVEL_ACTUAL

EXPECTED_REMOTE:
$EXPECTED_REMOTE

ACTUAL_REMOTE:
$ACTUAL_REMOTE

EXPECTED_GIT_REMOTE:
$EXPECTED_GIT_REMOTE

ACTUAL_GIT_REMOTE:
$ACTUAL_GIT_REMOTE

EXPECTED_BRANCH:
$EXPECTED_BRANCH

ACTUAL_BRANCH:
$ACTUAL_BRANCH

APPROVED_SSH_HOST_ALIASES:
$aliases

SSH_ALIAS_EVIDENCE:
$SSH_ALIAS_EVIDENCE

PUSH_ALLOWED:
$EFFECTIVE_PUSH_ALLOWED

IDENTITY_VALIDATION_STATUS:
$IDENTITY_VALIDATION_STATUS

IDENTITY_VALIDATION_ERROR:
$IDENTITY_VALIDATION_ERROR

INITIALIZATION_COPY_POLICY:
agent-system copied without .git; project-input, project-runtime, and project-archive created locally.
EOF
}

write_repository_lock() {
  local lock_path="$TARGET_ROOT/project-runtime/REPOSITORY_LOCK.md"
  local accepted_at="NONE"

  [[ ! -e "$lock_path" ]] || die "refusing to overwrite existing repository lock: $lock_path"

  if [[ "$REPOSITORY_LOCK_STATUS" == "accepted" ]]; then
    accepted_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  fi

  cat >"$lock_path" <<EOF
# REPOSITORY_LOCK

LOCK_STATUS:
$REPOSITORY_LOCK_STATUS

WORKSPACE_TYPE:
$WORKSPACE_TYPE

PROJECT_SLUG:
$PROJECT_SLUG

EXPECTED_REMOTE:
$EXPECTED_REMOTE

EXPECTED_GIT_REMOTE:
$EXPECTED_GIT_REMOTE

EXPECTED_BRANCH:
$EXPECTED_BRANCH

ACTUAL_REMOTE_AT_LOCK:
$ACTUAL_REMOTE

ACTUAL_GIT_REMOTE_AT_LOCK:
$ACTUAL_GIT_REMOTE

ACTUAL_BRANCH_AT_LOCK:
$ACTUAL_BRANCH

PUSH_ALLOWED:
$EFFECTIVE_PUSH_ALLOWED

LOCK_ACCEPTED_AT:
$accepted_at

LOCK_ACCEPTANCE_REQUIREMENTS:
- expected remote input is required
- expected branch input is required
- target .git must be rooted at PROJECT_ROOT_EXPECTED before lock acceptance
- ACTUAL_GIT_REMOTE must equal EXPECTED_GIT_REMOTE before lock acceptance
- ACTUAL_BRANCH must equal EXPECTED_BRANCH before lock acceptance
- PUSH_ALLOWED true requires LOCK_STATUS accepted
- test_fixture workspaces must keep PUSH_ALLOWED false

COPY_PROTECTION:
The package repository .git directory was not copied or reused.
EOF
}

SOURCE_ROOT=""
TARGET_ROOT_INPUT=""
PROJECT_NAME=""
PROJECT_SLUG=""
WORKSPACE_TYPE="project_workspace"
EXPECTED_REMOTE=""
EXPECTED_BRANCH=""
ACCEPT_REPOSITORY_LOCK="false"
REQUESTED_PUSH_ALLOWED="false"
SSH_ALIAS_EVIDENCE="NONE"
APPROVED_SSH_HOST_ALIASES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      require_value "$1" "${2:-}"
      SOURCE_ROOT="$2"
      shift 2
      ;;
    --target)
      require_value "$1" "${2:-}"
      TARGET_ROOT_INPUT="$2"
      shift 2
      ;;
    --project-name)
      require_value "$1" "${2:-}"
      PROJECT_NAME="$2"
      shift 2
      ;;
    --project-slug)
      require_value "$1" "${2:-}"
      PROJECT_SLUG="$2"
      shift 2
      ;;
    --workspace-type)
      require_value "$1" "${2:-}"
      WORKSPACE_TYPE="$2"
      shift 2
      ;;
    --expected-remote)
      require_value "$1" "${2:-}"
      EXPECTED_REMOTE="$2"
      shift 2
      ;;
    --expected-branch)
      require_value "$1" "${2:-}"
      EXPECTED_BRANCH="$2"
      shift 2
      ;;
    --approved-ssh-host-alias)
      require_value "$1" "${2:-}"
      APPROVED_SSH_HOST_ALIASES+=("$2")
      shift 2
      ;;
    --ssh-alias-evidence)
      require_value "$1" "${2:-}"
      SSH_ALIAS_EVIDENCE="$2"
      shift 2
      ;;
    --accept-repository-lock)
      ACCEPT_REPOSITORY_LOCK="true"
      shift
      ;;
    --push-allowed)
      require_value "$1" "${2:-}"
      REQUESTED_PUSH_ALLOWED="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$TARGET_ROOT_INPUT" ]] || die "--target is required"
[[ -n "$PROJECT_NAME" ]] || die "--project-name is required"
[[ -n "$PROJECT_SLUG" ]] || die "--project-slug is required"
[[ -n "$EXPECTED_REMOTE" ]] || die "--expected-remote is required"
[[ -n "$EXPECTED_BRANCH" ]] || die "--expected-branch is required"
[[ "$PROJECT_SLUG" =~ ^[A-Za-z0-9._-]+$ ]] || die "--project-slug may contain only letters, numbers, dots, underscores, and hyphens"

EXPECTED_REMOTE="$(trim "$EXPECTED_REMOTE")"
EXPECTED_BRANCH="$(trim "$EXPECTED_BRANCH")"
[[ -n "$EXPECTED_REMOTE" ]] || die "--expected-remote must not be blank"
[[ -n "$EXPECTED_BRANCH" ]] || die "--expected-branch must not be blank"

case "$WORKSPACE_TYPE" in
  project_workspace | implementation_repo | test_fixture)
    ;;
  package_repo)
    die "this script initializes project workspaces, not package_repo checkouts"
    ;;
  *)
    die "--workspace-type must be project_workspace, implementation_repo, or test_fixture"
    ;;
esac

case "$REQUESTED_PUSH_ALLOWED" in
  true | false)
    ;;
  *)
    die "--push-allowed must be true or false"
    ;;
esac

if [[ "$WORKSPACE_TYPE" == "test_fixture" && "$REQUESTED_PUSH_ALLOWED" == "true" ]]; then
  die "push_without_repository_lock: test_fixture workspaces must keep PUSH_ALLOWED false"
fi

if [[ "$REQUESTED_PUSH_ALLOWED" == "true" && "$ACCEPT_REPOSITORY_LOCK" != "true" ]]; then
  die "push_without_repository_lock: PUSH_ALLOWED true requires --accept-repository-lock"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -z "$SOURCE_ROOT" ]]; then
  SOURCE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
else
  SOURCE_ROOT="$(canonical_existing_dir "$SOURCE_ROOT")"
fi

TARGET_ROOT="$(canonical_target_path "$TARGET_ROOT_INPUT")"

[[ "$TARGET_ROOT" != "$SOURCE_ROOT" ]] || die "target must not be the package repository root"
[[ "$TARGET_ROOT" != "$SOURCE_ROOT"/* ]] || die "target must not be inside the package repository worktree"

if ! EXPECTED_GIT_REMOTE="$(canonical_remote "$EXPECTED_REMOTE")"; then
  die "expected remote must be an accepted GitHub remote form"
fi

mkdir -p "$TARGET_ROOT"

GIT_TOPLEVEL_ACTUAL="NONE"
ACTUAL_REMOTE="NONE"
ACTUAL_GIT_REMOTE="NONE"
ACTUAL_BRANCH="NONE"
TARGET_HAS_OWN_GIT="false"

if git_toplevel="$(git -C "$TARGET_ROOT" rev-parse --show-toplevel 2>/dev/null)"; then
  GIT_TOPLEVEL_ACTUAL="$(canonical_existing_dir "$git_toplevel")"

  if [[ "$GIT_TOPLEVEL_ACTUAL" != "$TARGET_ROOT" ]]; then
    die "workspace_identity_leakage: target inherits Git worktree from $GIT_TOPLEVEL_ACTUAL"
  fi

  TARGET_HAS_OWN_GIT="true"
  ACTUAL_REMOTE="$(git -C "$TARGET_ROOT" remote get-url origin 2>/dev/null || true)"
  [[ -n "$ACTUAL_REMOTE" ]] || die "repository_identity_mismatch: existing target .git has no origin remote"

  if ! ACTUAL_GIT_REMOTE="$(canonical_remote "$ACTUAL_REMOTE")"; then
    die "repository_identity_mismatch: existing target .git origin is not an accepted GitHub remote form"
  fi

  if [[ "$ACTUAL_GIT_REMOTE" != "$EXPECTED_GIT_REMOTE" ]]; then
    die "repository_identity_mismatch: existing target .git origin $ACTUAL_GIT_REMOTE does not match expected $EXPECTED_GIT_REMOTE"
  fi

  ACTUAL_BRANCH="$(git -C "$TARGET_ROOT" branch --show-current 2>/dev/null || true)"
  [[ -n "$ACTUAL_BRANCH" ]] || die "repository_branch_mismatch: existing target .git is detached or has no current branch"

  if [[ "$ACTUAL_BRANCH" != "$EXPECTED_BRANCH" ]]; then
    die "repository_branch_mismatch: existing target branch $ACTUAL_BRANCH does not match expected $EXPECTED_BRANCH"
  fi
fi

REPOSITORY_LOCK_STATUS="pending"
IDENTITY_VALIDATION_STATUS="blocked"
IDENTITY_VALIDATION_ERROR="repository_lock_missing"
EFFECTIVE_PUSH_ALLOWED="false"

if [[ "$ACCEPT_REPOSITORY_LOCK" == "true" ]]; then
  [[ "$TARGET_HAS_OWN_GIT" == "true" ]] || die "repository_lock_missing: target .git must exist before lock acceptance"
  REPOSITORY_LOCK_STATUS="accepted"
  IDENTITY_VALIDATION_STATUS="passed"
  IDENTITY_VALIDATION_ERROR="NONE"
  EFFECTIVE_PUSH_ALLOWED="$REQUESTED_PUSH_ALLOWED"
fi

if [[ -e "$TARGET_ROOT/project-runtime/WORKSPACE_IDENTITY.md" ]]; then
  die "refusing to overwrite existing workspace identity: $TARGET_ROOT/project-runtime/WORKSPACE_IDENTITY.md"
fi

if [[ -e "$TARGET_ROOT/project-runtime/REPOSITORY_LOCK.md" ]]; then
  die "refusing to overwrite existing repository lock: $TARGET_ROOT/project-runtime/REPOSITORY_LOCK.md"
fi

mkdir -p "$TARGET_ROOT/project-input" "$TARGET_ROOT/project-runtime" "$TARGET_ROOT/project-archive"

copy_agent_system
write_workspace_identity
write_repository_lock

printf 'Initialized workspace: %s\n' "$TARGET_ROOT"
printf 'Workspace identity: %s\n' "$TARGET_ROOT/project-runtime/WORKSPACE_IDENTITY.md"
printf 'Repository lock: %s\n' "$TARGET_ROOT/project-runtime/REPOSITORY_LOCK.md"
printf 'Repository lock status: %s\n' "$REPOSITORY_LOCK_STATUS"
