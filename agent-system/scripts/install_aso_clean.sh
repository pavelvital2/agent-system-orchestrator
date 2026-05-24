#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash agent-system/scripts/install_aso_clean.sh --source PATH --venv PATH [options]

Install ASO from an isolated source snapshot so the live checkout receives no
build, wheel, or egg-info artifacts.

Options:
  --source PATH       ASO source repository root to install from (required)
  --venv PATH         Virtual environment path to create (required)
  --python PYTHON     Python executable for venv creation (default: python3)
  --fresh             Remove and recreate --venv if it already exists
  --reuse-venv        Explicitly allow installing into an existing --venv
  --with-test         Install the supported ASO test extra
  --source-copy PATH  Directory for the isolated source copy (default: mktemp)
  --keep-source       Keep the isolated source copy after install
  --skip-verify       Install only; do not run installed ASO verification
  -h, --help          Show this help
EOF
}

python_bin="${PYTHON:-python3}"
source_root=""
venv_dir=""
source_copy=""
with_test=0
keep_source=0
verify_install=1
fresh_venv=0
reuse_venv=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source)
      if [ "$#" -lt 2 ]; then
        echo "install_aso_clean.sh: --source requires a value" >&2
        exit 2
      fi
      source_root="$2"
      shift 2
      ;;
    --venv)
      if [ "$#" -lt 2 ]; then
        echo "install_aso_clean.sh: --venv requires a value" >&2
        exit 2
      fi
      venv_dir="$2"
      shift 2
      ;;
    --python)
      if [ "$#" -lt 2 ]; then
        echo "install_aso_clean.sh: --python requires a value" >&2
        exit 2
      fi
      python_bin="$2"
      shift 2
      ;;
    --fresh)
      fresh_venv=1
      shift
      ;;
    --reuse-venv)
      reuse_venv=1
      shift
      ;;
    --with-test)
      with_test=1
      shift
      ;;
    --source-copy)
      if [ "$#" -lt 2 ]; then
        echo "install_aso_clean.sh: --source-copy requires a value" >&2
        exit 2
      fi
      source_copy="$2"
      shift 2
      ;;
    --keep-source)
      keep_source=1
      shift
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
      echo "install_aso_clean.sh: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$source_root" ] || [ -z "$venv_dir" ]; then
  echo "install_aso_clean.sh: --source and --venv are required" >&2
  usage >&2
  exit 2
fi

if [ "$fresh_venv" -eq 1 ] && [ "$reuse_venv" -eq 1 ]; then
  echo "install_aso_clean.sh: --fresh and --reuse-venv are mutually exclusive" >&2
  exit 2
fi

source_root="$(cd "$source_root" && pwd)"
venv_parent="$(dirname "$venv_dir")"
mkdir -p "$venv_parent"
venv_dir="$(cd "$venv_parent" && pwd)/$(basename "$venv_dir")"

if [ ! -f "$source_root/pyproject.toml" ] || [ ! -f "$source_root/agent-system/tools/aso/aso.py" ]; then
  echo "install_aso_clean.sh: source is not an agent-system-orchestrator repository root: $source_root" >&2
  exit 1
fi

case "$venv_dir" in
  "$source_root"|"$source_root"/*)
    echo "install_aso_clean.sh: --venv must be outside the source repository for clean-source validation" >&2
    exit 1
    ;;
esac

if [ "$fresh_venv" -eq 1 ]; then
  rm -rf "$venv_dir"
elif [ -e "$venv_dir" ] && [ "$reuse_venv" -eq 0 ]; then
  if [ -d "$venv_dir" ] && [ -z "$(find "$venv_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    :
  else
    echo "install_aso_clean.sh: --venv already exists and is non-empty: $venv_dir" >&2
    echo "install_aso_clean.sh: use --fresh to recreate it or --reuse-venv to reuse it intentionally" >&2
    exit 1
  fi
fi

if ! git -C "$source_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "install_aso_clean.sh: --source must be a git worktree so status can be verified" >&2
  exit 1
fi

repo_top="$(git -C "$source_root" rev-parse --show-toplevel)"
if [ "$repo_top" != "$source_root" ]; then
  echo "install_aso_clean.sh: --source must be the git repository root: $repo_top" >&2
  exit 1
fi

status_before="$(mktemp "${TMPDIR:-/tmp}/aso-clean-install-before.XXXXXX")"
status_after="$(mktemp "${TMPDIR:-/tmp}/aso-clean-install-after.XXXXXX")"
cleanup_paths=("$status_before" "$status_after")

if [ -z "$source_copy" ]; then
  source_copy="$(mktemp -d "${TMPDIR:-/tmp}/aso-clean-install-src.XXXXXX")"
  cleanup_paths+=("$source_copy")
else
  mkdir -p "$(dirname "$source_copy")"
  source_copy_parent="$(cd "$(dirname "$source_copy")" && pwd)"
  source_copy="$source_copy_parent/$(basename "$source_copy")"
  case "$source_copy" in
    "$source_root"|"$source_root"/*)
      echo "install_aso_clean.sh: --source-copy must be outside the source repository" >&2
      exit 1
      ;;
  esac
  if [ -e "$source_copy" ]; then
    echo "install_aso_clean.sh: --source-copy already exists: $source_copy" >&2
    exit 1
  fi
  mkdir -p "$source_copy"
  if [ "$keep_source" -eq 0 ]; then
    cleanup_paths+=("$source_copy")
  fi
fi

cleanup() {
  for path in "${cleanup_paths[@]}"; do
    rm -rf "$path"
  done
}
trap cleanup EXIT

git -C "$source_root" status --short --branch >"$status_before"

git -C "$source_root" archive --format=tar HEAD | tar -x -C "$source_copy"

"$python_bin" -m venv "$venv_dir"

venv_python="$venv_dir/bin/python"
venv_pip="$venv_dir/bin/pip"
venv_aso="$venv_dir/bin/aso"

if [ ! -x "$venv_python" ] || [ ! -x "$venv_pip" ]; then
  echo "install_aso_clean.sh: virtual environment was not created correctly at $venv_dir" >&2
  exit 1
fi

install_spec="$source_copy"
if [ "$with_test" -eq 1 ]; then
  install_spec="$source_copy[test]"
fi

PYTHONDONTWRITEBYTECODE=1 "$venv_python" -m pip install --upgrade pip setuptools wheel
PYTHONDONTWRITEBYTECODE=1 "$venv_pip" install "$install_spec"

if [ "$verify_install" -eq 1 ]; then
  if [ ! -x "$venv_aso" ]; then
    echo "install_aso_clean.sh: installed aso command not found at $venv_aso" >&2
    exit 1
  fi

  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" --help >/dev/null
  PYTHONDONTWRITEBYTECODE=1 "$venv_aso" status --root "$source_root" --mode package >/dev/null
fi

git -C "$source_root" status --short --branch >"$status_after"
if ! diff -u "$status_before" "$status_after"; then
  echo "install_aso_clean.sh: source git status changed during clean install" >&2
  exit 1
fi

cat <<EOF
ASO clean install complete.
Source:       $source_root
Source copy:  $source_copy
Virtual env:  $venv_dir
Activate with: source $venv_dir/bin/activate
EOF
