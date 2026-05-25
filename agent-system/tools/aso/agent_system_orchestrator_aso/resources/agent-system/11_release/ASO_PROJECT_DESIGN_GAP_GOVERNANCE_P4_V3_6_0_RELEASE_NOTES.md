# ASO Project Design Gap Governance P4 v3.6.0 Release Notes

## Status

Final local release validation completed for the corrected P4 package on
2026-05-22. The validation report is recorded in
`agent-system/11_release/ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_V3_6_0_VALIDATION_REPORT.md`.

## Active Tuple

```text
CURRENT_PACKAGE_VERSION: 3.6.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.6.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P4 installs the corrected designer-led project design and gap governance
contract. ASO remains a deterministic governance/control conveyor: it validates
artifacts, gates transitions, routes audited owner question cards, records
receipts, and preserves process authority.

Semantic product design remains the responsibility of the fresh profile agent
in the project designer or requirements analyst role. ASO must not read TZ by
meaning, replace designer reasoning, generate product questions from TZ, or ask
non-engineer owners to make implementation technology choices.

## Release Scope

This release adds the authoritative P4 contract, role and template alignment,
gap-register and owner-question validation surfaces, design gate verification,
audited owner-question routing, positive and negative design/gap fixtures,
Project Factory documentation alignment, and final release evidence for
corrected P4.

Owner questions are project-designer-authored and auditor-approved. ASO routes
only existing audited cards, asks one owner question at a time, and blocks only
when a gap reaches its declared blocking stage without an accepted answer or
assumption.

## Runtime Schema Impact

Runtime Schema remains `3.1.0`. This release does not redefine the P2/P3
runtime sidecar envelope and does not migrate active runtime state.

## Validation Summary

Final local validation passed for baseline tests, smoke tests, editable install,
installed CLI verification, strict lint/doctor/package-layout/preflight,
state verification, proposal/apply dry-runs, Project Factory reference smoke,
design/gap positive checks, required negative design/gap guards, whitespace
checks, and forbidden-root tracked-file checks.

Validation log directory:

```text
/tmp/aso-dg4-100-validation-20260522-092743/
```

## Superseded Work

The branch `upgrade/product-intake-capability-p4-v3.6.0` is superseded and
non-authoritative. It must stay untouched and must not be merged as the
authoritative P4 line.

## Publication Boundary

No forbidden owner/runtime/archive/venv root is tracked for publication:

```text
git ls-files project-input project-runtime project-archive .venv
```

returned empty during final validation.

The required `bash install.sh` validation created local untracked `.venv/`.
Final cleanup removes local package inputs, `.venv/`, Python bytecode caches,
and egg-info directories before handoff.

## Non-Goals Preserved

This release does not add product-intake code, daemon mode, live dispatch,
checkpoint execution, external workers, product generation, secret collection,
or ASO semantic TZ reading.
