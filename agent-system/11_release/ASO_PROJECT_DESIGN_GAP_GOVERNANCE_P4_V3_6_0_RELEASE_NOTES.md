# ASO Project Design Gap Governance P4 v3.6.0 Release Notes

## Status

Contract/version boundary placeholder for the corrected P4 package.

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

## Runtime Schema Impact

Runtime Schema remains `3.1.0`. This release does not redefine the P2/P3
runtime sidecar envelope and does not migrate active runtime state.

## Superseded Work

The branch `upgrade/product-intake-capability-p4-v3.6.0` is superseded and
non-authoritative. It must stay untouched and must not be merged as the
authoritative P4 line.

## Deferred Implementation

Later P4 tasks may add role docs, templates, schemas, validators, audit
integration, fixtures, and final validation evidence under their own task
packets. This boundary task does not add product-intake code, daemon mode, live
dispatch, checkpoint execution, external workers, product generation, or secret
collection.
