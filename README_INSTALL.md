# ASO local user install

Run from the repository root:

```text
bash install.sh
```

On Windows PowerShell, run from the repository root:

```text
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer creates `.venv`, installs this checkout as an editable package,
and verifies the installed `aso` command. It uses local Python packaging only;
it does not require secrets, GitHub credentials, remote repository access,
dispatch authority, checkpoint execution, commit, push, or publication rights.

This install document covers package version `3.2.0` with runtime schema
`3.0.0`. The schema remains unchanged by Project Factory P0.

Both installers accept a Python executable and virtual environment path:

```text
bash install.sh --python python3 --venv .venv
powershell -ExecutionPolicy Bypass -File install.ps1 -Python python -Venv .venv
```

## Activate

```text
source .venv/bin/activate
aso --help
```

On Windows PowerShell:

```text
.\.venv\Scripts\Activate.ps1
aso --help
```

Direct script execution remains supported without activating the environment:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
```

## Verify

```text
make verify-install
```

The verification target runs the installed `aso` command for package status,
Project Factory command help, strict package lint, strict package doctor, and
strict package-layout verification. Package validation still works without
`.venv` through direct script execution:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
```

Project Factory help should also be available after install:

```text
aso project create --help
aso project verify-clean --help
```

Create and verify a local generated project without secrets or remote access:

```text
aso project create --local --target /tmp/demo-project --name "Demo Project" --slug demo-project --profile generic --repo-url none --branch main
aso project verify-clean --root /tmp/demo-project --strict
```

## Dev Container

When using VS Code Dev Containers, reopen this repository in the container.
The included `.devcontainer/devcontainer.json` uses the Python devcontainer
image and runs `bash install.sh` after creation. It creates only local
workspace state and does not require GitHub credentials, secrets, admin
privileges, commit rights, or publish rights.

## Update

After pulling or receiving new package changes, refresh the editable install:

```text
bash install.sh
make verify-install
```

## Cleanup

Remove the local virtual environment at any time:

```text
rm -rf .venv
```

On Windows PowerShell:

```text
Remove-Item -Recurse -Force .venv
```

Then use direct script checks, or recreate the environment with `bash
install.sh`. The local `.venv` directory is generated workspace state and must
not be staged, committed, or published.
