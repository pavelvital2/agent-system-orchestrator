param(
    [string]$Python = $(if ($env:PYTHON) { $env:PYTHON } else { "python" }),
    [string]$Venv = ".venv",
    [switch]$SkipVerify,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    Write-Output @"
Usage: powershell -ExecutionPolicy Bypass -File install.ps1 [-Python PYTHON] [-Venv PATH] [-SkipVerify]

Create a local virtual environment, install ASO from this checkout in editable
mode, and verify the installed aso command.

Options:
  -Python PYTHON   Python executable to use (default: env:PYTHON or python)
  -Venv PATH       Virtual environment path (default: .venv)
  -SkipVerify      Install only; do not run installed ASO verification
  -Help            Show this help
"@
}

if ($Help -or $args -contains "--help" -or $args -contains "/?") {
    Show-Usage
    exit 0
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (!(Test-Path "pyproject.toml") -or !(Test-Path "agent-system/tools/aso/aso.py")) {
    throw "install.ps1: run from the agent-system-orchestrator repository root"
}

& $Python -m venv --system-site-packages $Venv

$VenvPython = Join-Path $Venv "Scripts/python.exe"
$VenvPip = Join-Path $Venv "Scripts/pip.exe"
$VenvAso = Join-Path $Venv "Scripts/aso.exe"

if (!(Test-Path $VenvPython) -or !(Test-Path $VenvPip)) {
    throw "install.ps1: virtual environment was not created correctly at $Venv"
}

& $VenvPython -c @"
import re
import setuptools

match = re.match(r"^(\d+)", setuptools.__version__)
major = int(match.group(1)) if match else 0
if major < 68:
    raise SystemExit(
        "setuptools>=68 is required for local editable install; "
        f"found {setuptools.__version__}"
    )
"@

& $VenvPip install --no-deps --no-build-isolation -e .

if (!$SkipVerify) {
    if (!(Test-Path $VenvAso)) {
        throw "install.ps1: installed aso command not found at $VenvAso"
    }

    $env:PYTHONDONTWRITEBYTECODE = "1"
    & $VenvAso --help | Out-Null
    & $VenvAso status --root . --mode package | Out-Null
    & $VenvAso project create --help | Out-Null
    & $VenvAso project verify-clean --help | Out-Null
    & $VenvAso package-layout verify --root . --strict
}

Write-Output "ASO editable install complete."
Write-Output "Activate with: .\$Venv\Scripts\Activate.ps1"
Write-Output "Verify with:  make verify-install"
