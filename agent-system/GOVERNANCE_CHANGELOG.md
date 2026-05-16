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
STATUS: proposed

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
```
