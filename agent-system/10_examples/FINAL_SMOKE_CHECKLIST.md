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
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
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
agent-system/09_validators/schemas/project_state.schema.json
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
  structured input. Routing examples use v1.2.0 NEXT_ACTION fields:
  ACTION_TYPE, TARGET_ROLE, TASK_ID, TASK_PACKET, DEPENDENCY_STATUS, and
  BLOCKED_BY.

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
  schema require NEXT_RECOMMENDED_ACTION as the canonical v1.2.0 RESULT field.
  NEXT_REQUIRED_ACTION appears only as a documented legacy alias and is not
  required by v1.2.0 validators.

STATE_ALIGNMENT:
  runtime state templates, task registry, accepted artifacts registry, logs,
  and transition rules use compatible statuses and routing terms.

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

NEXT_VERSION_ABSENCE:
  final smoke and cross-link corrections do not install next-version feature
  docs, fields, roles, runtime enums, or version constants.
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
