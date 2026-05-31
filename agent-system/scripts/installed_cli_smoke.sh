#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash agent-system/scripts/installed_cli_smoke.sh --aso PATH --package-root PATH --work-dir PATH

Exercise installed ASO console-script command paths against an isolated work
directory. This script is an internal packaging gate; it does not add public CLI
surface.
EOF
}

aso_bin=""
package_root=""
work_dir=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --aso)
      if [ "$#" -lt 2 ]; then
        echo "installed_cli_smoke.sh: --aso requires a value" >&2
        exit 2
      fi
      aso_bin="$2"
      shift 2
      ;;
    --package-root)
      if [ "$#" -lt 2 ]; then
        echo "installed_cli_smoke.sh: --package-root requires a value" >&2
        exit 2
      fi
      package_root="$2"
      shift 2
      ;;
    --work-dir)
      if [ "$#" -lt 2 ]; then
        echo "installed_cli_smoke.sh: --work-dir requires a value" >&2
        exit 2
      fi
      work_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "installed_cli_smoke.sh: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$aso_bin" ] || [ -z "$package_root" ] || [ -z "$work_dir" ]; then
  echo "installed_cli_smoke.sh: --aso, --package-root, and --work-dir are required" >&2
  usage >&2
  exit 2
fi

if [ ! -x "$aso_bin" ]; then
  echo "installed_cli_smoke.sh: installed aso command is not executable: $aso_bin" >&2
  exit 1
fi

package_root="$(cd "$package_root" && pwd)"
mkdir -p "$work_dir"
work_dir="$(cd "$work_dir" && pwd)"

reference_project="$work_dir/reference-project"
vendored_project="$work_dir/vendored-project"
workspace="$work_dir/workspace"

PYTHONDONTWRITEBYTECODE=1 "$aso_bin" --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" status --root "$package_root" --mode package >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" doctor --root "$package_root" --mode package --strict >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" package-layout verify --root "$package_root" --mode package --strict >/dev/null

PYTHONDONTWRITEBYTECODE=1 "$aso_bin" project create \
  --target "$reference_project" \
  --name "ASO Reference Install Smoke" \
  --slug "aso-reference-install-smoke" \
  --engine-mode reference \
  --repo-url none \
  >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" project verify-clean --root "$reference_project" --strict >/dev/null
test ! -e "$reference_project/agent-system"

PYTHONDONTWRITEBYTECODE=1 "$aso_bin" project create \
  --target "$vendored_project" \
  --name "ASO Vendored Install Smoke" \
  --slug "aso-vendored-install-smoke" \
  --engine-mode vendored \
  --repo-url none \
  >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" project verify-clean --root "$vendored_project" --strict >/dev/null

test -f "$vendored_project/agent-system/00_start/ORCHESTRATOR_START.md"
test -f "$vendored_project/agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json"
test -f "$vendored_project/agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json"
test -f "$vendored_project/agent-system/tools/aso/aso.py"
test -d "$vendored_project/agent-system/09_validators"
test ! -e "$vendored_project/agent_system_orchestrator_aso"
test ! -e "$vendored_project/agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system"

for forbidden_name in site-packages .venv venv __pycache__ .pytest_cache .mypy_cache .ruff_cache .tox .nox build dist htmlcov node_modules; do
  if find "$vendored_project" -type d -name "$forbidden_name" -print -quit | grep -q .; then
    echo "installed_cli_smoke.sh: vendored project contains forbidden directory: $forbidden_name" >&2
    exit 1
  fi
done

if find "$vendored_project" -type d -regextype posix-extended -regex '.*/python[0-9]+(\.[0-9]+)?' -print -quit | grep -q .; then
  echo "installed_cli_smoke.sh: vendored project contains Python library version roots" >&2
  exit 1
fi

mkdir -p "$workspace/project-input"
cat >"$workspace/project-input/TZ_REAL.md" <<'EOF'
# TZ

Build a governed install smoke workspace.
EOF

PYTHONDONTWRITEBYTECODE=1 "$aso_bin" state init \
  --root "$workspace" \
  --project-name "ASO Installed State Smoke" \
  --project-slug "aso-installed-state-smoke" \
  --tz project-input/TZ_REAL.md \
  --confirm-write \
  --deterministic-timestamps \
  --json-out "$work_dir/state-init.json" \
  >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" intake bootstrap \
  --root "$workspace" \
  --tz project-input/TZ_REAL.md \
  --target-role requirements_analyst \
  --confirm-write \
  --deterministic-timestamps \
  --json-out "$work_dir/intake-bootstrap.json" \
  >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" state verify \
  --root "$workspace" \
  --strict \
  --json-out "$work_dir/state-verify.json" \
  >/dev/null
PYTHONDONTWRITEBYTECODE=1 "$aso_bin" plan-next \
  --root "$workspace" \
  --strict \
  --json-out "$work_dir/plan-next.json" \
  >/dev/null
for view_name in PROJECT_STATE TASK_REGISTRY NEXT_ACTION CURRENT_GATE WORKSPACE_IDENTITY REPOSITORY_LOCK ACCEPTED_ARTIFACTS CHECKPOINT_STATE SCHEMA_MANIFEST GAP_REGISTER AGENT_RESULTS_LOG ORCHESTRATOR_EVENTS_LOG STATUS_SUMMARY; do
  test -f "$workspace/project-runtime/$view_name.md"
done

echo "ASO installed CLI smoke: passed"
