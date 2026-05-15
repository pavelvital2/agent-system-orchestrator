# VALIDATOR_SPEC

## Purpose

This document defines the universal validator layer for the deterministic
agent-system runtime.

The validator layer is documentation-first. It specifies required checks,
failure classes, and routing expectations. It does not require a working CLI,
script, service, or executable implementation.

Validators help the orchestrator detect:

- inconsistent runtime state;
- invalid state transitions;
- invalid task packets;
- invalid agent RESULT payloads;
- unsafe or unauthorized file changes;
- unsafe Git checkpoint attempts;
- secret-handling violations.

## Source of authority

Validator rules must comply with:

```text
agent-system/02_runtime/GOVERNANCE_AUTHORITY.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
```

If this validator specification conflicts with runtime governance, runtime
governance wins and this specification must be corrected.

## Validator documents

```text
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
agent-system/09_validators/TASK_PACKET_VALIDATION_RULES.md
agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
```

## Validation points

The orchestrator should apply validator rules at these points:

```text
before_dispatch:
  runtime consistency
  task packet validity
  transition validity

after_agent_result:
  result validity
  file-scope validity
  transition validity

before_audit_dispatch:
  runtime consistency
  audit task packet validity

after_audit_result:
  result validity
  transition validity
  accepted-state rules

before_git_checkpoint:
  Git checkpoint validity
  secret-safety checks
  allowed/forbidden file checks
```

## Failure classification

Validator failures are orchestrator-classified violations or routing blockers.
Profile agents still return only:

```text
pass
fail
blocked
gap
```

`violation` is not a profile-agent RESULT status. It is an orchestrator
classification for recovery and logging.

## Common validation outcomes

```text
valid:
  Continue governed routing.

invalid_recoverable:
  Log violation or invalid state.
  Enter correction flow.

invalid_blocked:
  Log blocker.
  Route to wait_for_owner only when owner input is required.

invalid_terminal:
  Stop dispatch until governance or owner correction is provided.
```

## Secret-safety baseline

Validators must never require reading, printing, storing, staging, committing,
or pushing secret values.

Secret-safety checks should verify paths, file names, diff metadata, and
redacted indicators only. If a suspected secret value is encountered, the
validator result must refer to the path and violation class without reproducing
the value.

## File-scope baseline

Every validator that inspects changes must compare changed paths against:

- task packet `ALLOWED_FILE_CHANGES`;
- task packet `FORBIDDEN_FILE_CHANGES`;
- role authority in filesystem governance;
- runtime restrictions on `agent-system/`, `project-runtime/`,
  `project-input/`, and `project-archive/`.

Any path outside allowed scope is a workflow/filesystem violation.

## Project-agnostic rule

Validator rules must remain universal. They must not include business-domain
terms, application-specific implementation details, or project-specific
exceptions.
