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
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
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
  Stage documents do not contradict the lifecycle order.

ROLE_ALIGNMENT:
  Role documents keep authority boundaries distinct. Profile agents do not
  audit themselves, run Git checkpoints, or mark whole projects completed.

TASK_RESULT_ALIGNMENT:
  TASK_PACKET_TEMPLATE and AGENT_RESULT_TEMPLATE include the fields required
  by validator rules and schema sidecars.

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
  runtime consistency rules, and smoke checks use this exact required set:
  project-runtime/PROJECT_STATE.md
  project-runtime/CURRENT_GATE.md
  project-runtime/NEXT_ACTION.md
  project-runtime/GAP_REGISTER.md
  project-runtime/AGENT_RESULTS_LOG.md
  project-runtime/TASK_REGISTRY.md
  project-runtime/ACCEPTED_ARTIFACTS.md
  project-runtime/ORCHESTRATOR_EVENTS_LOG.md
  project-runtime/STATUS_SUMMARY.md

AUDIT_CHECKPOINT_ALIGNMENT:
  Audit pass is required before accepted-state checkpoint. Audit fail,
  blocked, or gap cannot advance to accepted commit/push state.

SETUP_RUN_LAUNCH_HANDOVER_ALIGNMENT:
  setup, run/smoke, launch readiness, and handover templates have explicit
  evidence requirements and do not require actual deployment or credentials.

PROFILE_ALIGNMENT:
  profiles are optional extensions and do not replace core governance,
  lifecycle, runtime, validator, or evidence requirements.

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

CONTRADICTIONS_FOUND:
- <file refs and contradiction> | NONE

SECRET_SAFETY_CHECK:
- no secret values read or printed;
- no credential files required;
- only path/name/redacted-class checks used.

NEXT_RECOMMENDED_ACTION:
- create final auditor agent or route correction according to orchestrator state.
```
