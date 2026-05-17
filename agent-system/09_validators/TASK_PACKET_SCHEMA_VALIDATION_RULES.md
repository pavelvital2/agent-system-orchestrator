# TASK_PACKET_SCHEMA_VALIDATION_RULES

## Purpose

This document defines deterministic schema validation for task packets and task
proposals.

Validation exists to prevent:

- profile-agent dispatch from malformed task packets;
- informal task proposals from being used as dispatchable task packets;
- invalid downstream task packet files from entering a checkpoint before
  `git add`.

The executable validator is:

```text
agent-system/scripts/validate_task_packet.py
```

Equivalent governed validators may be used only when they enforce every rule in
this document and report the same blocker class:

```text
invalid_task_packet_schema
```

Solution architect design output must classify downstream task-like artifacts
according to:

```text
agent-system/03_templates/DESIGN_OUTPUT_CONTRACT.md
```

## Required status values

Task packet schema evidence must use:

```text
TASK_PACKET_SCHEMA_STATUS: not_checked | passed | failed | blocked | not_applicable
```

`not_checked` is valid only before a check is required. Once a changed
task-like artifact is in audit or checkpoint scope, `not_checked`, `failed`,
or `blocked` forbids auditor pass, staging, commit, and push.

## Packet classes

### Dispatchable task packet

A dispatchable task packet is a markdown file that declares:

```text
# TASK PACKET
```

and conforms to:

```text
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
```

Only a dispatchable task packet may be used as:

```text
NEXT_ACTION.TASK_PACKET
```

for:

```text
NEXT_ACTION.ACTION_TYPE: create_agent
```

### Task proposal

A task proposal is a markdown file that declares:

```text
# TASK PROPOSAL
```

or uses:

```text
TASK_PROPOSAL
```

as its explicit template/class marker.

A task proposal must conform to:

```text
agent-system/03_templates/TASK_PROPOSAL_TEMPLATE.md
```

Task proposals are non-dispatchable. They may be reviewed or converted into a
full task packet by a governed task, but they must not be placed in
`NEXT_ACTION.TASK_PACKET` and must not be used to create a profile agent.

If a `TASK_PROPOSAL` is selected for `create_agent`, validation must fail with:

```text
invalid_task_packet_schema
```

## Downstream artifact classification

Design output and other planning output may create future work artifacts only
when each changed task-like artifact is explicitly classified:

```text
TASK_PACKET:
  dispatchable only if the file declares # TASK PACKET and passes task packet
  schema validation

TASK_PROPOSAL:
  non-dispatchable only if the file declares # TASK PROPOSAL or TASK_PROPOSAL
  and contains DISPATCH_STATUS: non_dispatchable
```

The design contract requires these artifacts to be listed in
`DISPATCHABLE_TASK_PACKETS` with classification, schema status, dependencies,
and `NEXT_ACTION` eligibility.

Changed downstream files matching these patterns must be inspected before
design audit pass and again before checkpoint staging:

```text
TASK_*.md
TASK_PROPOSAL*.md
*_TASK_PACKET*.md
```

Rules:

- a changed downstream `TASK_*.md` file that is intended for dispatch must be a
  valid dispatchable `# TASK PACKET`;
- a changed downstream `TASK_*.md` file that is not ready for dispatch must be
  classified as a `TASK_PROPOSAL` and must remain non-dispatchable;
- a task-like artifact that lacks both task packet and task proposal markers is
  invalid;
- a `TASK_PROPOSAL` selected by `NEXT_ACTION.TASK_PACKET` is invalid;
- invalid or ambiguous downstream task artifacts must be reported as
  `invalid_task_packet_schema`.

## Mandatory task packet sections

Every dispatchable task packet must include these `##` sections exactly once in
substance. The validator checks presence and non-empty content:

```text
TASK_ID
TASK_STATUS
TASK_KIND
SUPERSEDES
SUPERSEDED_BY
CORRECTION_OF
SOURCE_RESULT_REF
ATTEMPT_NO
FAILURE_TYPE
TASK_TITLE
TASK_TYPE
TARGET_ROLE
REASONING_LEVEL
DEPENDENCIES
DEPENDENCY_STATUS
REQUESTED_BY_ROLE
REQUESTED_BY_TASK
RESEARCH_QUESTION_ID
RESEARCH_PURPOSE
RESEARCH_QUESTIONS
ALLOWED_SOURCES
FORBIDDEN_SOURCES
EXPECTED_EVIDENCE
EXPECTED_OUTPUT
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS
RETURN_TO_ROLE_AFTER_AUDIT_PASS
RETURN_TASK_AFTER_AUDIT_PASS
PURPOSE
SOURCE_OF_TRUTH
SCOPE_IN
SCOPE_OUT
REQUIRED_DOCS
INPUTS
READ_INPUTS
EXPECTED_OUTPUTS
ALLOWED_FILE_CHANGES
FORBIDDEN_FILE_CHANGES
ACCEPTANCE_CRITERIA
EVIDENCE_REQUIREMENTS
SETUP_HOOKS
LAUNCH_HOOKS
RESULT_PATH
RISK_REQUIREMENTS
MANDATORY_WORKFLOW
NEXT_ROLE_ON_PASS
NEXT_ROLE_ON_FAIL
NEXT_ROLE_ON_BLOCKED
NEXT_ROLE_ON_GAP
AUDIT_REQUIREMENTS
TESTING_REQUIREMENTS
DOCUMENTATION_REQUIREMENTS
FILESYSTEM_GOVERNANCE
RUNTIME_GOVERNANCE
RESULT_FORMAT
TERMINAL_CONDITIONS
NOTES
```

## Mandatory proposal sections

Every `TASK_PROPOSAL` must include:

```text
PROPOSAL_ID
PROPOSAL_STATUS
PROPOSAL_TITLE
REQUESTED_BY_ROLE
PURPOSE
PROPOSED_TASK_KIND
PROPOSED_TARGET_ROLE
PROPOSED_SCOPE
OPEN_QUESTIONS
DISPATCH_STATUS
```

`DISPATCH_STATUS` must be:

```text
non_dispatchable
```

## Dispatch validation

Before any profile-agent `create_agent`, the orchestrator must validate the
selected task packet in dispatch mode.

Dispatch mode must verify:

1. the file declares `# TASK PACKET`;
2. the file does not declare `# TASK PROPOSAL`;
3. all mandatory task packet sections exist and are non-empty;
4. enum fields use values allowed by `TASK_PACKET_TEMPLATE.md`;
5. `TASK_STATUS` is `active`;
6. `TASK_TYPE` and `TARGET_ROLE` match after role alias normalization for
   profile execution tasks;
7. `REQUIRED_DOCS` does not include `project-archive/` or deprecated documents;
8. the file path is valid under filesystem governance.

If any dispatch validation fails, `create_agent` is forbidden and the
orchestrator must route to governed correction with:

```text
invalid_task_packet_schema
```

## Path validation

Ordinary dispatchable task packets must be inside:

```text
ACTIVE_DOC_ROOT
```

The only first-bootstrap exception outside `ACTIVE_DOC_ROOT` is:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

This exception is valid only when all conditions are true:

- it is the first profile-agent dispatch;
- `<TARGET_ROLE>` is populated by the selected first profile route;
- the packet is a full bootstrap task packet;
- the packet passes schema validation.

Blank-role bootstrap placeholders are invalid.

Owner-authorized package-governance correction/update task packets may be
validated as explicit package-correction input only when the active task packet
and runtime route identify them as package governance correction material.
This exception does not authorize ordinary project task packets outside
`ACTIVE_DOC_ROOT`.

## Checkpoint validation

Before any post-audit checkpoint stages files, checkpoint preflight must run
task packet schema validation against changed task artifacts.

The preflight must inspect changed markdown files that are task artifacts,
including:

```text
TASK_*.md
TASK_PROPOSAL*.md
*_TASK_PACKET*.md
```

Rules:

- every changed file declaring `# TASK PACKET` must pass task packet schema
  validation;
- every changed downstream `TASK_*.md` dispatchable artifact must pass schema
  validation before audit pass and before checkpoint;
- every changed active dispatchable task packet must also pass dispatch path
  validation;
- every changed `TASK_PROPOSAL` must pass proposal validation and remain
  non-dispatchable;
- a changed task artifact that lacks both a task packet marker and a task
  proposal marker is invalid;
- failure blocks checkpoint before `git add`.

The checkpoint blocker code is:

```text
invalid_task_packet_schema
```

## Validator commands

Schema-only validation:

```text
python agent-system/scripts/validate_task_packet.py --mode schema <task_packet.md>
```

Dispatch validation:

```text
python agent-system/scripts/validate_task_packet.py --mode dispatch --active-doc-root project-docs <task_packet.md>
```

First-bootstrap validation:

```text
python agent-system/scripts/validate_task_packet.py --mode dispatch --active-doc-root project-docs --allow-first-bootstrap project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
```

Package-governance correction validation:

```text
python agent-system/scripts/validate_task_packet.py --mode dispatch --active-doc-root project-docs --allow-system-package-correction <task_packet.md>
```

Checkpoint validation:

```text
python agent-system/scripts/validate_task_packet.py --mode checkpoint --active-doc-root project-docs <changed_task_artifact.md>
```

Design-audit downstream artifact validation may use the same checkpoint mode
against each changed task-like artifact before auditor pass. The audit evidence
must record which changed artifacts were validated and whether each was a
dispatchable `TASK_PACKET` or non-dispatchable `TASK_PROPOSAL`.

## Audit evidence for changed task packets

When changed files include `TASK_*.md`, `TASK_PROPOSAL*.md`, or
`*_TASK_PACKET*.md`, auditor evidence must include:

```text
VALIDATED_TASK_PACKETS:
- path: <changed path>
  classification: TASK_PACKET | TASK_PROPOSAL | invalid
  TASK_PACKET_SCHEMA_STATUS: passed | failed | blocked
  validator_or_manual_rule_ref: <command or rule reference>
  dispatchable: yes | no
```

Every changed dispatchable `TASK_PACKET` entry must have
`TASK_PACKET_SCHEMA_STATUS: passed` before audit pass or checkpoint
eligibility can be accepted. Any invalid, ambiguous, missing, or unlisted
changed task-like artifact must be reported as:

```text
invalid_task_packet_schema
```
