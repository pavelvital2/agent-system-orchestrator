# ASO P57 Documentation and Runtime Authority Cleanup v3.7.8 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.8
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.8
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P57 records the accepted documentation authority and runtime-boundary cleanup
for the active `3.7.8 / 3.7.8 / 3.1.1 / 1.1.0` package tuple.

This release preserves Runtime Schema `3.1.1`, Artifact Package Schema
`1.1.0`, Project Factory P1, the P5.4 planner Dispatchability Gate, installed
real-TZ intake/bootstrap guidance, clean install semantics, and local/remote CI
governance checks. It does not install a runtime migration or a new product
execution surface.

## Accepted P57 Scope

P57 covers these accepted task results:

| Task | Result |
| --- | --- |
| `TASK_ASO_P57_010_GOVERNANCE_DOC_AUTHORITY_SYNC` | active package/governance tuple advanced to `3.7.8 / 3.7.8`; runtime JSON sidecar authority documented |
| `TASK_ASO_P57_020_INSTALL_DOC_SYNC` | install documentation synchronized with clean install and installed real-TZ workflow boundaries |
| `TASK_ASO_P57_030_STATE_RENDER_ALL_SIDECAR_VIEWS` | state render/verify documentation and tests aligned with canonical sidecar rendering |
| `TASK_ASO_P57_040_RUNTIME_TIMESTAMP_POLICY` | confirmed runtime writes documented to use factual UTC timestamps by default |
| `TASK_ASO_P57_050_SOURCE_HYGIENE_EXPANSION` | source contamination guard expanded for generated Python/build artifacts |
| `TASK_ASO_P57_060_CLI_MODE_OMISSION_GUARD` | package/workspace mode omission guard documented and covered |
| `TASK_ASO_P57_070_PACKAGE_SYNC_BOUNDARY_DOCS` | deprecated package-sync alias boundary documented without duplicate package trees |
| `TASK_ASO_P57_080_ORCHESTRATOR_AGENT_GOVERNANCE_HARDENING` | one-agent/one-task lifecycle, reasoning floor, task complexity, and lifecycle policy governance hardened |
| `TASK_ASO_P57_090_RELEASE_VALIDATION_AND_REMOTE_CI_EVIDENCE` | final release notes, local validation report, changelog entry, and post-push remote CI evidence recorded |

## Validation Evidence

Local release validation is recorded in:

```text
agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_VALIDATION_REPORT.md
```

Post-push GitHub Actions evidence for the final pushed HEAD is recorded in:

```text
agent-system/11_release/ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_REMOTE_CI_EVIDENCE.md
```

The remote CI evidence file is a post-push observation. It must not be filled
before the final pushed HEAD has a completed `ASO Package Governance` run with
`CONCLUSION: success`.

## Final Real-TZ Readiness Boundary

P57 documents final real-TZ readiness criteria but does not claim final
real-TZ acceptance. The accepted local smoke target remains
`PYTHONDONTWRITEBYTECODE=1 make e2e-real-tz-smoke`, which validates the
installed real-TZ bootstrap smoke fixture. A final real-TZ acceptance run
against owner-selected live input remains owner-instructed follow-up after P57
merge readiness and remote CI evidence are complete.

## Not Included

- Runtime schema migration.
- Artifact package schema migration.
- Semantic reading of raw TZ content.
- Product-intake engine or product generation.
- Live profile-agent dispatch.
- Checkpoint execution.
- Daemon mode, ASO Studio, external workers, or secret collection.
- Final real-TZ acceptance beyond the required smoke target.
