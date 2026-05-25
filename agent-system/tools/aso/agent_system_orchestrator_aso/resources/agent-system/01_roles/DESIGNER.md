# DESIGNER

## Deprecated Alias

`designer` is a deprecated compatibility alias for the canonical
`solution_architect` role.

New task packets, runtime state, handoffs, and result records must use:

```text
solution_architect
```

Legacy task packets that already use:

```text
designer
```

remain valid through the role alias:

```yaml
ROLE_ALIASES:
  designer: solution_architect
```

Validators must treat `designer` as `solution_architect` for compatibility and
emit a warning instead of a hard failure. This wrapper remains so old
`REQUIRED_DOCS` references to `agent-system/01_roles/DESIGNER.md` do not break.

## Canonical Role Contract

Use the canonical role document for all active design authority:

```text
agent-system/01_roles/SOLUTION_ARCHITECT.md
```

The old name was retired because `designer` can be confused with UI/UX or
graphic design, while this system role owns architecture, contracts, bounded
scope, task DAGs, dispatchable task packets, audit planning, and risk/gap
management.
