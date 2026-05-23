# ASO Artifact Package Model P5.1 v3.7.1 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Corrective Scope

P5.1 corrects P5 operational blockers without adding daemon behavior, live
dispatch, checkpoint execution, ASO Studio, product-intake code, distributed
workers, or secret collection.

The correction installs:

- canonical bootstrap task packets using `# TASK PACKET` and
  `TASK_KIND: bootstrap`;
- explicit failure for obsolete `# BOOTSTRAP TASK PACKET`;
- self-contained artifact package directories rooted at `manifest.json`;
- package-relative manifest refs with fail-closed path guards;
- whole-package accept/reject with inventory hashes and rejection reports;
- accepted/superseded active P5 changelog state;
- read-only `aso orchestrator status` and `aso orchestrator next` conveyor
  summaries.

## Compatibility

Runtime Schema remains `3.1.0`. Existing manifest-only P5 candidates must be
repackaged as self-contained package directories before P5.1 validation,
acceptance, or rejection.
