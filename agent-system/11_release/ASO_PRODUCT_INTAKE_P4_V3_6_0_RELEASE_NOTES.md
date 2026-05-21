# ASO Product Intake P4 v3.6.0 Release Notes

## Status

Release evidence for the Product Intake P4 package. Final local command
evidence is recorded in
`agent-system/11_release/ASO_PRODUCT_INTAKE_P4_V3_6_0_VALIDATION_REPORT.md`.

## Version Boundary

```text
PACKAGE_VERSION: 3.6.0
GOVERNANCE_RULESET_VERSION: 3.6.0
RUNTIME_SCHEMA_VERSION: 3.1.0
PRODUCT_ARTIFACT_SCHEMA_VERSION: 1.0.0
```

Runtime Schema `3.1.0` remains unchanged.

## Scope

P4 is a planning/intake capability. It may define local product planning
artifacts under governed ignored runtime roots, but it does not execute product
builds, deployments, live integrations, checkpoint execution, commit, push, or
agent dispatch.

## Command Surface

P4 adds the `aso product` command group:

```text
aso product intake
aso product clarify
aso product spec
aso product capabilities
aso product plan
```

The command group converts owner TZ/source material into bounded planning
artifacts:

- `PRODUCT_INTAKE` from local owner input.
- `OPEN_QUESTIONS` and owner decision needs from intake gaps.
- `PRODUCT_SPEC` with explicit assumptions, gaps, and non-goals.
- `CAPABILITY_MATRIX` with traceability and readiness signals.
- `PRODUCT_PLAN` as non-executable planning output.

All commands support dry-run behavior and explicit `--json-out`. Confirmed
workspace writes require `--confirm-write` and are limited to governed ignored
runtime roots such as `project-runtime/product/`, `project-runtime/reports/`,
and permitted render paths.

## Safety Boundary

P4 preserves all accepted P0/P1/P2/P3 behavior. It does not add:

- runtime daemon or live agent dispatch;
- checkpoint executor;
- commit, push, tag, merge, or GitHub publication automation;
- external API calls or live integrations;
- real secret collection;
- product build execution or deployment execution;
- user application source generation;
- web dashboard, GUI, distributed workers, or multi-project registry.

Owner-provided source material remains owner input. Product artifacts may
summarize, normalize, and trace that input for planning, but they must not be
treated as implementation completion or final owner acceptance.

## Compatibility

P4 keeps Runtime Schema `3.1.0` as the active runtime sidecar schema. Existing
P0/P1/P2/P3 generated-project, state, proposal, and apply command boundaries
remain compatible when their accepted publication and runtime-artifact rules
are satisfied. Product artifact schema version `1.0.0` is scoped to P4 product
planning artifacts and does not migrate active project runtime state.

## Validation And Publication

Local validation must run the P4 validation command matrix, including product
help, product dry-run smoke examples, tests, smoke checks, install
verification, strict package lint/doctor/package-layout checks,
checkpoint-preflight, whitespace checks, and publication-boundary checks.

The package repository must not publish owner/runtime roots:

```text
project-input/**
project-runtime/**
project-archive/**
.venv/**
```

After final local validation and before orchestrator checkpoint/publish,
remove the local extracted upgrade package and generated install/cache
artifacts. Remote HEAD equality and GitHub Actions success must be verified
after the orchestrator performs any final commit and push.
