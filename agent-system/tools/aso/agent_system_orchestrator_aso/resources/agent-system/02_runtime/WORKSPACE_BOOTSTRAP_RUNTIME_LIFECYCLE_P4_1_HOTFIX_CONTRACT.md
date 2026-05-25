# WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT

## Purpose

This document defines the P4.1 hotfix boundary for ASO package version
`3.6.1`, governance ruleset version `3.6.1`, Runtime Schema version `3.1.0`,
and design/gap governance schema version `1.0.0`.

P4.1 is a bounded hotfix to corrected P4. It preserves the P2/P3 Runtime
Schema `3.1.0` sidecar envelope and does not introduce product-intake
automation.

## Hotfix Scope

P4.1 fixes these workflow/runtime issues:

- workspace/package mode guard handling, so package-mode validation does not
  block generated workspace bootstrap;
- runtime Markdown view materialization, where legacy human-readable
  `project-runtime/*.md` compatibility views are derived from canonical JSON
  sidecars under `project-runtime/state/`;
- profile-agent lifecycle termination recording, so accepted artifact receipt
  evidence and a termination event exist after RESULT and before audit routing
  readiness.

The required lifecycle sequence is:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

`ARTIFACT_ACCEPTED`, `AGENT_TERMINATED`, and `AUDIT_ROUTE_READY` events
reference accepted artifact ids and artifact acceptance receipt refs. This is
receipt/order evidence only; it does not add daemon behavior, live dispatch, or
checkpoint execution.

## Authority Boundary

ASO remains a deterministic governance and control conveyor. It validates
mode, process shape, required files, schemas, allowed transitions, derived
runtime views, lifecycle events, receipts, and audit state.

ASO must not:

- semantically interpret raw TZ or owner input as product requirements;
- infer business intent from raw text as deterministic code;
- decide which product capabilities the owner needs;
- replace the project designer or requirements analyst;
- generate owner questions from TZ content by script;
- install product-intake code or a product-intake engine;
- run a daemon;
- dispatch live agents;
- execute checkpoints;
- generate products;
- run external workers or distributed queue infrastructure;
- collect secrets.

Project designer and requirements analyst responsibilities remain unchanged
from corrected P4. They read TZ and owner context by meaning, produce design
artifacts, identify gaps, author owner-facing question cards, and recommend
bounded options. ASO validates and gates the artifacts; it does not perform
the designer's reasoning.

## Runtime Schema Boundary

Runtime Schema remains `3.1.0`. P4.1 changes package/governance metadata,
workflow compatibility rules, and derived-view/lifecycle requirements only. It
does not change the P2/P3 runtime sidecar envelope and does not silently
migrate active `project-runtime/` state.

## Branch Boundary

The branch `upgrade/product-intake-capability-p4-v3.6.0` remains superseded
and non-authoritative. It must not be treated as the active P4 or P4.1 line.
