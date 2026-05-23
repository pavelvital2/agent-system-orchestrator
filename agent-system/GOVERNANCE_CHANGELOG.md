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
CHANGE_SUBTYPE:
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

CHANGE_ID: GOV-2026-05-16-004
CHANGE_TITLE: CORR_ASU_120_016 final linkage smoke coverage
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/README.md
AFFECTED_INVARIANTS:
- final smoke bootstrap routing is not designer-only
- final smoke profile-role audit transition coverage includes all v1.2.0 profile execution roles
- final smoke minimal fixture schema alignment is explicit
- final smoke profile-agent Git authority prohibition is explicit
- cross-link validation covers bootstrap/lifecycle requirements-design routing
- cross-link validation covers profile-role transition sets
- cross-link validation covers minimal fixture/runtime schema/task packet alignment
- cross-link validation covers post-audit Git checkpoint authority against role docs and filesystem governance
- changelog traceability covers files and invariants changed by the final linkage smoke correction
- no next-version feature installation
- no reasoning-level policy change
AFFECTED_TRANSITIONS:
- bootstrap routing -> requirements_analyst for incomplete, ambiguous, or uncertain input
- bootstrap routing -> designer only for sufficiently structured input
- profile agent pass with mandatory audit -> auditor before next profile role, lifecycle phase, terminal completion, or Git checkpoint
- auditor STATUS: pass -> orchestrator-owned post-audit Git checkpoint
- auditor fail, blocked, or gap -> no commit, no push, governed correction or owner routing
- final smoke validation -> final auditor or correction routing
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This correction adds documentation-level smoke and cross-link coverage only. It does not advance the active package, governance ruleset, or runtime schema version, does not install next-version files or features, and does not change reasoning-level policy.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-005
CHANGE_TITLE: CORR_ASU_120_017 through CORR_ASU_120_021 final pre-1.2.1 smoke coverage
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/README.md
AFFECTED_INVARIANTS:
- bootstrap first profile dispatch requires a valid task packet protocol
- example filesystem governance keeps profile-agent outputs out of project-runtime
- current_gate schema sidecar linkage is represented in smoke coverage
- STATUS_SUMMARY sidecar policy is explicit
- PROJECT_STATE semantic fields have template/schema/runtime/validator parity
- profile-agent Git authority remains prohibited
- package version tuple compatibility remains unchanged
- no v1.2.1 installation
- no reasoning-level policy change
AFFECTED_TRANSITIONS:
- bootstrap routing -> first profile-agent task packet validation
- final smoke validation -> final auditor or correction routing
- auditor STATUS: pass -> orchestrator-owned post-audit Git checkpoint
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction records final smoke and changelog traceability for CORR_ASU_120_017 through CORR_ASU_120_021. It adds documentation-level coverage only, does not advance the active package, governance ruleset, or runtime schema version, does not install v1.2.1, and does not change reasoning-level policy.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-006
CHANGE_TITLE: CORR_ASU_120_022 through CORR_ASU_120_026 bootstrap canonicalization traceability sync
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/09_validators/schemas/task_packet.schema.json
- agent-system/09_validators/schemas/result.schema.json
- agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
- agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/README.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/PACKAGE_VERSIONING.md
AFFECTED_INVARIANTS:
- CORR_ASU_120_022: first bootstrap profile-agent dispatch uses canonical task packet path project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
- CORR_ASU_120_023: the only active task packet exception outside ACTIVE_DOC_ROOT is the first bootstrap task packet; ordinary task packets outside ACTIVE_DOC_ROOT remain invalid
- CORR_ASU_120_024: example task packets match task packet template/schema fields and do not use RESULT-only NEXT_RECOMMENDED_ACTION
- CORR_ASU_120_025: governance changelog records correction-chain affected files and invariants for CORR_ASU_120_017 through CORR_ASU_120_026 or the current accepted chain scope
- CORR_ASU_120_026: final pre-1.2.1 smoke covers bootstrap canonical path, bootstrap exception propagation, task packet example/schema parity, changelog traceability, runtime file set stability, version tuple stability, next-version absence, and reasoning-level policy absence
- handoff files are not task packets
- profile agents do not write runtime-owned state paths
- package version tuple compatibility remains unchanged
- no v1.2.1 installation
- no reasoning-level policy change
AFFECTED_TRANSITIONS:
- bootstrap intake -> first profile-agent task packet validation
- first bootstrap task packet -> requirements_analyst or designer only by governed bootstrap routing
- ordinary post-bootstrap task packet validation -> ACTIVE_DOC_ROOT enforcement
- task packet example validation -> correction routing for template/schema mismatches
- final smoke validation -> final auditor or correction routing
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This traceability sync records the current pre-1.2.1 correction chain scope for CORR_ASU_120_022 through CORR_ASU_120_026, together with existing CORR_ASU_120_017 through CORR_ASU_120_021 coverage, without changing active package, governance ruleset, or runtime schema version constants. It does not install v1.2.1 features and does not change reasoning-level policy.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-007
CHANGE_TITLE: CORR_ASU_120_027 final pre-1.2.1 consistency cleanup
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.2.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- bootstrap task packet schema parity excludes standalone REQUESTER and RESULT-only NEXT_RECOMMENDED_ACTION
- bootstrap role documents map explicitly to REQUIREMENTS_ANALYST.md and DESIGNER.md
- bootstrap canonical placeholder remains project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md with concrete REQUIREMENTS_ANALYST and DESIGNER examples
- CURRENT_GATE runtime schema documentation matches template and schema sidecar mandatory fields
- NEXT_ACTION runtime schema documentation matches template and schema sidecar mandatory fields
- PROJECT_LIFECYCLE accounts for AUDIT and FINAL_ACCEPTANCE through explicit aliases without standalone stage documents
- final smoke and cross-link validation cover the corrected pre-1.2.1 consistency checks
- package version tuple compatibility remains unchanged
- no v1.2.1 installation
- no prohibited design-loop or requester-return feature scope, runtime file set change, executable validator, or generalized DAG/parallel orchestration
AFFECTED_TRANSITIONS:
- bootstrap intake -> first profile-agent task packet validation
- current gate validation -> correction routing for schema/template drift
- next action validation -> correction routing for schema/template drift
- lifecycle cross-link validation -> correction routing for unresolved stage aliases
- final smoke validation -> final auditor or correction routing
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction updates documentation parity and smoke coverage only. It preserves the active 1.2.0 package version, 1.2.0 governance ruleset version, and 1.1.0 runtime schema version, and does not install v1.2.1 features.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-16-008
CHANGE_TITLE: UPG_ASU_130_001 research return protocol and reasoning model
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: minor
AFFECTED_FILES:
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/01_roles/ORCHESTRATOR.md
- agent-system/01_roles/DESIGNER.md
- agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md
- agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
- agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
- agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
- agent-system/07_lifecycle/DESIGN_STAGE.md
- agent-system/07_lifecycle/DESIGN_RESEARCH_LOOP.md
- agent-system/09_validators/VALIDATOR_SPEC.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/RESULT_VALIDATION_RULES.md
- agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
- agent-system/09_validators/RESEARCH_RETURN_VALIDATION_RULES.md
- agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
- agent-system/09_validators/schemas/task_packet.schema.json
- agent-system/09_validators/schemas/result.schema.json
- agent-system/09_validators/schemas/next_action.schema.json
- agent-system/09_validators/schemas/task_registry.schema.json
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
AFFECTED_INVARIANTS:
- Research Dependency Loop distinguishes RESEARCH_DEPENDENCY from GAP and BLOCKER.
- Design Research Loop requires designer not to guess when factual evidence is missing.
- Requester Return Protocol requires explicit return metadata and independent audit pass before requester continuation.
- Reasoning level model defines low/default/high/maximum/role_default, role defaults, and gate-required floors.
- Runtime tuple validation explicitly includes CURRENT_GATE.ACTION_SEMANTIC and NEXT_ACTION.ACTION_SEMANTIC.
- Profile agents still never commit or push.
- One-agent-one-task, fresh context, audit gate, and bootstrap canonical path invariants remain unchanged.
AFFECTED_TRANSITIONS:
- requester task -> research_dependency -> research RESULT -> auditor -> audit pass -> requester continuation
- research audit fail/blocked/gap -> correction, blocked/GAP handling, governed update_state, or owner handling; no requester continuation
- designer missing factual evidence -> research_dependency -> audited research -> design_continuation
- reasoning level below gate-required floor -> dispatch blocked and governed correction
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Active package and governance ruleset versions change to 1.3.0 and runtime schema version changes to 1.2.0. Existing runtime state and task registries must be checked for requester return context, task kind, reasoning level fields, task registry return metadata, and ACTION_SEMANTIC tuple parity before normal dispatch. This feature upgrade must not use 1.2.1 as the active tuple.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: superseded
SUPERSEDED_BY: GOV-2026-05-23-001

CHANGE_ID: GOV-2026-05-16-009
CHANGE_TITLE: UPG_ASU_130_002_BOOTSTRAP_V13_CONSISTENCY_FIX
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- stale bootstrap placeholder removed from current normative docs
- bootstrap NEXT_ACTION examples aligned with current runtime schema fields
- requester-return runtime tuple coverage strengthened for NEXT_ACTION.REQUESTER_RETURN_CONTEXT and TASK_REGISTRY.requester_return_metadata
- stale version wording removed from bootstrap and role-set validation text
- canonical bootstrap placeholder and concrete REQUIREMENTS_ANALYST/DESIGNER examples preserved
- requester-return audit gate remains mandatory before requester continuation
- active version tuple remains 1.3.0 / 1.3.0 / 1.2.0
AFFECTED_TRANSITIONS:
- bootstrap intake -> first profile-agent create_agent with complete NEXT_ACTION fields
- runtime tuple validation -> correction routing for missing requester-return context or task registry metadata
- research dependency audit pass -> requester continuation only through explicit return metadata after required audit gate
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction reconciles v1.3.0 bootstrap/runtime documentation consistency only. It does not change active package, governance ruleset, or runtime schema version constants; does not add executable validators or CI; does not change role authority, runtime file set, or generalized orchestration behavior; and does not weaken requester-return audit gating.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: proposed

CHANGE_ID: GOV-2026-05-16-010
CHANGE_TITLE: UPG_ASU_130_003_DISPATCH_REASONING_AND_BOOTSTRAP_SMOKE_FIX
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/01_roles/AUDITOR.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- UPG_ASU_130_002 was invalidated as clean baseline due to reasoning-level dispatch mismatch.
- UPG_ASU_130_002 also left stale bootstrap placeholder references.
- UPG_ASU_130_003 fixes dispatch reasoning enforcement and bootstrap smoke consistency.
- orchestrator must resolve role default, task packet reasoning, gate-required floor, `REASONING_LEVEL_RESOLVED`, requested/configured runner reasoning, and `RUNNER_CONFIG_EVIDENCE` before RESULT routing
- `REASONING_LEVEL_RESOLVED`, `RUNNER_CONFIG_EVIDENCE`, and `REASONING_LEVEL_COMPLIANCE` must be recorded with SPAWN_LOG_REF or HANDOFF_LOG_REF evidence
- requested/configured runner reasoning below `REASONING_LEVEL_RESOLVED` invalidates worker RESULT and forbids auditor pass
- checkpoint, commit, and push are forbidden after reasoning-level mismatch
- auditor must validate reasoning-level execution compliance from task packet, role default, gate floor, and spawn/handoff evidence
- requester-return runtime tuple coverage explicitly includes NEXT_ACTION.REQUESTER_RETURN_CONTEXT and TASK_REGISTRY.requester_return_metadata
- active version tuple remains 1.3.0 / 1.3.0 / 1.2.0
AFFECTED_TRANSITIONS:
- profile-agent create_agent dispatch -> reasoning-level resolution, requested/configured runner reasoning, and runner configuration evidence recording before RESULT routing
- invalid dispatch from requested/configured runner reasoning below `REASONING_LEVEL_RESOLVED` -> governed correction
- invalid reasoning dispatch -> audit fail or blocked, no pass
- reasoning-level mismatch -> no post-audit checkpoint, no commit, no push
- runtime tuple validation -> correction routing when requester return context or requester return metadata is missing or contradictory
SCHEMA_TEMPLATE_IMPACT: template_update_required
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction hardens v1.3.0 dispatch reasoning enforcement, auditor compliance checks, requester-return tuple documentation, final smoke coverage, and changelog traceability only. It preserves the active package, governance ruleset, and runtime schema tuple 1.3.0 / 1.3.0 / 1.2.0; does not add executable validators or CI; does not change the runtime nine-file set, role authority, DAG/parallel orchestration, requester-return audit gate, or version constants.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: proposed

CHANGE_ID: GOV-2026-05-16-011
CHANGE_TITLE: CORR_ASU_130_004_FULL_REMEDIATION
STATUS: accepted
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: patch
TRACEABILITY_SUMMARY: affected files, invariants preserved, and independent audit requirement are recorded in this entry.
AFFECTED_FILES:
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
- agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md
- agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/09_validators/RESULT_VALIDATION_RULES.md
- agent-system/09_validators/RESEARCH_RETURN_VALIDATION_RULES.md
- agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
- agent-system/09_validators/VALIDATOR_SPEC.md
- agent-system/09_validators/schemas/project_state.schema.json
- agent-system/09_validators/schemas/research_result.schema.json
- agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
- agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
DEFECTS_FIXED:
- ASU130-F001: verified stale blank-role bootstrap placeholder absent under agent-system.
- ASU130-F002: bootstrap NEXT_ACTION examples remain aligned with current v1.3.0 fields.
- ASU130-F003: MINIMAL_EXAMPLE_FIXTURE NEXT_ACTION now contains the current required field set.
- ASU130-F004: v1.3.0 correction chain has this accepted closure entry while preserving proposed history for prior entries.
- ASU130-F005 and ASU130-F006: research and design continuation templates are explicit schema-invalid extension sections unless embedded in a full task packet.
- ASU130-F008: active PROJECT_STATE ACTION_SEMANTIC enum now uses completed_state_transition.
- ASU130-F009: research RESULT extension fields are machine-checkable through research_result.schema.json.
- ASU130-F010: missing or unknown reasoning evidence now invalidates auditor pass.
- ASU130-F011: dispatch reasoning metadata uses DISPATCH_TASK_ID, leaving task payload TASK_ID unambiguous.
AFFECTED_INVARIANTS:
- one-agent-one-task and fresh-context execution preserved
- Research Dependency Loop preserved as sequential dependency routing, not GAP/BLOCKER substitution or generalized DAG orchestration
- Requester Return Protocol remains audit-pass gated and explicit-metadata based
- reasoning-level governance remains auditable through required/actual/compliance spawn evidence
- profile agents still cannot commit or push
- orchestrator authority remains limited to routing/state/checkpoint governance and does not design, implement, audit, or test
AFFECTED_TRANSITIONS:
- first bootstrap dispatch -> complete NEXT_ACTION field validation
- research_dependency RESULT -> result.schema.json plus research_result.schema.json validation before audited requester return
- profile-agent dispatch -> reasoning evidence validation before auditor pass acceptance
- finalization semantic update -> completed_state_transition as the active terminal-state semantic
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded remediation preserves the active 1.3.0 / 1.3.0 / 1.2.0 tuple. Existing runtime state that still uses the legacy completed-state semantic must be corrected to completed_state_transition before normal dispatch. Research dependency RESULT validation should apply research_result.schema.json alongside result.schema.json when task context is TASK_KIND: research_dependency.
COMPATIBILITY_NOTE: RESEARCH_REQUEST_TEMPLATE.md and DESIGN_CONTINUATION_TASK_TEMPLATE.md are extension sections only; standalone dispatch remains invalid unless the content is embedded in a full TASK_PACKET_TEMPLATE-compatible packet.
AUDIT_REQUIREMENT: Independent audit is required using TASK_PKG_AUD_ASU_130_004_FULL_REMEDIATION.md before accepted package checkpoint.
RELATION_TO_PRIOR_UPGRADES:
- UPG_ASU_130_001 installed the intended v1.3.0 feature surface but remains historically recorded as proposed in this changelog.
- UPG_ASU_130_002 remains explicitly invalidated as a clean baseline by UPG_ASU_130_003 findings; this entry does not rewrite that history.
- UPG_ASU_130_003 remains historically proposed and is superseded for closure purposes by this full remediation entry.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes

CHANGE_ID: GOV-2026-05-16-012
CHANGE_TITLE: CORR_ASU_130_005_FINAL_BOOTSTRAP_PLACEHOLDER_CLEANUP
STATUS: accepted
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
AFFECTED_INVARIANTS:
- stale blank-role bootstrap placeholder is absent from current agent-system markdown and JSON package docs
- generic bootstrap task packet path convention uses project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
- concrete bootstrap examples remain project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md and project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
- CORR_ASU_130_004 is recorded as incomplete for the stale blank-role bootstrap placeholder finding despite its accepted closure entry
- active version tuple remains 1.3.0 / 1.3.0 / 1.2.0
- no schema, runtime file set, role authority, requester-return audit gate, or reasoning-level policy change
AFFECTED_TRANSITIONS:
- bootstrap intake -> first profile-agent task packet validation through project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
- task packet validation -> correction routing if a blank-role bootstrap placeholder or contradictory canonical bootstrap wording reappears
- final smoke validation -> correction routing if canonical bootstrap path convention or concrete examples regress
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction finalizes residual bootstrap placeholder cleanup only. It preserves the active package, governance ruleset, and runtime schema tuple 1.3.0 / 1.3.0 / 1.2.0 and does not install new package behavior.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes

CHANGE_ID: GOV-2026-05-16-013
CHANGE_TITLE: CORR_ASU_130_006_FINAL_FAIL_CLOSED_REMEDIATION
STATUS: accepted
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 1.3.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
- agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- blank-role bootstrap placeholder is absent from current agent-system package docs
- canonical generic bootstrap path uses project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
- concrete bootstrap examples remain project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md and project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
- checkpoint validation now requires both working-tree and committed HEAD validation before push
- CORR_ASU_130_004 and CORR_ASU_130_005 were incomplete for this residual placeholder defect
- active version tuple remains 1.3.0 / 1.3.0 / 1.2.0
AFFECTED_TRANSITIONS:
- bootstrap intake -> first profile-agent task packet validation through project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
- package invariant validation -> governed correction if a blank-role bootstrap placeholder or contradictory canonical bootstrap wording appears
- auditor STATUS: pass -> post-audit Git checkpoint -> working-tree validation -> commit -> committed HEAD validation -> push
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This bounded correction records the final residual placeholder remediation and hardens checkpoint validation semantics without changing active package, governance ruleset, or runtime schema version constants. It does not change role authority, runtime file set, requester-return audit gating, or reasoning-level policy.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes

CHANGE_ID: GOV-2026-05-16-014
CHANGE_TITLE: CORR_ASU_130_007_FINAL_V13_ACTIVATION_TRACEABILITY
DATE: 2026-05-16
PACKAGE_VERSION_BEFORE: 1.2.0
PACKAGE_VERSION_AFTER: 1.3.0
GOVERNANCE_RULESET_BEFORE: 1.2.0
GOVERNANCE_RULESET_AFTER: 1.3.0
RUNTIME_SCHEMA_BEFORE: 1.1.0
RUNTIME_SCHEMA_AFTER: 1.2.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: release_acceptance
AFFECTED_FILES:
- agent-system/GOVERNANCE_CHANGELOG.md
AFFECTED_INVARIANTS:
- active package/governance/runtime tuple has an accepted v1.3.0 activation record
- UPG_ASU_130_001 remains historically recorded as a proposed implementation entry
- UPG_ASU_130_002 and UPG_ASU_130_003 remain historically recorded as proposed/incomplete correction entries
- CORR_ASU_130_004, CORR_ASU_130_005, and CORR_ASU_130_006 are accepted remediation closure records
- this entry is the accepted release activation record for package/governance v1.3.0 after remediation closure
- active version tuple remains 1.3.0 / 1.3.0 / 1.2.0
- no new runtime behavior, role authority, filesystem authority, or schema behavior is introduced
- merge to main remains forbidden until independent audit pass and post-commit --head / pushed --ref verification pass
AFFECTED_TRANSITIONS:
- final v1.3.0 audit gate -> accepted release activation traceability -> merge readiness review
- missing accepted activation traceability -> governed correction before main merge
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This entry ratifies the installed v1.3.0 package/governance tuple after accepted remediation closure. No runtime migration or active tuple change is introduced by this correction.
TRACEABILITY_NOTE: UPG_ASU_130_001 remains historically proposed as the initial implementation proposal. UPG_ASU_130_002 and UPG_ASU_130_003 remain historically recorded as proposed/incomplete correction entries. This CORR_ASU_130_007 entry is the accepted release activation record for package/governance v1.3.0 after CORR_ASU_130_004, CORR_ASU_130_005, and CORR_ASU_130_006 remediation closure.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-17-001
CHANGE_TITLE: ASO_25_GOVERNANCE_HARDENING_V2_0_0_WORKSPACE_IDENTITY_GATE
DATE: 2026-05-17
PACKAGE_VERSION_BEFORE: 1.3.0
PACKAGE_VERSION_AFTER: 2.0.0
GOVERNANCE_RULESET_BEFORE: 1.3.0
GOVERNANCE_RULESET_AFTER: 2.0.0
RUNTIME_SCHEMA_BEFORE: 1.2.0
RUNTIME_SCHEMA_AFTER: 2.0.0
CHANGE_TYPE: major
AFFECTED_FILES:
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/03_templates/WORKSPACE_IDENTITY_TEMPLATE.md
- agent-system/03_templates/REPOSITORY_LOCK_TEMPLATE.md
- agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md
AFFECTED_INVARIANTS:
- Fix 1: workspace identity gate is mandatory before dispatch, runtime initialization, checkpoint, commit, or push.
- Fix 2: workspace identity manifest/template declares identity, workspace type, expected remote, branch, push policy, allowed identity fields, and version tuple compatibility.
- Fix 3: repository lock defaults PUSH_ALLOWED to false until explicitly accepted and validated.
- Fix 4: package_repo, project_workspace, implementation_repo, and test_fixture behavior are defined.
- Fix 5: wrong remote or wrong branch is a hard blocker for push, and commit requires an explicit governed local-only exception.
- Fix 7: identity leakage across README, runtime, manifest, Git remote, branch, and workspace type is a blocker.
- canonical repository identity comparison is required; raw remote string comparison alone is insufficient.
- SSH host aliases are accepted only when explicitly locked or proven to resolve to github.com.
AFFECTED_TRANSITIONS:
- runtime validation -> workspace identity gate before any dispatchable action.
- profile-agent dispatch -> blocked when repository_identity_mismatch, repository_branch_mismatch, workspace_identity_leakage, or unapproved_ssh_host_alias is active.
- auditor pass -> post-audit checkpoint eligibility still requires workspace identity and repository lock validation.
- checkpoint/commit/push -> blocked unless repository identity, branch, workspace type, and PUSH_ALLOWED policy validate.
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Existing runtime states must add workspace identity, repository lock, and checkpoint eligibility fields before normal dispatch. Missing or contradictory identity fields must route to correction or owner wait; the orchestrator must not infer identity from folder name, copied .git metadata, or raw remote strings.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-17-008
CHANGE_TITLE: ASO_25_GOVERNANCE_HARDENING_V2_0_0_GOVERNANCE_SMOKE_TESTS
DATE: 2026-05-17
PACKAGE_VERSION_BEFORE: 2.0.0
PACKAGE_VERSION_AFTER: 2.0.0
GOVERNANCE_RULESET_BEFORE: 2.0.0
GOVERNANCE_RULESET_AFTER: 2.0.0
RUNTIME_SCHEMA_BEFORE: 2.0.0
RUNTIME_SCHEMA_AFTER: 2.0.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/scripts/checkpoint_preflight.sh
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- tests/fixtures/wrong_remote/*
- tests/fixtures/wrong_branch/*
- tests/fixtures/package_repo_with_project_docs/*
- tests/fixtures/invalid_task_packet/*
- tests/fixtures/push_not_allowed/*
- tests/fixtures/secret_file_present/*
AFFECTED_INVARIANTS:
- TASK_ASO_PATCH_008_GOVERNANCE_SMOKE_TESTS covers Fix 25 with deterministic local smoke fixtures.
- Wrong remote, wrong branch, package/project path pollution, invalid task packet, push without accepted lock, and secret-file exposure are expected blockers.
- Smoke execution uses dry-run preflight checks and temporary local Git repositories; no real network push or real secret material is required.
- Final smoke assertion verifies TOTAL_FIXES: 25 and REQUIRED_COVERAGE: 25/25 from the v2.0.0 coverage matrix.
- Active version tuple remains 2.0.0 / 2.0.0 / 2.0.0.
AFFECTED_TRANSITIONS:
- auditor pass -> checkpoint preflight remains blocked when repository identity, branch, repository lock, file scope, or secret-scan blockers are present.
- invalid task packet -> profile-agent dispatch and checkpoint validation remain blocked.
- package_repo changed files -> project documentation path pollution remains blocked even when a malformed task packet attempts to allow project-docs paths.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Existing runtime states are unaffected by the smoke fixtures. The v2.0.0 workspace identity, repository lock, checkpoint eligibility, task packet validation, and secret-scan migration requirements remain governed by the major package update.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-17-009
CHANGE_TITLE: ASO_CORR_200_001_REPRODUCIBLE_SMOKE_PREFLIGHT_VALIDATION
DATE: 2026-05-17
PACKAGE_VERSION_BEFORE: 2.0.0
PACKAGE_VERSION_AFTER: 2.0.0
GOVERNANCE_RULESET_BEFORE: 2.0.0
GOVERNANCE_RULESET_AFTER: 2.0.0
RUNTIME_SCHEMA_BEFORE: 2.0.0
RUNTIME_SCHEMA_AFTER: 2.0.0
CHANGE_TYPE: patch
AFFECTED_FILES:
- agent-system/scripts/checkpoint_preflight.sh
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/10_examples/ASO_25_GOVERNANCE_HARDENING_COVERAGE_MATRIX.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/00_start/ORCHESTRATOR_START.md
- agent-system/01_roles/AUDITOR.md
- agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- tests/fixtures/approved_ssh_alias/*
AFFECTED_INVARIANTS:
- Smoke is reproducible from tracked repository files and no longer reads project-input/.
- Checkpoint preflight delegates task packet validation to validate_task_packet.py.
- Minimal malformed task packets block checkpoint with invalid_task_packet_schema.
- Owner-approved SSH alias canonicalization is accepted for the package repository.
- Smoke verifies accepted v2.0.0 changelog status.
- Executable shell/Python changes require syntax evidence before auditor pass and checkpoint.
AFFECTED_TRANSITIONS:
- auditor pass -> checkpoint preflight -> full task packet schema validation before git add.
- executable script change -> syntax evidence required before auditor pass and checkpoint eligibility.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: This correction changes reproducible package smoke coverage and checkpoint preflight enforcement only. The active version tuple remains 2.0.0 / 2.0.0 / 2.0.0.
TRACEABILITY_NOTE: Corrects AUDIT_ASO_PATCH_V2_0_0_FAIL_NON_REPRODUCIBLE_SMOKE_AND_PREFLIGHT_VALIDATION_GAP through TASK_ASO_CORR_200_001_REPRODUCIBLE_SMOKE_AND_PREFLIGHT_VALIDATION after mandatory auditor pass and orchestrator-owned checkpoint.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-17-010
CHANGE_TITLE: ASO_CORR_200_002_BOOTSTRAP_CONTINUATION_BASELINE_GATE
DATE: 2026-05-17
PACKAGE_VERSION_BEFORE: 2.0.0
PACKAGE_VERSION_AFTER: 2.0.0
GOVERNANCE_RULESET_BEFORE: 2.0.0
GOVERNANCE_RULESET_AFTER: 2.0.0
RUNTIME_SCHEMA_BEFORE: 2.0.0
RUNTIME_SCHEMA_AFTER: 2.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: correction
AFFECTED_FILES:
- agent-system/01_roles/AUDITOR.md
- agent-system/01_roles/DESIGNER.md
- agent-system/01_roles/ORCHESTRATOR.md
- agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/04_state/CURRENT_GATE_TEMPLATE.md
- agent-system/04_state/NEXT_ACTION_TEMPLATE.md
- agent-system/04_state/PROJECT_STATE_TEMPLATE.md
- agent-system/04_state/RUNTIME_STATE_SCHEMA.md
- agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
- agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
- agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md
- agent-system/scripts/checkpoint_preflight.sh
- agent-system/scripts/init_project_workspace.sh
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/tests/fixtures/*
AFFECTED_INVARIANTS:
- Bootstrap audit/checkpoint acceptance requires a valid downstream task packet, explicit GAP, explicit BLOCKED route, or explicit wait_for_owner route.
- Orchestrator/TASK_PACKET:NONE correction routes cannot create project task packets or project design artifacts.
- Baseline tracking gate blocks untracked critical agent-system/project-runtime baseline paths unless an explicit owner policy records the allowed exception.
- Smoke fixtures are self-contained under agent-system/tests/fixtures and do not depend on top-level tests/fixtures or owner project-input.
- checkpoint_preflight.sh accepts canonical github.com/OWNER/REPO remote fields and reads actual remote, branch, and toplevel from live Git commands.
- Manual preflight descriptions are insufficient checkpoint evidence.
- Active version tuple remains 2.0.0 / 2.0.0 / 2.0.0.
AFFECTED_TRANSITIONS:
- bootstrap audit pass -> blocked when BOOTSTRAP_CONTINUATION_STATUS is missing or invalid.
- first profile-agent dispatch/checkpoint -> blocked on untracked critical baseline without policy exception.
- checkpoint preflight -> live Git actual state is authoritative over cached runtime ACTUAL_* fields.
- checkpoint evidence -> manual preflight references block checkpoint eligibility.
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Existing v2.0.0 project workspaces must track the installed agent-system and critical project-runtime identity/lock/state baseline before normal dispatch/checkpoint, or record an explicit owner policy exception for private project input. Existing cached ACTUAL_* runtime fields remain evidence but are not authoritative for real Git checks.
TRACEABILITY_NOTE: Corrects AUDIT_MARKETS_V2_TEST_RUN_FAIL_BOOTSTRAP_DEAD_END_AND_BASELINE_GOVERNANCE_GAP through TASK_ASO_CORR_200_002_BOOTSTRAP_CONTINUATION_BASELINE_GATE after mandatory auditor pass and orchestrator-owned checkpoint.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-17-011
CHANGE_TITLE: ASO_CORR_200_003_REMOVE_LEGACY_TOP_LEVEL_FIXTURES
DATE: 2026-05-17
PACKAGE_VERSION_BEFORE: 2.0.0
PACKAGE_VERSION_AFTER: 2.0.0
GOVERNANCE_RULESET_BEFORE: 2.0.0
GOVERNANCE_RULESET_AFTER: 2.0.0
RUNTIME_SCHEMA_BEFORE: 2.0.0
RUNTIME_SCHEMA_AFTER: 2.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: correction
SUMMARY:
- Removed legacy top-level tests/fixtures after smoke fixtures were moved under agent-system/tests/fixtures.
- Confirmed governance smoke remains self-contained inside the copied agent-system package.
STATUS: accepted

CHANGE_ID: GOV-2026-05-18-001
CHANGE_TITLE: ASO_CONTROL_PLANE_V3_0_0_RELEASE_CANDIDATE_PACKAGE_MODE_AND_ROOT_RUNTIME_CLEANUP
DATE: 2026-05-18
PACKAGE_VERSION_BEFORE: 2.0.0
PACKAGE_VERSION_AFTER: 3.0.0
GOVERNANCE_RULESET_BEFORE: 2.0.0
GOVERNANCE_RULESET_AFTER: 3.0.0
RUNTIME_SCHEMA_BEFORE: 2.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: major
AFFECTED_FILES:
- README.md
- .gitignore
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/01_roles/SOLUTION_ARCHITECT.md
- agent-system/01_roles/DESIGNER.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md
- agent-system/02_runtime/RUNTIME_FILE_TAXONOMY.md
- agent-system/02_runtime/TRANSACTIONAL_CHECKPOINT_SPEC.md
- agent-system/02_runtime/CANONICAL_JSON_STATE_PREPARATION.md
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/03_templates/TASK_PACKET_TEMPLATE.md
- agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
- agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
- agent-system/09_validators/PRODUCT_CAPABILITY_GATE_POLICY.md
- agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
- agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
- agent-system/09_validators/schemas/task_packet.schema.json
- agent-system/tools/aso/aso.py
- agent-system/tools/aso/commands/package_checks.py
- agent-system/tools/aso/commands/status.py
- agent-system/tools/aso/commands/lint.py
- agent-system/tools/aso/commands/archive_verify.py
- agent-system/tools/aso/tests/test_status.py
- agent-system/tools/aso/tests/test_lint.py
- agent-system/tools/aso/tests/test_archive_verify.py
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/scripts/run_governance_smoke_tests.py
- agent-system/scripts/validate_task_packet.py
- agent-system/tests/test_governance_smoke_runner.py
- agent-system/tests/test_validate_task_packet.py
- agent-system/11_release/ASO_CONTROL_PLANE_V0_RELEASE_CANDIDATE.md
AFFECTED_INVARIANTS:
- Active package, governance ruleset, and runtime schema tuple is 3.0.0 / 3.0.0 / 3.0.0.
- ASO v0 is an experimental read-only helper CLI for status, lint, and archive verify only.
- ASO v0 has explicit package/workspace validation mode and no mutation, dispatch, checkpoint, migration, or repair commands.
- Package repository cleanup policy excludes root generated workspace artifacts from shipped package state.
- Root generated project-runtime, project-input, and project-archive artifacts are not tracked as package state.
- Canonical worker result and audit result paths are package-governed runtime artifact taxonomy.
- Profile-agent lifecycle invariant is one agent = one task = one RESULT = terminate.
- REASONING_LEVEL policy uses low, medium, high, and xhigh.
- solution_architect is the canonical project design role and designer is a deprecated compatibility alias.
- Design output contract and review rubric govern design acceptance.
- Smoke runner hardening remains self-contained, timeout-bounded, and local.
- Transactional checkpoint behavior is specification-only in v0 and does not authorize CLI mutation.
- JSON state migration preparation is documented while Markdown runtime state remains v0-compatible.
- Product capability gate vocabulary separates process pass, capability pass, product pass, MVP readiness, and final acceptance.
AFFECTED_TRANSITIONS:
- package repository validation -> explicit --mode package for ASO status/lint.
- target workspace validation -> explicit --mode workspace for ASO status/lint.
- missing or tracked root generated workspace artifacts in package repository -> package-mode finding or governed cleanup.
- profile-agent dispatch -> one fresh bounded task packet -> one RESULT -> logical termination.
- worker RESULT -> canonical worker result path -> auditor review -> canonical audit result path.
- design task routing -> solution_architect canonical role with designer compatibility alias only.
- checkpoint request in ASO v0 -> rejected as unsupported mutation behavior; checkpoint remains orchestrator-owned specification/policy.
- capability or product readiness claim -> governed by product capability gate vocabulary before MVP or final acceptance claim.
SCHEMA_TEMPLATE_IMPACT: both
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Existing target project workspaces are not automatically cleaned. Root project-runtime/project-input/project-archive are ignored only in the package repository. Target workspaces may continue generating project-runtime as runtime state. Existing v2.0.0 workspaces must install or update agent-system to v3.0.0 before relying on ASO package/workspace mode.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-18-002
CHANGE_TITLE: ASO_V3_0_1_DOCS_EXAMPLES_COHERENCE_PATCH
DATE: 2026-05-18
PACKAGE_VERSION_BEFORE: 3.0.0
PACKAGE_VERSION_AFTER: 3.0.1
GOVERNANCE_RULESET_BEFORE: 3.0.0
GOVERNANCE_RULESET_AFTER: 3.0.1
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: docs_examples_coherence
AFFECTED_FILES:
- .gitignore
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/11_release/ASO_CONTROL_PLANE_V0_RELEASE_CANDIDATE.md
- agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
- agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
- agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
- agent-system/10_examples/PRODUCT_CAPABILITY_GATE_EXAMPLES.md
- agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
- agent-system/01_roles/REQUIREMENTS_ANALYST.md
- agent-system/02_runtime/AGENT_LIFECYCLE.md
- agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
- agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
- agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
- agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md
- agent-system/02_runtime/STATE_TRANSITION_RULES.md
- agent-system/05_gap_flow/GAP_FLOW.md
- agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
- agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
- agent-system/08_profiles/PROJECT_PROFILE_SPEC.md
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/tools/aso/tests/test_archive_verify.py
- agent-system/tools/aso/tests/test_lint.py
AFFECTED_INVARIANTS:
- Active package/governance tuple is 3.0.1 / 3.0.1 while runtime schema remains 3.0.0.
- v3.0.0 release evidence records final released commit, release tag, main release status, and passed whitespace diff check.
- Current examples use `solution_architect` as the canonical design role; `designer` remains only a deprecated alias or historical reference.
- Current examples and smoke-generated task packets use canonical worker and audit result paths.
- Lifecycle completion requires RESULT receipt plus orchestrator-recorded termination event.
- ASO v0 remains read-only and does not add mutation, dispatch, checkpoint, migration, or repair commands.
- Runtime schema sidecars are unchanged by this patch.
AFFECTED_TRANSITIONS:
- profile-agent RESULT receipt -> orchestrator records `agent_result_received` -> orchestrator records `agent_instance_terminated` -> lifecycle completion.
- design task routing -> `solution_architect` canonical role, with `designer` accepted only as deprecated compatibility alias.
- worker/audit RESULT persistence -> canonical `project-runtime/results/worker/` and `project-runtime/results/audit/` paths for new artifacts.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Existing v3.0.0 target workspaces do not require runtime schema migration. They should update package/governance docs and examples to v3.0.1 before using current package coherence checks.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-18-003
CHANGE_TITLE: ASO_STAGE1_EXECUTABLE_CONTROLS_DOCS_CHANGELOG_CLEANUP
DATE: 2026-05-18
PACKAGE_VERSION_BEFORE: 3.0.1
PACKAGE_VERSION_AFTER: 3.0.1
GOVERNANCE_RULESET_BEFORE: 3.0.1
GOVERNANCE_RULESET_AFTER: 3.0.1
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: documentation_release_handoff
AFFECTED_FILES:
- README.md
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/11_release/STAGE1_UPGRADE_VALIDATION_REPORT.md
AFFECTED_INVARIANTS:
- Stage 1 command documentation covers local editable install, direct script compatibility, Make targets, package/workspace doctor, design validation, context-pack validation, CI/smoke expectations, and cleanup/publication boundaries.
- The ASO helper remains read-only and does not add mutation, dispatch, checkpoint, migration, repair, commit, push, or file deletion authority.
- Working upgrade packages and generated runtime/audit artifacts remain outside accepted package publication paths.
- The final validation report is created as a pending tester handoff only and must not claim pass/fail evidence until TASK 007/tester completes real validation.
- Active package/governance/runtime tuple remains 3.0.1 / 3.0.1 / 3.0.0 to stay aligned with pyproject and wrapper metadata within this documentation-only task scope.
AFFECTED_TRANSITIONS:
- Stage 1 documentation cleanup -> independent audit -> orchestrator-owned checkpoint if accepted.
- Stage 1 final validation handoff -> tester completes real command evidence before final acceptance claims.
- local cleanup -> verify no tracked project-input, project-runtime, or project-archive files before publication.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: No runtime schema migration is introduced. The active tuple remains unchanged because this bounded task cannot update pyproject.toml or agent_system_orchestrator_aso.__version__; a future package version bump must update all package metadata in one audited change.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-19-001
CHANGE_TITLE: ASO_STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_VERSION_RELEASE_CLEANUP
DATE: 2026-05-19
PACKAGE_VERSION_BEFORE: 3.0.2
PACKAGE_VERSION_AFTER: 3.1.0
GOVERNANCE_RULESET_BEFORE: 3.0.2
GOVERNANCE_RULESET_AFTER: 3.1.0
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: docs_version_release_cleanup
AFFECTED_FILES:
- README.md
- pyproject.toml
- Makefile
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/10_examples/STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_COMMANDS.md
- agent-system/11_release/STAGE3_SAFE_AUTOMATION_DIAGNOSTICS_RELEASE_NOTES.md
- agent_system_orchestrator_aso/__init__.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.1.0 / 3.1.0 / 3.0.0.
- Stage 3 command surfaces are read-only, dry-run, or proposal-only.
- ASO package-sync verification is a guard for metadata and command surface coherence, not a repair or publishing command.
- Direct script execution remains the compatibility baseline; installed `aso` console-script use is additive after local editable install.
- Root project-input, project-runtime, and project-archive remain local generated or owner-input roots and must not be published as accepted package documentation.
- Stage 1 and Stage 2 release reports remain historical package evidence.
- Stage 3 Task 007 release notes do not claim final validation pass before Task 008 supplies command evidence.
AFFECTED_TRANSITIONS:
- package metadata update -> independent audit -> orchestrator-owned checkpoint only after audit pass.
- package-sync verify -> read-only diagnostic result; no mutation, repair, checkpoint, commit, push, or publication.
- Stage 3 cleanup -> Task 008 final validation evidence before final acceptance can be claimed.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: No runtime schema migration is introduced. Existing v3.0.x workspaces should update the package and governance docs to v3.1.0 before relying on Stage 3 package-sync guard documentation. Runtime schema remains 3.0.0.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: proposed

CHANGE_ID: GOV-2026-05-19-002
CHANGE_TITLE: ASO_STAGE3_DAG_CHECKPOINT_CORRECTION_DOCS_VERSION_WORKFLOW
DATE: 2026-05-19
PACKAGE_VERSION_BEFORE: 3.1.0
PACKAGE_VERSION_AFTER: 3.1.1
GOVERNANCE_RULESET_BEFORE: 3.1.0
GOVERNANCE_RULESET_AFTER: 3.1.1
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: docs_version_workflow_correction
AFFECTED_FILES:
- README.md
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- .github/workflows/stage1-governance.yml
- pyproject.toml
- agent_system_orchestrator_aso/__init__.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.1.1 / 3.1.1 / 3.0.0.
- Stage 3 acceptance is recorded through the DAG checkpoint correction branch and Task 005 validation report, not the earlier proposed v3.1.0 release cleanup entry alone.
- `ASO-STAGE3-AUDIT-BLOCKER-001` is addressed by documenting that `audit_passed` is not a satisfied dependency for downstream readiness.
- Downstream readiness requires `checkpoint_done` with complete checkpoint evidence, or another explicitly completed terminal state allowed by governance.
- Stage 3 command surfaces remain read-only, dry-run, or proposal-only.
- ASO package-sync verification remains a read-only guard for metadata and command surface coherence, not repair, checkpoint, commit, push, or publication authority.
- The workflow display name is package-neutral and no longer labels current governance checks as Stage 1.
- Root project-input, project-runtime, and project-archive remain local generated or owner-input roots and must not be published as accepted package documentation.
- This Task 004 documentation/version update does not claim the final correction pass before Task 005 supplies validation command evidence.
- This changelog entry has exactly one status field, its value is accepted, and adjacent entry status fields are outside this entry boundary.
AFFECTED_TRANSITIONS:
- package metadata correction -> independent audit -> orchestrator-owned checkpoint only after audit pass.
- DAG dependency evaluation -> downstream readiness only after dependency checkpoint completion evidence, not merely `audit_passed`.
- package-sync verify -> read-only diagnostic result; no mutation, repair, checkpoint, commit, push, or publication.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: No runtime schema migration is introduced. Existing v3.1.0 workspaces should update package and governance docs to v3.1.1 before relying on Stage 3 DAG checkpoint dependency documentation. Runtime schema remains 3.0.0.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-20-001
CHANGE_TITLE: ASO_STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_DOCS_VERSION_CHANGELOG
DATE: 2026-05-20
PACKAGE_VERSION_BEFORE: 3.1.1
PACKAGE_VERSION_AFTER: 3.1.2
GOVERNANCE_RULESET_BEFORE: 3.1.1
GOVERNANCE_RULESET_AFTER: 3.1.2
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: pre_main_package_layout_cleanup_docs_version_changelog
AFFECTED_FILES:
- README.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/11_release/STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_VALIDATION_REPORT.md
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.1.2 / 3.1.2 / 3.0.0.
- Canonical installable ASO package source is agent-system/tools/aso/agent_system_orchestrator_aso/.
- Root duplicate package path agent_system_orchestrator_aso/ is absent from tracked package files.
- pyproject.toml package discovery points to agent-system/tools/aso.
- Package-layout verification replaces duplicate copy synchronization for package-source coherence.
- Final validation evidence records VALIDATION_COMMAND_HEAD separately from post-push remote HEAD verification.
- Merge readiness points to 09_MAIN_MERGE_READINESS_PROCEDURE.md or accepted package merge-readiness docs and does not claim a main merge.
AFFECTED_TRANSITIONS:
- pre-main package layout cleanup -> independent audit -> orchestrator-owned checkpoint only after audit pass.
- package-layout verify -> read-only diagnostic result for package-source layout and hygiene.
- validation report -> records command evidence with FINAL_COMMIT_PENDING: yes and REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_PUSH: yes.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: No runtime schema migration is introduced. Existing v3.1.1 workspaces should update package and governance docs to v3.1.2 before relying on pre-main package-layout verification and merge-readiness evidence. Runtime schema remains 3.0.0.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-21-001
CHANGE_TITLE: ASO_PROJECT_FACTORY_P1_GITHUB_WIZARD_DOCS_RELEASE
DATE: 2026-05-21
PACKAGE_VERSION_BEFORE: 3.2.0
PACKAGE_VERSION_AFTER: 3.3.0
GOVERNANCE_RULESET_BEFORE: 3.2.0
GOVERNANCE_RULESET_AFTER: 3.3.0
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.0.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: project_factory_p1_docs_install_release
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/11_release/ASO_PROJECT_FACTORY_P1_V3_3_0_RELEASE_NOTES.md
- agent-system/12_project_factory/PROJECT_FACTORY_P1_SPEC.md
- agent-system/12_project_factory/REFERENCE_ENGINE_MODE_CONTRACT.md
- agent-system/12_project_factory/GITHUB_PUBLISH_CONTRACT.md
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.3.0 / 3.3.0 / 3.0.0.
- Local vendored mode preserves the P0 generated-project behavior and remains bounded to explicit generated-project target paths.
- Local reference mode records the external ASO engine in aso.lock and does not vendor agent-system/.
- GitHub dry-run planning performs no generated-project target writes, Git commands, GitHub CLI calls, network actions, repository creation, commits, or pushes, except for explicit plan output such as --json-out.
- Confirmed GitHub publish requires explicit confirmation, GitHub CLI authentication, exact visibility selection, selected engine mode, clean generated-project verification, and target-scoped Git operations.
- GitHub CLI is optional for install, local creation, local verification, wizard dry-run, and GitHub dry-run planning; it is required only for confirmed publish.
- The wizard exposes the same bounded Project Factory creation and publish planning surface.
- Generated-project publication must not track owner-input roots, runtime roots, archives, caches, logs, virtual environments, local upgrade packages, secret-like files, or ASO engine .git metadata.
- Project Factory P1 does not install a daemon, distributed workers, live agent dispatch, or checkpoint executor.
AFFECTED_TRANSITIONS:
- project factory local creation -> explicit generated-project target path mutation only.
- project factory GitHub dry-run -> deterministic plan only, with no GitHub or Git publish operation.
- project factory confirmed publish -> generated-project clean verification and preflight before target-scoped GitHub publication.
- wizard dry-run -> deterministic plan only; wizard confirmed flow -> same Project Factory safety boundary as the selected command.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: No runtime schema migration is introduced. Existing v3.2.0 generated projects remain compatible where their lockfiles satisfy the accepted compatibility rules. New P1 generated projects record package version 3.3.0 and runtime schema 3.0.0.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-21-002
CHANGE_TITLE: ASO_RUNTIME_STATE_P2_CONTRACT_VERSION_BOUNDARY
DATE: 2026-05-21
PACKAGE_VERSION_BEFORE: 3.3.0
PACKAGE_VERSION_AFTER: 3.4.0
GOVERNANCE_RULESET_BEFORE: 3.3.0
GOVERNANCE_RULESET_AFTER: 3.4.0
RUNTIME_SCHEMA_BEFORE: 3.0.0
RUNTIME_SCHEMA_AFTER: 3.1.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: runtime_state_p2_contract_version_boundary
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/CANONICAL_JSON_STATE.md
- agent-system/02_runtime/RUNTIME_STATE_P2_CONTRACT.md
- agent-system/09_validators/schemas/aso_lock.schema.json
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.4.0 / 3.4.0 / 3.1.0.
- Runtime State P2 sidecars are JSON-first canonical runtime state under project-runtime/state/.
- Markdown runtime views are compatibility and human-readable render outputs for P2+ state.
- P1 generated-project behavior remains compatible for accepted P1/P0 engine tuples: 3.3.0 / 3.0.0 and 3.2.0 / 3.0.0.
- Runtime State P2 does not install daemon, proposal/apply, live dispatch, checkpoint executor, distributed worker, or external queue authority.
AFFECTED_TRANSITIONS:
- state verification -> recognizes runtime schema 3.1.0 as the current P2 target while preserving compatibility diagnostics for older state.
- project factory lockfile validation -> accepts only the governed engine tuples 3.4.0 / 3.1.0, 3.3.0 / 3.0.0, and 3.2.0 / 3.0.0 without granting new publication authority.
SCHEMA_TEMPLATE_IMPACT: schema_update_required
MIGRATION_REQUIRED: yes
MIGRATION_NOTE: Existing runtime schema 3.0.0 workspaces remain compatible but are not silently current P2 state. A later bounded migration task must deterministically convert compatible sidecars to the 3.1.0 envelope. This task defines the contract/version boundary only and does not write active project-runtime state.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-21-003
CHANGE_TITLE: ASO_SAFE_PROPOSAL_APPLY_P3_CONTRACT_VERSION_BOUNDARY
DATE: 2026-05-21
PACKAGE_VERSION_BEFORE: 3.4.0
PACKAGE_VERSION_AFTER: 3.5.0
GOVERNANCE_RULESET_BEFORE: 3.4.0
GOVERNANCE_RULESET_AFTER: 3.5.0
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: proposal_apply_p3_contract_version_boundary
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/PROPOSAL_APPLY_P3_CONTRACT.md
- agent-system/02_runtime/RUNTIME_STATE_P2_CONTRACT.md
- agent-system/09_validators/rules/governance_rules.json
- agent-system/09_validators/schemas/aso_lock.schema.json
- agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
- agent-system/09_validators/schemas/schema_manifest.schema.json
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.5.0 / 3.5.0 / 3.1.0.
- Runtime Schema 3.1.0 remains the canonical sidecar schema for current runtime state.
- Proposal/apply is bounded local runtime-state automation through proposal, review, dry-run, confirmed apply, receipt, and post-apply verification.
- Allowed local runtime artifact roots for P3 are project-runtime/proposals/, project-runtime/receipts/, and project-runtime/reports/.
- P3 does not install a runtime daemon, live agent dispatch, checkpoint executor, commit/push automation, distributed workers, web control panel, or multi-project registry.
- P4 dashboard/control-plane work, P5 queue/dispatcher work, P6 checkpoint executor work, daemon mode, and distributed workers remain deferred.
AFFECTED_TRANSITIONS:
- state verification -> remains the required before/after guard for confirmed apply.
- proposal creation -> may write only proposal artifacts under project-runtime/proposals/.
- confirmed apply -> may write only validated state sidecars, receipts, and reports under allowed project-runtime roots.
- checkpoint proposal -> records eligibility evidence only and does not execute checkpoint, commit, or push actions.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. P3 adds a proposal/apply contract and package/governance version metadata only; it does not silently migrate active project-runtime state or broaden publication authority.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted

CHANGE_ID: GOV-2026-05-22-001
CHANGE_TITLE: ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT_VERSION_BOUNDARY
DATE: 2026-05-22
PACKAGE_VERSION_BEFORE: 3.5.0
PACKAGE_VERSION_AFTER: 3.6.0
GOVERNANCE_RULESET_BEFORE: 3.5.0
GOVERNANCE_RULESET_AFTER: 3.6.0
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_AFTER: 1.0.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: project_design_gap_governance_contract_version_boundary
AFFECTED_FILES:
- README.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/PROJECT_DESIGN_GAP_GOVERNANCE_P4_CONTRACT.md
- agent-system/11_release/ASO_PROJECT_DESIGN_GAP_GOVERNANCE_P4_V3_6_0_RELEASE_NOTES.md
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/aso.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/proposal_contracts.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.6.0 / 3.6.0 / 3.1.0.
- Design/gap governance schema version is 1.0.0.
- ASO remains a deterministic governance/control conveyor and does not replace project designer or requirements analyst reasoning.
- TZ semantic reading and product question authorship remain profile-agent responsibilities, not deterministic ASO code responsibilities.
- Owner-facing questions must be functional, product, UX, interface, visualization, workflow, or business-usage questions in plain language.
- Engineering implementation choices must not be pushed to non-engineer owners.
- Gaps may be immediate blockers, deferred blockers, bounded assumptions, or optional items, but ASO must block crossing the declared blocking stage when required owner input or accepted assumption is missing.
- The branch upgrade/product-intake-capability-p4-v3.6.0 is superseded and non-authoritative but must remain untouched.
- P4 does not install product-intake code, runtime daemon, live dispatch, checkpoint executor, product generation, external workers, or secret collection.
AFFECTED_TRANSITIONS:
- design gap unresolved at blocking stage -> stop dependent transition and route to audited owner question or accepted bounded assumption.
- audited owner question ready -> present exactly one owner question card.
- owner answer recorded -> validate receipt and unblock only the linked stage/gap allowed by policy.
- package metadata update -> independent audit -> orchestrator-owned checkpoint only after audit pass.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. P4 adds governance contract and version metadata for designer-led project design, gap blocking, and owner question policy; it does not migrate active project-runtime state or redefine the P2/P3 runtime sidecar envelope.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: proposed

CHANGE_ID: GOV-2026-05-22-002
CHANGE_TITLE: ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_CONTRACT_VERSION_BOUNDARY
DATE: 2026-05-22
PACKAGE_VERSION_BEFORE: 3.6.0
PACKAGE_VERSION_AFTER: 3.6.1
GOVERNANCE_RULESET_BEFORE: 3.6.0
GOVERNANCE_RULESET_AFTER: 3.6.1
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_AFTER: 1.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: workspace_bootstrap_runtime_lifecycle_hotfix_boundary
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_HOTFIX_CONTRACT.md
- agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_RELEASE_NOTES.md
- agent-system/09_validators/schemas/apply_receipt.schema.json
- agent-system/09_validators/schemas/aso_lock.schema.json
- agent-system/09_validators/schemas/proposal_artifact.schema.json
- agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
- agent-system/09_validators/schemas/schema_manifest.schema.json
- agent-system/tests/fixtures/proposal_apply_p3/valid_workspace/project-runtime/state/PROJECT_STATE.json
- agent-system/tests/fixtures/proposal_apply_p3/valid_workspace/project-runtime/state/SCHEMA_MANIFEST.json
- agent-system/tests/fixtures/state/p2_valid_workspace/project-runtime/state/PROJECT_STATE.json
- agent-system/tests/fixtures/state/p2_valid_workspace/project-runtime/state/SCHEMA_MANIFEST.json
- agent-system/tools/aso/tests/test_lockfile.py
- agent-system/tools/aso/tests/test_packaging.py
- agent-system/tools/aso/tests/test_project.py
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/aso.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/proposal_contracts.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.6.1 / 3.6.1 / 3.1.0.
- Runtime Schema 3.1.0 remains the canonical sidecar schema for current runtime state.
- P4.1 fixes workspace/package mode guard handling, derived runtime Markdown materialization, and lifecycle termination event recording after RESULT/artifact acceptance before audit routing readiness.
- ASO remains a deterministic governance/control conveyor and does not replace project designer or requirements analyst reasoning.
- ASO does not semantically read TZ, infer product capability intent from raw text, or install product-intake code or a product-intake engine.
- P4.1 does not install a daemon, live dispatch, checkpoint executor, product generation, external workers, or secret collection.
- The branch upgrade/product-intake-capability-p4-v3.6.0 is superseded and non-authoritative but must remain untouched.
AFFECTED_TRANSITIONS:
- RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY is the required lifecycle ordering for profile-agent completion before audit routing readiness.
- runtime sidecar verification -> may require deterministic derived Markdown compatibility views without changing canonical JSON authority.
- workspace bootstrap validation -> must not be blocked by package-mode checks unless package mode is explicitly valid for the root.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. P4.1 changes package/governance metadata and hotfix boundary documentation only in this task; it does not migrate active project-runtime state or redefine the P2/P3 runtime sidecar envelope.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: proposed

CHANGE_ID: GOV-2026-05-22-003
CHANGE_TITLE: TASK_ASO_APM5_010_CONTRACT_VERSION_BOUNDARY
DATE: 2026-05-22
PACKAGE_VERSION_BEFORE: 3.6.1
PACKAGE_VERSION_AFTER: 3.7.0
GOVERNANCE_RULESET_BEFORE: 3.6.1
GOVERNANCE_RULESET_AFTER: 3.7.0
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_AFTER: 1.0.0
DESIGN_GAP_GOVERNANCE_SCHEMA_AFTER: 1.0.0
CHANGE_TYPE: minor
CHANGE_SUBTYPE: artifact_package_model_p5_contract_version_boundary
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/ARTIFACT_PACKAGE_MODEL_P5_CONTRACT.md
- agent-system/03_templates/apply_receipt.template.json
- agent-system/03_templates/proposal_artifact.template.json
- agent-system/09_validators/schemas/apply_receipt.schema.json
- agent-system/09_validators/schemas/aso_lock.schema.json
- agent-system/09_validators/schemas/proposal_artifact.schema.json
- agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
- agent-system/09_validators/schemas/schema_manifest.schema.json
- agent-system/scripts/run_governance_smoke_tests.sh
- agent-system/tools/aso/tests/test_lockfile.py
- agent-system/tools/aso/tests/test_packaging.py
- agent-system/tools/aso/tests/test_project.py
- agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/aso.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/lockfile.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/proposal_contracts.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.7.0 / 3.7.0 / 3.1.0.
- Artifact package schema version is 1.0.0.
- Runtime Schema 3.1.0 remains the canonical sidecar schema for current runtime state.
- P5 defines publishable artifact package boundaries without treating project-input, project-runtime, project-archive, or .venv as package artifacts.
- Earlier accepted engine tuples remain compatibility cases for generated-project lockfile validation.
- P5 does not install a daemon, live dispatch, checkpoint executor, product generation, external workers, or secret collection.
AFFECTED_TRANSITIONS:
- package metadata update -> independent audit -> orchestrator-owned checkpoint only after audit pass.
- package artifact validation -> fail closed when workspace-local roots are treated as publishable package artifacts.
SCHEMA_TEMPLATE_IMPACT: metadata_only
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. P5 adds artifact package schema 1.0.0 metadata and package-boundary documentation only; it does not migrate active project-runtime state or redefine the P2/P3 runtime sidecar envelope.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: superseded
SUPERSEDED_BY: GOV-2026-05-23-001

CHANGE_ID: GOV-2026-05-22-004
CHANGE_TITLE: TASK_ASO_APM5_070_LIFECYCLE_EVENTS_RECEIPTS_AND_REPLAY
DATE: 2026-05-22
PACKAGE_VERSION_BEFORE: 3.7.0
PACKAGE_VERSION_AFTER: 3.7.0
GOVERNANCE_RULESET_BEFORE: 3.7.0
GOVERNANCE_RULESET_AFTER: 3.7.0
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_AFTER: 1.0.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: lifecycle_artifact_receipt_ordering
AFFECTED_FILES:
- agent-system/02_runtime/AGENT_LIFECYCLE.md
- agent-system/02_runtime/ARTIFACT_STORAGE_P5_CONTRACT.md
- agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md
- agent-system/09_validators/AGENT_LIFECYCLE_VALIDATION_RULES.md
- agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_INCIDENT_REPLAY_NOTES.md
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/aso.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/artifact.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/lifecycle.py
- agent-system/tools/aso/tests/test_artifact_cli.py
- agent-system/tools/aso/tests/test_lifecycle.py
AFFECTED_INVARIANTS:
- Lifecycle completion after RESULT requires accepted artifact receipt evidence before termination.
- Lifecycle events after RESULT receipt reference accepted artifact ids and artifact acceptance receipt refs.
- AUDIT_ROUTE_READY is a deterministic readiness marker only; it does not dispatch live agents or execute checkpoints.
- No daemon, live dispatch, checkpoint executor, or product-intake engine is added.
AFFECTED_TRANSITIONS:
- RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY is the required lifecycle ordering before audit routing readiness.
- candidate artifact acceptance -> immutable accepted copy plus artifact acceptance receipt plus ARTIFACT_ACCEPTED lifecycle event.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. This patch adds local lifecycle event/receipt integration for existing P5 artifact acceptance and profile-agent completion paths only; it does not migrate active project-runtime state or redefine sidecar schemas.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: superseded
SUPERSEDED_BY: GOV-2026-05-23-001

CHANGE_ID: GOV-2026-05-23-001
CHANGE_TITLE: ASO_ARTIFACT_PACKAGE_MODEL_P5_1_CORRECTIVE_UPGRADE
DATE: 2026-05-23
PACKAGE_VERSION_BEFORE: 3.7.0
PACKAGE_VERSION_AFTER: 3.7.1
GOVERNANCE_RULESET_BEFORE: 3.7.0
GOVERNANCE_RULESET_AFTER: 3.7.1
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_BEFORE: 1.0.0
ARTIFACT_PACKAGE_SCHEMA_AFTER: 1.1.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: artifact_package_model_p5_1_corrective_upgrade
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/ARTIFACT_PACKAGE_MODEL_P5_1_CORRECTION_CONTRACT.md
- agent-system/02_runtime/ORCHESTRATOR_CONVEYOR_PROTOCOL.md
- agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
- agent-system/09_validators/schemas/artifact_package_manifest.schema.json
- agent-system/scripts/validate_task_packet.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/artifact.py
- agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/orchestrator.py
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.7.1 / 3.7.1 / 3.1.0.
- Artifact package schema version is 1.1.0.
- Bootstrap task packets use `# TASK PACKET` with `TASK_KIND: bootstrap`; the obsolete `# BOOTSTRAP TASK PACKET` marker is invalid.
- Artifact package manifests are package-relative and self-contained under the package root directory.
- Artifact accept/reject operates on whole package directories and records inventory hashes.
- Normal orchestrator conveyor flow consumes current ASO status, next-action, validation, and receipt JSON before broad governance rereads.
AFFECTED_TRANSITIONS:
- candidate package validation -> fail closed on absolute, parent traversal, or workspace-root-prefixed payload refs.
- candidate package acceptance -> immutable accepted package directory plus inventory-hash receipt.
- candidate package rejection -> immutable rejected package directory plus rejection report.
SCHEMA_TEMPLATE_IMPACT: artifact_package_manifest_schema_1_1_0
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 is preserved. Existing P5 manifest-only candidates must be repackaged as self-contained directories before P5.1 acceptance or rejection.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted
```

```text
CHANGE_ID: GOV-2026-05-23-002
CHANGE_TITLE: ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_CORRECTION
DATE: 2026-05-23
PACKAGE_VERSION_BEFORE: 3.7.1
PACKAGE_VERSION_AFTER: 3.7.2
GOVERNANCE_RULESET_BEFORE: 3.7.1
GOVERNANCE_RULESET_AFTER: 3.7.2
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_BEFORE: 1.1.0
ARTIFACT_PACKAGE_SCHEMA_AFTER: 1.1.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: bootstrap_state_reconciliation_p5_2_correction
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/02_runtime/BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT.md
- agent-system/02_runtime/CORRECTED_BOOTSTRAP_SEQUENCE_P4_1.md
- agent-system/02_runtime/ORCHESTRATOR_CONVEYOR_PROTOCOL.md
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
- agent-system/11_release/ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_V3_7_2_RELEASE_NOTES.md
- agent-system/11_release/ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_V3_7_2_VALIDATION_REPORT.md
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.7.2 / 3.7.2 / 3.1.0.
- Artifact package schema version remains 1.1.0.
- Runtime Schema 3.1.0 remains the canonical sidecar schema for current runtime state.
- Active/open bootstrap state with mandatory inputs and no completed first dispatch must not route to terminal STOP.
- PROJECT_STATE.TZ_PATH is a project TZ file path and must not be populated with an IANA timezone string.
- Missing derived Markdown runtime views are materialization or repair blockers, not clean PASS evidence.
- Normal orchestrator conveyor flow may consume ASO status/next summaries, but summary contradictions route to recovery or correction.
AFFECTED_TRANSITIONS:
- active/open bootstrap plus terminal stop_terminal -> bootstrap preparation or governed correction.
- missing derived runtime views -> state render/materialization or repairable blocker.
- invalid TZ_PATH -> semantic validation blocker until corrected.
SCHEMA_TEMPLATE_IMPACT: none
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema 3.1.0 and Artifact Package Schema 1.1.0 are preserved. P5.2 changes bootstrap semantic validation, planning, and documentation alignment only; it does not migrate active project-runtime state or redefine the P2/P3 runtime sidecar envelope.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted
```

```text
CHANGE_ID: GOV-2026-05-23-003
CHANGE_TITLE: ASO_BOOTSTRAP_TASK_REGISTRY_ALIGNMENT_P5_3_CORRECTION
DATE: 2026-05-23
PACKAGE_VERSION_BEFORE: 3.7.2
PACKAGE_VERSION_AFTER: 3.7.3
GOVERNANCE_RULESET_BEFORE: 3.7.2
GOVERNANCE_RULESET_AFTER: 3.7.3
RUNTIME_SCHEMA_BEFORE: 3.1.0
RUNTIME_SCHEMA_AFTER: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_BEFORE: 1.1.0
ARTIFACT_PACKAGE_SCHEMA_AFTER: 1.1.0
CHANGE_TYPE: patch
CHANGE_SUBTYPE: bootstrap_task_registry_alignment_p5_3_correction
AFFECTED_FILES:
- README.md
- README_INSTALL.md
- pyproject.toml
- agent-system/README.md
- agent-system/PACKAGE_VERSIONING.md
- agent-system/GOVERNANCE_CHANGELOG.md
- agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
- agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
- agent-system/09_validators/schemas/schema_manifest.schema.json
- agent-system/11_release/ASO_BOOTSTRAP_TASK_REGISTRY_ALIGNMENT_P5_3_V3_7_3_RELEASE_NOTES.md
- agent-system/11_release/ASO_BOOTSTRAP_TASK_REGISTRY_ALIGNMENT_P5_3_V3_7_3_VALIDATION_REPORT.md
AFFECTED_INVARIANTS:
- Active package/governance/runtime tuple is 3.7.3 / 3.7.3 / 3.1.1.
- Artifact package schema version remains 1.1.0.
- TASK_REGISTRY task_kind allows bootstrap for the first bootstrap route and governed bootstrap correction/preparation.
- Unknown task_kind values remain forbidden.
AFFECTED_TRANSITIONS:
- first bootstrap route -> TASK_REGISTRY task_kind bootstrap allowed.
- governed bootstrap correction/preparation -> TASK_REGISTRY task_kind bootstrap allowed.
- unknown task_kind -> forbidden validation/review blocker.
SCHEMA_TEMPLATE_IMPACT: TASK_REGISTRY task-kind documentation and runtime schema manifest metadata aligned; artifact package schema unchanged.
MIGRATION_REQUIRED: no
MIGRATION_NOTE: Runtime Schema metadata advances to 3.1.1 for TASK_REGISTRY task-kind alignment. Artifact Package Schema 1.1.0 is preserved. P5.3 does not migrate active project-runtime state, change artifact package storage semantics, or redefine the orchestrator runtime protocol beyond the governed task-kind contract alignment.
AUTHORIZED_BY: project_owner
AUDIT_REQUIRED: yes
STATUS: accepted
```
