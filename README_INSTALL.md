# ASO local user install

Run from the repository root:

```text
bash install.sh
```

The installer creates `.venv`, installs this checkout as an editable package,
and verifies the installed `aso` command. It uses local Python packaging only;
it does not require secrets, GitHub credentials, remote repository access,
dispatch authority, checkpoint execution, commit, push, or publication rights.

## Activate

```text
source .venv/bin/activate
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
strict package lint, strict package doctor, and strict package-layout
verification. Package validation still works without `.venv` through direct
script execution:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
```

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

Then use direct script checks, or recreate the environment with `bash
install.sh`. The local `.venv` directory is generated workspace state and must
not be staged, committed, or published.
