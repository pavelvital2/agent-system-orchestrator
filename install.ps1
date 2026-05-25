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

& $Python -m venv $Venv

$VenvPython = Join-Path $Venv "Scripts/python.exe"
$VenvPip = Join-Path $Venv "Scripts/pip.exe"
$VenvAso = Join-Path $Venv "Scripts/aso.exe"

if (!(Test-Path $VenvPython) -or !(Test-Path $VenvPip)) {
    throw "install.ps1: virtual environment was not created correctly at $Venv"
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
& $VenvPip install -e .

if (!$SkipVerify) {
    if (!(Test-Path $VenvAso)) {
        throw "install.ps1: installed aso command not found at $VenvAso"
    }

    $env:PYTHONDONTWRITEBYTECODE = "1"
    & $VenvAso --help | Out-Null
    & $VenvAso status --root . --mode package | Out-Null
    & $VenvAso project create --help | Out-Null
    & $VenvAso project verify-clean --help | Out-Null
    $ProjectSmokeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("aso-install-project-smoke-" + [System.Guid]::NewGuid().ToString("N"))
    try {
        & $VenvAso project create --local --target (Join-Path $ProjectSmokeDir "project") --name "ASO Install Smoke" --slug "aso-install-smoke" | Out-Null
        & $VenvAso project verify-clean --root (Join-Path $ProjectSmokeDir "project") --strict | Out-Null
    }
    finally {
        if (Test-Path $ProjectSmokeDir) {
            Remove-Item -Recurse -Force $ProjectSmokeDir
        }
    }
    & $VenvAso package-layout verify --root . --strict
}

Write-Output "ASO editable install complete."
Write-Output "Activate with: .\$Venv\Scripts\Activate.ps1"
Write-Output "Verify with:  make verify-install"
