# agent-system-orchestrator

Repository for the universal `agent-system/` orchestration package.

Start from:

```text
agent-system/00_start/ORCHESTRATOR_START.md
```

Package documentation is in:

```text
agent-system/README.md
```

The package is a filesystem-governed instruction, template, lifecycle, and validation system for Codex CLI orchestration. It includes an experimental read-only ASO helper CLI at `agent-system/tools/aso/aso.py`.

## Local install and command surface

For local console-script use from this repository:

```text
python3 -m pip install -e .
aso --help
```

Direct script execution remains supported and is the compatibility baseline:

```text
python3 agent-system/tools/aso/aso.py --help
```

Package repository checks use explicit package mode:

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
```

Initialized project workspaces use explicit workspace mode:

```text
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
python3 agent-system/tools/aso/aso.py doctor --root /path/to/project --mode workspace --strict
```

Design and context-pack validators are read-only:

```text
python3 agent-system/tools/aso/aso.py validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
python3 agent-system/tools/aso/aso.py validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict
```

Repeatable root targets:

```text
make install
make test
make smoke
make doctor
make lint
make ci
```

The smoke target includes CLI help, package status, strict package lint,
strict package doctor, valid design/context-pack fixtures, and the local
governance smoke runner. The CI target runs the local test, smoke, doctor,
lint, and whitespace diff checks. CI should use the same local commands and must not
require secrets, network credentials, real remotes, or publishing permissions.

The helper supports read-only status, lint, doctor, design validation, context
pack validation, and archive verify inspection. Its read-only behavior is part
of the ASO v0 boundary. It does not provide mutation, dispatch, or checkpoint
commands.

## Publication boundary

`project-input/`, `project-runtime/`, and `project-archive/` are local
generated or owner-input roots. Working upgrade packages, runtime results,
audit files, scratch notes, command logs, and local Codex artifacts from those
roots must not be published as package documentation. After the accepted Stage
1 flow completes, remove the local upgrade package and verify:

```text
git status --short project-input project-runtime project-archive
git ls-files project-input project-runtime project-archive
```

The expected tracked-file result is empty. Stable release or validation
summaries belong under accepted package paths such as `agent-system/11_release/`.
