# FINAL_SMOKE_CHECKLIST

## Purpose

This checklist verifies that the upgraded universal package is internally
consistent at documentation level. It is a smoke fixture for the final auditor;
it is not a deployment checklist and does not require credentials.

## Required package documents exist

Check that each path exists:

```text
agent-system/00_start/ORCHESTRATOR_START.md
agent-system/01_roles/ORCHESTRATOR.md
agent-system/01_roles/REQUIREMENTS_ANALYST.md
agent-system/01_roles/DESIGNER.md
agent-system/01_roles/DEVELOPER.md
agent-system/01_roles/AUDITOR.md
agent-system/01_roles/TESTER.md
agent-system/01_roles/TECHNICAL_WRITER.md
agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md
agent-system/01_roles/RELEASE_MANAGER.md
agent-system/02_runtime/ORCHESTRATOR_RUNTIME_LOOP.md
agent-system/02_runtime/ALLOWED_ORCHESTRATOR_ACTIONS.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
agent-system/02_runtime/AGENT_LIFECYCLE.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/HANDOFF_PROTOCOL.md
agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
agent-system/03_templates/ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
agent-system/03_templates/HANDOFF_TEMPLATE.md
agent-system/03_templates/OWNER_DECISION_TEMPLATE.md
agent-system/03_templates/EVIDENCE_MATRIX_TEMPLATE.md
agent-system/03_templates/FINDINGS_REGISTER_TEMPLATE.md
agent-system/03_templates/SETUP_TASK_TEMPLATE.md
agent-system/03_templates/RUN_SMOKE_CHECKLIST_TEMPLATE.md
agent-system/03_templates/LAUNCH_READINESS_CHECKLIST_TEMPLATE.md
agent-system/03_templates/HANDOVER_CHECKLIST_TEMPLATE.md
agent-system/03_templates/RESEARCH_REQUEST_TEMPLATE.md
agent-system/03_templates/RESEARCH_RESULT_TEMPLATE.md
agent-system/03_templates/DESIGN_CONTINUATION_TASK_TEMPLATE.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
agent-system/04_state/PROJECT_STATE_TEMPLATE.md
agent-system/04_state/CURRENT_GATE_TEMPLATE.md
agent-system/04_state/NEXT_ACTION_TEMPLATE.md
agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
agent-system/05_gap_flow/GAP_FLOW.md
agent-system/05_gap_flow/GAP_REGISTER_TEMPLATE.md
agent-system/06_logs/AGENT_RESULTS_LOG_TEMPLATE.md
agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
agent-system/06_logs/STATUS_SUMMARY_TEMPLATE.md
agent-system/07_lifecycle/PROJECT_LIFECYCLE.md
agent-system/07_lifecycle/BOOTSTRAP_STAGE.md
agent-system/07_lifecycle/REQUIREMENTS_STAGE.md
agent-system/07_lifecycle/DESIGN_STAGE.md
agent-system/07_lifecycle/DESIGN_RESEARCH_LOOP.md
agent-system/07_lifecycle/IMPLEMENTATION_STAGE.md
agent-system/07_lifecycle/TESTING_STAGE.md
agent-system/07_lifecycle/SETUP_STAGE.md
agent-system/07_lifecycle/RUN_STAGE.md
agent-system/07_lifecycle/LAUNCH_STAGE.md
agent-system/07_lifecycle/DOCUMENTATION_STAGE.md
agent-system/07_lifecycle/HANDOVER_STAGE.md
agent-system/08_profiles/PROJECT_PROFILE_SPEC.md
agent-system/08_profiles/generic.md
agent-system/08_profiles/backend_api.md
agent-system/08_profiles/frontend_app.md
agent-system/08_profiles/fullstack_app.md
agent-system/08_profiles/cli_tool.md
agent-system/08_profiles/browser_automation.md
agent-system/08_profiles/data_pipeline.md
agent-system/08_profiles/infra.md
agent-system/08_profiles/parser.md
agent-system/08_profiles/documentation_only.md
agent-system/08_profiles/telegram_bot.md
agent-system/09_validators/VALIDATOR_SPEC.md
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md
agent-system/09_validators/RESEARCH_RETURN_VALIDATION_RULES.md
agent-system/09_validators/REASONING_LEVEL_VALIDATION_RULES.md
agent-system/09_validators/schemas/project_state.schema.json
agent-system/09_validators/schemas/current_gate.schema.json
agent-system/09_validators/schemas/next_action.schema.json
agent-system/09_validators/schemas/task_packet.schema.json
agent-system/09_validators/schemas/result.schema.json
agent-system/09_validators/schemas/task_registry.schema.json
agent-system/09_validators/schemas/accepted_artifacts.schema.json
agent-system/09_validators/schemas/orchestrator_event.schema.json
agent-system/10_examples/MINIMAL_EXAMPLE_FIXTURE.md
agent-system/10_examples/EXPECTED_FLOW_EXAMPLE.md
agent-system/10_examples/FINAL_SMOKE_CHECKLIST.md
agent-system/PACKAGE_VERSIONING.md
agent-system/GOVERNANCE_CHANGELOG.md
agent-system/README.md
```

## Consistency smoke checks

Mark each item pass, fail, blocked, or gap:

```text
VERSION_ALIGNMENT:
  PACKAGE_VERSIONING, README, runtime templates, and schemas use compatible
  package, governance, and runtime schema version fields.

LIFECYCLE_ALIGNMENT:
  PROJECT_LIFECYCLE includes requirements, design, implementation, audit,
  testing, setup, run, launch, documentation, handover, and final acceptance.
  Stage documents exist for documented lifecycle stages where applicable and do
  not contradict the lifecycle order.
  Lifecycle stages are represented by runtime phase/gate enums or by explicit
  documented mappings, and gate evidence requirements do not contradict
  runtime transition rules.

BOOTSTRAP_REQUIREMENTS_ROUTING:
  ORCHESTRATOR_START and BOOTSTRAP_STAGE do not hard-code designer as the only
  first profile agent. They route incomplete, ambiguous, or uncertain input to
  requirements_analyst and allow direct designer routing only for sufficiently
  structured input. Routing examples use current NEXT_ACTION fields:
  ACTION_TYPE, TARGET_ROLE, TASK_ID, TASK_PACKET, DEPENDENCY_STATUS, and
  BLOCKED_BY. The first profile-agent TASK_PACKET is a valid bootstrap task
  packet using the canonical path convention
  project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md, never
  TASK_PACKET: NONE, and never a plain handoff-only file.
  This is the only active task packet exception outside ACTIVE_DOC_ROOT;
  ordinary task packets outside ACTIVE_DOC_ROOT remain invalid, and more than
  one active first bootstrap task packet at the same time is invalid.
  Smoke evidence must explicitly verify all of these bootstrap paths:
  requirements_analyst route is valid for incomplete, ambiguous, or uncertain
  owner input; direct designer route is valid only for sufficiently structured
  owner input; no bootstrap document presents designer as the universal first
  profile agent; BOOTSTRAP_TASK_PACKET_TEMPLATE includes full task packet
  fields and governance boundaries; bootstrap role docs map explicitly to
  agent-system/01_roles/REQUIREMENTS_ANALYST.md and
  agent-system/01_roles/DESIGNER.md instead of lower-case role interpolation.
  BOOTSTRAP_TASK_PACKET_TEMPLATE must not include standalone REQUESTER or
  standalone RESULT-only NEXT_RECOMMENDED_ACTION task-packet fields.

ROLE_ALIGNMENT:
  Role documents keep authority boundaries distinct. Profile agents do not
  audit themselves, run Git checkpoints, or mark whole projects completed.

TASK_RESULT_ALIGNMENT:
  TASK_PACKET_TEMPLATE and AGENT_RESULT_TEMPLATE include the fields required
  by validator rules and schema sidecars.
  TASK_PACKET_TEMPLATE and task_packet.schema.json use the same required field
  set for task identity, lifecycle, role routing, scope, source-of-truth docs,
  dependencies, acceptance criteria, evidence, audit, next-role routing, and
  result format.

RESULT_ACTION_FIELD_ALIGNMENT:
  AGENT_RESULT_TEMPLATE, RESULT_VALIDATION_RULES, runtime loop, and result
  schema require NEXT_RECOMMENDED_ACTION as the canonical RESULT field.
  NEXT_REQUIRED_ACTION appears only as a documented legacy alias and is not
  required by current validators.

STATE_ALIGNMENT:
  runtime state templates, task registry, accepted artifacts registry, logs,
  and transition rules use compatible statuses and routing terms.
  PROJECT_STATE_TEMPLATE, RUNTIME_STATE_SCHEMA, and project_state.schema.json
  all require ACTION_SEMANTIC and SEMANTIC_REASON, and validators cover parity
  for those fields.
  RUNTIME_STATE_SCHEMA, CURRENT_GATE_TEMPLATE, and current_gate.schema.json
  represent the same CURRENT_GATE mandatory fields, including ACTION_SEMANTIC,
  ENTRY_CRITERIA, EXIT_CRITERIA, REQUIRED_NEXT_ROLE, GATE_EVIDENCE,
  BLOCKING_STATUS, and NOTES.
  RUNTIME_STATE_SCHEMA, NEXT_ACTION_TEMPLATE, and next_action.schema.json
  represent the same NEXT_ACTION mandatory fields, including ACTION_SEMANTIC,
  REQUESTER_RETURN_CONTEXT,
  BLOCKING_OR_RESUME_CONTEXT, REQUIRED_UNIVERSAL_DOCS,
  REQUIRED_PROJECT_DOCS, EXPECTED_RESULT, and
  INSTRUCTION_FOR_ORCHESTRATOR.
  Runtime tuple validation explicitly includes CURRENT_GATE.ACTION_SEMANTIC
  and NEXT_ACTION.ACTION_SEMANTIC.

RESEARCH_DEPENDENCY_LOOP:
  REQUESTER_RETURN_PROTOCOL, DESIGN_RESEARCH_LOOP, RESEARCH_REQUEST_TEMPLATE,
  RESEARCH_RESULT_TEMPLATE, DESIGN_CONTINUATION_TASK_TEMPLATE,
  RESEARCH_RETURN_VALIDATION_RULES, task_packet.schema.json,
  result.schema.json, next_action.schema.json, and task_registry.schema.json
  all represent research dependency routing. Smoke evidence must confirm that
  RESEARCH_DEPENDENCY is distinct from GAP and BLOCKER, exact questions and
  allowed/forbidden sources are required, expected evidence/output are
  required, and requester continuation is blocked until independent audit pass.
  Audit fail, blocked, or gap must route to correction/blocked/GAP handling,
  not requester continuation.

REQUESTER_RETURN_PROTOCOL_ALIGNMENT:
  Task packets, task registry entries, and NEXT_ACTION preserve
  REQUESTED_BY_ROLE, REQUESTED_BY_TASK,
  RETURN_TO_REQUESTER_AFTER_AUDIT_PASS,
  RETURN_TO_ROLE_AFTER_AUDIT_PASS, and
  RETURN_TASK_AFTER_AUDIT_PASS where applicable. The orchestrator must not
  infer return targets from informal context.

REASONING_LEVEL_ALIGNMENT:
  Allowed levels are low, default, high, maximum, and role_default. Role
  defaults include tester: high. Task packets may raise reasoning level freely,
  may lower it only for mechanical bounded tasks with OVERRIDE_REASON, and may
  never lower below gate-required floor. Low is forbidden for design,
  requirements, audit, correction after failed audit, lifecycle/state/transition
  changes, security/secrets policy, launch/release readiness, final acceptance,
  and cross-link validation.

RUNTIME_FILE_SET_ALIGNMENT:
  Mandatory runtime file lists in start, runtime loop, runtime state schema,
  orchestrator role loading rules, filesystem governance, validators, and smoke
  checks use this exact required set:
  project-runtime/PROJECT_STATE.md
  project-runtime/CURRENT_GATE.md
  project-runtime/NEXT_ACTION.md
  project-runtime/GAP_REGISTER.md
  project-runtime/AGENT_RESULTS_LOG.md
  project-runtime/TASK_REGISTRY.md
  project-runtime/ACCEPTED_ARTIFACTS.md
  project-runtime/ORCHESTRATOR_EVENTS_LOG.md
  project-runtime/STATUS_SUMMARY.md
  No authoritative current package doc keeps a stale runtime source-of-truth
  list that contains only the first five files in this set.

GATE_RUNTIME_ALIGNMENT:
  CURRENT_GATE template, lifecycle stages, transition rules, setup/run/launch/
  handover templates, and final acceptance wording use compatible gate names,
  owner roles, evidence states, and pass/fail/blocked/gap routing semantics.
  PROJECT_LIFECYCLE documents explicit lifecycle aliases for AUDIT and
  FINAL_ACCEPTANCE when there is no AUDIT_STAGE.md or
  FINAL_ACCEPTANCE_STAGE.md.

PACKAGE_DOCUMENT_COVERAGE:
  Required package document existence checks include mandatory runtime and
  governance docs referenced by start/runtime loading rules, plus previously
  missing package docs such as AGENT_LIFECYCLE, HANDOFF_PROTOCOL,
  ORCHESTRATOR_TASK_HANDOFF_TEMPLATE, DOCUMENTATION_STAGE, and
  CROSS_LINK_VALIDATION_RULES.

CROSS_LINK_ALIGNMENT:
  CROSS_LINK_VALIDATION_RULES exists and is linked from README, VALIDATOR_SPEC,
  and FINAL_SMOKE_CHECKLIST. It verifies role, lifecycle, template, validator,
  runtime, and README links.

PACKAGE_FILE_DEPENDENCY_ALIGNMENT:
  Every package file listed as required or referenced by README,
  VALIDATOR_SPEC, PROJECT_LIFECYCLE, and FINAL_SMOKE_CHECKLIST exists, unless
  the reference is explicitly documented as a runtime file dependency rather
  than a package file.

AUDIT_CHECKPOINT_ALIGNMENT:
  Audit pass is required before accepted-state checkpoint. Audit fail,
  blocked, or gap cannot advance to accepted commit/push state.
  Profile roles with mandatory audit requirements route pass results to
  auditor before any next profile role, lifecycle phase, terminal completion,
  or Git checkpoint. Requirements analyst, devops/setup engineer, and release
  manager pass routing examples are explicitly covered by transition rules.
  Smoke evidence must list each v1.2.0 profile execution role covered by
  mandatory-audit transition rules:
  requirements_analyst, designer, developer, tester, technical_writer,
  devops_setup_engineer, and release_manager.

MINIMAL_FIXTURE_SCHEMA_ALIGNMENT:
  MINIMAL_EXAMPLE_FIXTURE uses the active v1.3.0 runtime tuple, the canonical
  nine runtime file dependencies, current NEXT_ACTION fields, and task packet
  fields compatible with TASK_PACKET_TEMPLATE and task_packet.schema.json.
  Example task packets route outcomes through MANDATORY_WORKFLOW,
  NEXT_ROLE_ON_PASS, NEXT_ROLE_ON_FAIL, NEXT_ROLE_ON_BLOCKED, and
  NEXT_ROLE_ON_GAP, and do not include the RESULT-only
  NEXT_RECOMMENDED_ACTION field.
  It must not depend on deployment, credentials, external repositories, or
  project-specific business terms.

EXAMPLE_FILESYSTEM_GOVERNANCE_ALIGNMENT:
  MINIMAL_EXAMPLE_FIXTURE and EXPECTED_FLOW_EXAMPLE keep profile-agent task
  packet ALLOWED_FILE_CHANGES, EXPECTED_OUTPUTS, CHANGED_FILES, and result
  handoff examples under an active documentation root such as
  project-docs/example/*. They do not allow profile-agent writes to
  runtime-owned paths. project-runtime example paths appear only as
  orchestrator-owned runtime seed, state, or log examples.

PROFILE_AGENT_GIT_AUTHORITY:
  README, POST_AUDIT_GIT_CHECKPOINT, FILESYSTEM_GOVERNANCE, role docs, and
  task packet guidance preserve the rule that profile agents never commit or
  push and task packets cannot grant commit or push authority to profile
  agents. Git checkpoint authority remains orchestrator-owned and audit-pass
  only.

SETUP_RUN_LAUNCH_HANDOVER_ALIGNMENT:
  setup, run/smoke, launch readiness, and handover templates have explicit
  evidence requirements and do not require actual deployment or credentials.

PROFILE_ALIGNMENT:
  profiles are optional extensions and do not replace core governance,
  lifecycle, runtime, validator, or evidence requirements.

NEW_PROFILE_ROLE_PROPAGATION:
  Any new profile role must be represented consistently across role docs, task
  packet types, target roles, runtime state, gate owner roles, result roles,
  and filesystem governance before final smoke can pass.

GAP_OWNER_ALIGNMENT:
  GAP flow and owner decision templates route unresolved decisions to owner
  handling instead of allowing profile agents to decide blocked requirements.

SECRET_SAFETY_ALIGNMENT:
  package docs forbid reading, printing, storing, staging, committing, or
  pushing secret values. Smoke evidence may mention only paths, field names,
  and redacted risk classes.

PROJECT_AGNOSTIC_ALIGNMENT:
  universal core docs remain free of project-specific business implementation
  and named external-platform terminology.

HISTORICAL_PRE_1_2_1_CORRECTION_CHAIN_COVERAGE:
  Historical smoke evidence for the v1.2.0 correction chain must cover
  CORR_ASU_120_017 through
  CORR_ASU_120_021. Coverage must show that bootstrap first profile dispatch
  uses a valid bootstrap task packet protocol; example profile-agent outputs
  stay under an active documentation root and do not allow writes to
  project-runtime; current_gate.schema.json appears in validator and smoke
  sidecar lists; STATUS_SUMMARY sidecar policy is explicit; and
  ACTION_SEMANTIC plus SEMANTIC_REASON have parity across PROJECT_STATE
  template, runtime schema, JSON schema, runtime consistency validation, and
  smoke validation. This historical correction-chain coverage did not install
  v1.2.1 and preserved the rule that profile agents never commit or push.

BOOTSTRAP_ACTIVE_DOC_ROOT_EXCEPTION_SYNC:
  Smoke evidence must verify that the only active task packet exception outside
  ACTIVE_DOC_ROOT is
  project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md for the first
  bootstrap profile-agent dispatch. Ordinary task packets outside
  ACTIVE_DOC_ROOT, handoff files used as task packets, profile-agent dispatch
  without a task packet, and multiple simultaneously active first bootstrap
  task packets are invalid.

VERSIONED_READINESS_SMOKE:
  Final smoke evidence must explicitly verify the bootstrap canonical path
  convention in ORCHESTRATOR_START, BOOTSTRAP_STAGE,
  BOOTSTRAP_TASK_PACKET_TEMPLATE, runtime loop, filesystem governance, state
  transition rules, task packet validation rules, cross-link validation rules,
  and examples. It must verify that the bootstrap exception propagates only to
  the first bootstrap profile-agent task packet and not to ordinary task
  packets, handoff files, or profile-agent dispatch without a task packet.
  Evidence must compare example task packet fields against
  TASK_PACKET_TEMPLATE and schemas/task_packet.schema.json, including
  MANDATORY_WORKFLOW and NEXT_ROLE_ON_* routing fields, and must confirm that
  task packet examples do not include RESULT-only NEXT_RECOMMENDED_ACTION.
  Evidence must also confirm changelog traceability, canonical nine-file
  runtime set stability, active version tuple, and whether the current versioned
  task changes reasoning-level policy.

CHANGELOG_TRACEABILITY_SYNC:
  Governance changelog evidence must explicitly cover CORR_ASU_120_017 through
  CORR_ASU_120_021 and CORR_ASU_120_022 through CORR_ASU_120_026 or the
  current accepted scope of that chain. Coverage must include representative
  affected files, affected invariants, version tuple impact, and
  reasoning-level policy impact for the relevant versioned task.

CORR_ASU_120_027_FINAL_PRE_121_CONSISTENCY_CLEANUP:
  Final smoke evidence must explicitly verify removal of standalone REQUESTER
  and standalone NEXT_RECOMMENDED_ACTION from
  BOOTSTRAP_TASK_PACKET_TEMPLATE, explicit bootstrap role-doc mapping to
  REQUIREMENTS_ANALYST.md and DESIGNER.md, canonical bootstrap placeholder
  project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md plus concrete
  REQUIREMENTS_ANALYST and DESIGNER examples, CURRENT_GATE and NEXT_ACTION
  runtime schema parity with templates and schema sidecars, PROJECT_LIFECYCLE
  AUDIT and FINAL_ACCEPTANCE aliases, CROSS_LINK_VALIDATION_RULES coverage, and
  GOVERNANCE_CHANGELOG traceability for CORR_ASU_120_027.

V1_3_0_VERSION_ALIGNMENT:
  active package tuple is CURRENT_PACKAGE_VERSION: 1.3.0,
  CURRENT_GOVERNANCE_RULESET_VERSION: 1.3.0, and
  CURRENT_RUNTIME_SCHEMA_VERSION: 1.2.0. This feature upgrade must not use
  1.2.1 as the active tuple.
```

## Final smoke evidence format

```text
SMOKE_RESULT:
STATUS: pass | fail | blocked | gap

DOC_EXISTENCE:
- <path>: exists | missing

CONSISTENCY_CHECKS:
- <check id>: pass | fail | blocked | gap
  EVIDENCE: <file references and concise reason>

CROSS_LINK_CHECKS:
- CROSS_LINK_VALIDATION_RULES_LINKED: pass | fail | blocked | gap
  EVIDENCE: README, VALIDATOR_SPEC, and FINAL_SMOKE_CHECKLIST link to
    agent-system/09_validators/CROSS_LINK_VALIDATION_RULES.md.
- PACKAGE_FILE_DEPENDENCIES_EXIST: pass | fail | blocked | gap
  EVIDENCE: Required package file paths referenced by package docs exist, and
    runtime file dependencies use canonical names.

CONTRADICTIONS_FOUND:
- <file refs and contradiction> | NONE

SECRET_SAFETY_CHECK:
- no secret values read or printed;
- no credential files required;
- only path/name/redacted-class checks used.

NEXT_RECOMMENDED_ACTION:
- create final auditor agent or route correction according to orchestrator state.
```
