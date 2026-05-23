# Valid Stage 1 Design Fixture

## REQUIREMENTS_TRACEABILITY_MATRIX

REQUIREMENT_ID: REQ-001
SOURCE_REF: project-docs/00_project/REQUIREMENTS.md#REQ-001
DESIGN_RESPONSE: Add a read-only package CLI validator for design artifacts.
DOWNSTREAM_ARTIFACTS: TASK_DEV_VALIDATE_DESIGN_001
ACCEPTANCE_LINK: AC-006
STATUS: covered

## MVP_BOUNDARY

IN_SCOPE: Validate one Markdown design artifact using deterministic contract and traceability checks.
OUT_OF_SCOPE: Context-pack validation, design repair, dispatch, checkpoint, and agent generation.
MVP_ACCEPTANCE: AC-006 valid fixture passes and negative fixtures fail.
DEFERRALS: Rich semantic NLP checks are deferred to future bounded validator work.
SOURCE_REFS: project-input/PATCH_ASO_STAGE1_UPGRADE/02_STAGE1_UPGRADE_CONTRACT.md#D3
PRODUCT_CAPABILITY_LEVEL: task_complete
CAPABILITY_SCOPE: AC-006 design validator command surface.
CAPABILITY_ACCEPTANCE_REF: AC-006
CAPABILITY_SOURCE_REF: project-input/PATCH_ASO_STAGE1_UPGRADE/06_ACCEPTANCE_MATRIX.md#AC-006

## NON_GOALS

NON_GOAL_ID: NG-001
DESCRIPTION: Do not mutate or repair the design file.
REASON: Stage 1 commands are read-only.
SOURCE_OR_DECISION_REF: DEC-001
IMPACT_ON_TASKS: Downstream work emits findings only.

## ASSUMPTIONS_REGISTER

ASSUMPTION_ID: ASM-001
STATEMENT: Fixture paths are available inside the package repository.
BASIS: Test fixture ownership is explicit in the task packet.
IMPACT: Tests can use local fixture paths.
VALIDATION_PATH: implementation_check
EXPIRY_OR_REVIEW_TRIGGER: Fixture path ownership changes.

## GAP_REGISTER_UPDATES

GAP_ID: NONE
TYPE: none
STATUS: resolved
BLOCKS: NONE
QUESTION_TO_OWNER: NONE
RECOMMENDED_OPTIONS: NONE
RECOMMENDED_OPTION: NONE
REASON: No owner decision is required for this bounded fixture.
TARGET_REGISTER: NONE

## ARCHITECTURE_DECISIONS

DECISION_ID: DEC-001
DECISION: Implement validation as a read-only Markdown inspection command.
SOURCE_REFS: project-input/PATCH_ASO_STAGE1_UPGRADE/02_STAGE1_UPGRADE_CONTRACT.md#D3 agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
OPTIONS_CONSIDERED: Reuse lint; add focused validate-design command.
RATIONALE: The contract requires design-specific checks and JSON output.
CONSEQUENCES: Findings use deterministic rule IDs and the command exits nonzero on errors.
ASSUMPTION_REFS: ASM-001
GAP_REFS: NONE
RESEARCH_DEPENDENCY_REFS: NONE
TASK_REFS: TASK_DEV_VALIDATE_DESIGN_001
STATUS: accepted

## MODULE_CONTRACTS

MODULE_ID: MOD-001
PURPOSE: ASO validate-design command module.
OWNED_BEHAVIOR: Read a Markdown design and emit text or JSON findings.
PUBLIC_INTERFACE: aso validate-design DESIGN.md --root . --strict --json-out PATH
DEPENDENCIES: agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/parsers/markdown_design.py agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/rules/design.py
INPUTS: DESIGN.md
OUTPUTS: process exit code, stdout summary, optional JSON report.
ERROR_HANDLING: Unreadable input returns DESIGN_IO_001.
FILES_OR_PATHS: agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/validate_design.py
TASK_REFS: TASK_DEV_VALIDATE_DESIGN_001
SOURCE_REFS: DEC-001

## DATA_CONTRACTS

DATA_CONTRACT_ID: DATA-001
ENTITY_OR_PAYLOAD: validate-design JSON report.
FIELDS: tool, command, status, root, path, strict, summary, findings, design, rubric.
VALIDATION_RULES: Findings include deterministic rule_id, severity, path, section, and recommendation.
LIFECYCLE_OR_STATE_RULES: Report is output only and does not change runtime state.
READERS: CLI users and tests.
WRITERS: validate-design command only when --json-out is requested.
BACKWARD_COMPATIBILITY: Direct script invocation remains supported.
SECURITY_OR_PRIVACY_NOTES: No secrets are read beyond the provided design file and package docs.
SOURCE_REFS: agent-system/09_validators/DESIGN_REVIEW_RUBRIC.md
TASK_REFS: TASK_DEV_VALIDATE_DESIGN_001

## RUNTIME_MODEL

ENTRYPOINTS: python3 agent-system/tools/aso/aso.py validate-design DESIGN.md --root .
PROCESS_MODEL: Single local process, read-only inspection.
CONFIGURATION: CLI arguments only.
STATE_AND_STORAGE: No state mutation; optional JSON output path is explicit.
EXTERNAL_DEPENDENCIES: NONE
FAILURE_MODES: Missing file, malformed design, failed validation, bad JSON output path.
OBSERVABILITY: stdout summary and JSON findings.
LOCAL_RUN_OR_SMOKE_COMMANDS: python3 agent-system/tools/aso/aso.py validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict
SOURCE_REFS: project-input/PATCH_ASO_STAGE1_UPGRADE/02_STAGE1_UPGRADE_CONTRACT.md#D3
TASK_REFS: TASK_DEV_VALIDATE_DESIGN_001

## TESTING_STRATEGY

UNIT_OR_STATIC_CHECKS: python3 -m unittest discover -s agent-system/tools/aso/tests
INTEGRATION_CHECKS: validate-design runs against valid and negative fixture files.
RUNTIME_SMOKE_CHECKS: python3 agent-system/tools/aso/aso.py validate-design --help
ACCEPTANCE_SCENARIOS: valid_design.md passes under --strict.
NEGATIVE_OR_FAILURE_CHECKS: negative fixtures fail for DRF-001, DRF-002, DRF-003, DRF-004, DRF-005, and DRF-006.
EVIDENCE_REQUIRED: command exit codes and JSON report parse.
TESTING_TASK_REFS: TASK_DEV_VALIDATE_DESIGN_001
SOURCE_REFS: project-input/PATCH_ASO_STAGE1_UPGRADE/templates/DESIGN_VALIDATOR_NEGATIVE_FIXTURES.md

## TASK_DAG

NODE_ID: NODE-001
TASK_OR_ARTIFACT_REF: TASK_DEV_VALIDATE_DESIGN_001
ROLE: developer
DEPENDS_ON: design_audit_pass_then_checkpoint
UNBLOCKS: AC-006 validation evidence
GATE_REQUIRED: design_audit_pass_then_checkpoint
DISPATCH_STATUS: dispatchable

## DISPATCHABLE_TASK_PACKETS

ARTIFACT_REF: TASK_DEV_VALIDATE_DESIGN_001
CLASSIFICATION: task_packet
DISPATCH_STATUS: dispatchable
SCHEMA_STATUS: passed
TARGET_ROLE: developer
TASK_KIND: correction
REQUIRED_DOCS: project-input/PATCH_ASO_STAGE1_UPGRADE/task_packets/TASK_ASO_STAGE1_DEV_003_VALIDATE_DESIGN.md agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
ACCEPTANCE_SUMMARY: AC-006 valid fixture passes, negative fixtures fail, JSON output works, and validator remains read-only.
DEPENDENCIES: design_audit_pass_then_checkpoint
NEXT_ACTION_ELIGIBLE: yes
GATE_REQUIRED: design_audit_pass_then_checkpoint
ALLOWED_FILE_CHANGES: agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/** agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/parsers/** agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/rules/** agent-system/tools/aso/tests/** agent-system/tests/fixtures/design/**

## AUDIT_PLAN

DESIGN_SCOPE_CHECKS: Verify validate-design is read-only and scoped to design artifacts.
SOURCE_TRACEABILITY_CHECKS: Verify decisions cite task packet, contract, and rubric sources.
ASSUMPTION_GAP_RESEARCH_SEPARATION_CHECKS: Verify assumptions are listed separately and not used as accepted facts.
DECISION_SOURCE_CHECKS: Verify accepted decisions have SOURCE_REFS.
TASK_PACKET_SCHEMA_CHECKS: Verify downstream task artifact readiness is recorded.
DOWNSTREAM_DISPATCH_CHECKS: Verify design audit gate appears before dispatchable implementation work.
RISK_CHECKS: Verify risks map to next task or mitigation.
REQUIRED_EVIDENCE: Fixture command outputs, JSON parse, unit tests, doctor, lint, make test, make lint, git diff --check.

## RISK_REGISTER

RISK_ID: RISK-001
CATEGORY: validation
DESCRIPTION: Markdown validation is structural and deterministic, not a full natural-language proof.
LIKELIHOOD: medium
IMPACT: medium
MITIGATION: Use explicit fixture markers and deterministic rule IDs aligned with the contract fail conditions.
OWNER_OR_NEXT_TASK: TASK_DEV_VALIDATE_DESIGN_001
SOURCE_OR_DECISION_REF: DEC-001
STATUS: accepted
