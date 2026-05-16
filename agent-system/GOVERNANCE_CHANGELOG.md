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

CHANGE_ID: GOV-2026-05-15-001
DATE: 2026-05-15
PACKAGE_VERSION_BEFORE: 1.1.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: minor
AFFECTED_FILES:
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/README.md
- README.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/01_roles/REQUIREMENTS_ANALYST.md
- agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md
- agent-system/01_roles/RELEASE_MANAGER.md
- agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
- agent-system/02_runtime/HANDOFF_PROTOCOL.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/03_templates/HANDOFF_TEMPLATE.md
- agent-system/03_templates/OWNER_DECISION_TEMPLATE.md
- agent-system/03_templates/EVIDENCE_MATRIX_TEMPLATE.md
- agent-system/03_templates/FINDINGS_REGISTER_TEMPLATE.md
- agent-system/03_templates/SETUP_TASK_TEMPLATE.md
- agent-system/03_templates/RUN_SMOKE_CHECKLIST_TEMPLATE.md
- agent-system/03_templates/LAUNCH_READINESS_CHECKLIST_TEMPLATE.md
- agent-system/03_templates/HANDOVER_CHECKLIST_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
- agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
- agent-system/05_gap_flow/GAP_FLOW.md
- agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
- agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
- agent-system/06_logs/STATUS_SUMMARY_TEMPLATE.md
- agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
- agent-system/07_lifecycle/REQUIREMENTS_STAGE.md
- agent-system/07_lifecycle/DESIGN_STAGE.md
- agent-system/07_lifecycle/IMPLEMENTATION_STAGE.md
- agent-system/07_lifecycle/TESTING_STAGE.md
- agent-system/07_lifecycle/SETUP_STAGE.md
- agent-system/07_lifecycle/RUN_STAGE.md
- agent-system/07_lifecycle/LAUNCH_STAGE.md
- agent-system/07_lifecycle/HANDOVER_STAGE.md
- agent-system/08_profiles/PROJECT_PROFILE_SPEC.md
- agent-system/08_profiles/generic.md
- agent-system/08_profiles/backend_api.md
- agent-system/08_profiles/frontend_app.md
- agent-system/08_profiles/fullstack_app.md
- agent-system/08_profiles/cli_tool.md
- agent-system/08_profiles/browser_automation.md
- agent-system/08_profiles/data_pipeline.md
- agent-system/08_profiles/infra.md
- agent-system/08_profiles/parser.md
- agent-system/08_profiles/documentation_only.md
- agent-system/08_profiles/telegram_bot.md
- agent-system/09_validators/VALIDATOR_SPEC.md
- agent-system/09_validators/RESULT_VALIDATION_RULES.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
- agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
- agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
AFFECTED_INVARIANTS:
- one-agent-one-task
- fresh-context execution
- filesystem source-of-truth
- task packet and result schema validation
- runtime consistency validation
- accepted artifact and task traceability
- owner decision and GAP routing
- setup, run, launch, handover, and final acceptance gates
- optional project profile extension without replacing core runtime
- post-audit Git checkpoint after audit pass
- no commit or push after audit fail
- package version tuple compatibility
AFFECTED_TRANSITIONS:
- TASK_PACKET -> profile agent -> RESULT -> auditor agent -> AUDIT_RESULT -> post-audit Git checkpoint after audit pass
- audit fail -> no commit, no push, correction task
- blocked -> owner wait or prerequisite task
- gap -> owner decision protocol
- setup gate -> run/smoke gate -> launch readiness gate -> handover gate
- final acceptance requires completed task graph, audit passes, checkpoints, version/changelog/readme consistency, and final smoke evidence
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Active package and governance ruleset versions changed to 1.2.0 and runtime schema version changed to 1.1.0. Existing runtime state must be checked for the active version tuple, lifecycle status, stricter action/state semantics, task/result schema fields, accepted artifacts registry, task registry, orchestrator event log, setup/run/launch/handover gates, project profile selection, and post-audit Git checkpoint state before normal dispatch.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-001
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/README.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/01_roles/ORCHESTRATOR.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
- agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/02_runtime/VIOLATION_RECOVERY.md
- agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/02_runtime/AGENT_LIFECYCLE.md
- agent-system/02_runtime/HANDOFF_PROTOCOL.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
- agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
- agent-system/05_gap_flow/GAP_FLOW.md
- agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
- agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
- agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
- agent-system/06_logs/STATUS_SUMMARY_TEMPLATE.md
- agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
- agent-system/07_lifecycle/DOCUMENTATION_STAGE.md
- agent-system/09_validators/VALIDATOR_SPEC.md
- agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
- agent-system/09_validators/RESULT_VALIDATION_RULES.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
- agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
- agent-system/09_validators/schemas/result.schema.json
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
AFFECTED_INVARIANTS:
- runtime file set synchronization
- role and task enum synchronization
- RESULT next-action field normalization
- documentation stage reconciliation
- final smoke and cross-link validation hardening
- package version tuple compatibility
AFFECTED_TRANSITIONS:
- bootstrap/runtime validation -> correction or wait when mandatory runtime files are missing
- RESULT validation -> AGENT_RESULTS_LOG persistence -> STATUS routing
- documentation stage completion -> handover readiness when required
- final smoke validation -> final auditor or correction routing
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: This correction records completion of the v1.2.0 correction chain without advancing the active tuple. Existing runtime state must be checked against the synchronized nine-file runtime set, updated role/task enums, canonical NEXT_RECOMMENDED_ACTION RESULT field, documentation stage linkage, and final smoke/cross-link checks before normal dispatch.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-002
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/PACKAGE_VERSIONING.md
AFFECTED_INVARIANTS:
- lifecycle/runtime/gate alignment smoke coverage
- runtime file source-of-truth freshness
- task packet template/schema parity
- v1.2.0 correction traceability without new package installation
AFFECTED_TRANSITIONS:
- final smoke validation -> final auditor or correction routing
- cross-link validation -> correction routing for stale runtime lists or template/schema mismatches
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This v1.2.0 consistency correction adds final smoke and cross-link detection coverage only. It does not change active package, governance ruleset, or runtime schema version constants and does not install a new package version.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-003
CHANGE_TITLE: CORR_ASU_120_012 through CORR_ASU_120_016 final blockers correction sync
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/README.md
- agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md
- agent-system/01_roles/RELEASE_MANAGER.md
- agent-system/01_roles/DEVELOPER.md
- agent-system/01_roles/TECHNICAL_WRITER.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- bootstrap requirements/design routing sync
- profile-role audit transition sync
- minimal example fixture schema sync
- profile-agent Git authority hardening
- final smoke/cross-link coverage
- task packets cannot grant commit or push authority to profile agents
- post-audit Git checkpoint remains orchestrator-owned and audit-pass-only
AFFECTED_TRANSITIONS:
- profile agent RESULT -> auditor agent before accepted-state checkpoint
- auditor STATUS: pass -> orchestrator-owned post-audit Git checkpoint
- auditor fail, blocked, or gap -> no commit, no push, governed correction or owner routing
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This v1.2.0 final blockers correction sync hardens Git authority wording and records traceability for CORR_ASU_120_012 through CORR_ASU_120_016 without advancing the active package, governance ruleset, or runtime schema version and without installing v1.2.1 features.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted
```
