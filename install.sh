#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash install.sh [--python PYTHON] [--venv PATH] [--skip-verify]

Create a local virtual environment, install ASO from this checkout in editable
mode, and verify the installed `aso` command.

Options:
  --python PYTHON   Python executable to use (default: python3)
  --venv PATH       Virtual environment path (default: .venv)
  --skip-verify     Install only; do not run installed ASO verification
  -h, --help        Show this help
EOF
}

python_bin="${PYTHON:-python3}"
venv_dir=".venv"
verify_install=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --python)
      if [ "$#" -lt 2 ]; then
        echo "install.sh: --python requires a value" >&2
        exit 2
      fi
      python_bin="$2"
      shift 2
      ;;
    --venv)
      if [ "$#" -lt 2 ]; then
        echo "install.sh: --venv requires a value" >&2
        exit 2
      fi
      venv_dir="$2"
      shift 2
      ;;
    --skip-verify)
      verify_install=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "install.sh: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

if [ ! -f "pyproject.toml" ] || [ ! -f "agent-system/tools/aso/aso.py" ]; then
  echo "install.sh: run from the agent-system-orchestrator repository root" >&2
  exit 1
fi

"$python_bin" -m venv "$venv_dir"

venv_python="$venv_dir/bin/python"
venv_pip="$venv_dir/bin/pip"
venv_aso="$venv_dir/bin/aso"

if [ ! -x "$venv_python" ] || [ ! -x "$venv_pip" ]; then
  echo "install.sh: virtual environment was not created correctly at $venv_dir" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 "$venv_python" -m pip install --upgrade pip setuptools wheel
PYTHONDONTWRITEBYTECODE=1 "$venv_pip" install -e .

if [ "$verify_install" -eq 1 ]; then
  if [ ! -x "$venv_aso" ]; then
    echo "install.sh: installed aso command not found at $venv_aso" >&2
    exit 1
  fi

  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" --help >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" status --root . --mode package >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" project create --help >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" project verify-clean --help >/dev/null
  project_smoke_dir="$(mktemp -d "${TMPDIR:-/tmp}/aso-install-project-smoke.XXXXXX")"
  trap 'rm -rf "$project_smoke_dir"' EXIT
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" project create --local --target "$project_smoke_dir/project" --name "ASO Install Smoke" --slug "aso-install-smoke" >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" project verify-clean --root "$project_smoke_dir/project" --strict >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" package-layout verify --root . --strict
fi

cat <<EOF
ASO editable install complete.
Activate with: source $venv_dir/bin/activate
Verify with:  make verify-install
EOF
