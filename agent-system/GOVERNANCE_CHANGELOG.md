# GOVERNANCE_CHANGELOG

## Purpose

Append-only bounded changelog for governance, runtime schema, transition, filesystem, and package-version changes.

This document is not a release manifest, result log, evidence store, or artifact index.

## Entry template

```text
CHANGE_ID:
DATE:
PACKAGE_VERSION_BEFORE:
PACKAGE_VERSION_AFTER:
CHANGE_TYPE: patch | minor | major
AFFECTED_FILES:
- 
AFFECTED_INVARIANTS:
- 
AFFECTED_TRANSITIONS:
- 
SCHEMA_TEMPLATE_IMPACT: none | template_update_required | schema_update_required | both
MIGRATION_REQUIRED: yes | no
MIGRATION_NOTE:
AUTHORIZED_BY:
AUDIT_REQUIRED: yes | no
STATUS: proposed | accepted | superseded
```

## Rules

- Add one entry per bounded governance/package change.
- Do not store full audit evidence here.
- Do not store agent RESULT reports here.
- Do not use this document as project runtime state.
- If a change modifies mandatory transitions or schema fields, mark `CHANGE_TYPE: major` unless package policy explicitly defines it as compatible minor hardening.

## Entries

```text
CHANGE_ID: GOV-2026-05-12-001
DATE: 2026-05-12
PACKAGE_VERSION_BEFORE: unversioned
PACKAGE_VERSION_AFTER: 1.0.0
CHANGE_TYPE: major
AFFECTED_FILES:
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/01_roles/ORCHESTRATOR.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
- agent-system/02_runtime/AGENT_LIFECYCLE.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/02_runtime/VIOLATION_RECOVERY.md
- agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/05_gap_flow/GAP_FLOW.md
- agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
- agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
AFFECTED_INVARIANTS:
- one-agent-one-task
- fresh-context execution
- filesystem source-of-truth
- mandatory audit flow
- runtime-state governance
- accepted-state locking
- governance freeze before unsafe dispatch
AFFECTED_TRANSITIONS:
- designer(pass) -> auditor
- developer(pass) -> auditor
- tester(pass) -> technical_writer | orchestrator finalization
- tester(fail) -> developer correction
- technical_writer(pass) -> orchestrator finalization
- invalid runtime state -> correction
- finalization pass -> stop
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Existing runtime states must be checked for AGENT_RESULTS_LOG.md, package/version fields, aligned NEXT_ACTION enums, task packet lifecycle fields, and schema/template parity.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-12-002
DATE: 2026-05-12
PACKAGE_VERSION_BEFORE: 1.0.0
PACKAGE_VERSION_AFTER: 1.1.0
CHANGE_TYPE: minor
AFFECTED_FILES:
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/01_roles/ORCHESTRATOR.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
- agent-system/02_runtime/AGENT_LIFECYCLE.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/02_runtime/VIOLATION_RECOVERY.md
- agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/05_gap_flow/GAP_FLOW.md
- agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
- agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
AFFECTED_INVARIANTS:
- one-agent-one-task
- fresh-context execution
- filesystem source-of-truth
- mandatory audit flow
- deterministic runtime validation
- governance freeze recovery
- runtime-state package/version compatibility
- accepted-state correction metadata
- schema/transition authority separation
AFFECTED_TRANSITIONS:
- governance freeze -> correction | wait_for_owner | governed update_state | governed stop
- governance freeze create_agent -> bounded package-governance correction only
- wait_for_owner/update_state/finalize/stop/correction with TASK_PACKET: NONE -> allowed only when transition rules permit
- RESULT validation -> AGENT_RESULTS_LOG persistence -> STATUS routing
- missing owner bootstrap input -> wait_for_owner/project_owner
- invalid or missing package/runtime/template/governance bootstrap state -> correction/orchestrator
- runtime state tuple mismatch -> correction via STATE_TRANSITION_RULES.md and VIOLATION_RECOVERY.md
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Active package/governance versions changed to 1.1.0 while runtime schema remains 1.0.0; existing runtime states must be checked for package/governance version compatibility, RESULT logging, deterministic NEXT_ACTION routing, and correction metadata compatibility before normal dispatch. No project-runtime files were changed by this package update task set.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted
```
