# STATIC_DASHBOARD_OUTPUT_POLICY

## Purpose

`aso dashboard` renders a static HTML summary of workspace state. It is a
read-only inspection command for state sidecars, planner signals, blockers,
task counts, audit evidence, checkpoint signals, and context-budget metadata
when that metadata is present in state.

## Default behavior

When `--out` is omitted, the command prints the static HTML document to stdout
and writes no files.

```text
python3 agent-system/tools/aso/aso.py dashboard --root /path/to/workspace
```

## Explicit file output

File output must be explicit. `--out` and `--json-out` are accepted only when
the target path resolves under one of these local output roots:

```text
/tmp/...
<workspace>/project-runtime/dashboard/...
```

Package documentation and source paths such as `agent-system/...` are rejected.
The dashboard command may create missing parent directories only inside the
allowed output roots.

## Escaping policy

All text read from workspace state is treated as untrusted. The HTML renderer
escapes rendered values with Python standard-library HTML escaping before
writing them into the document. The dashboard is static HTML and does not
include JavaScript, live polling, a web server, or a remote control surface.
