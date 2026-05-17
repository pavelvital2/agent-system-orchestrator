# REASONING_LEVEL_VALIDATION_RULES

## Purpose

This document defines validation checks for explicit reasoning level governance.

## Allowed levels

```text
low
medium
high
xhigh
```

`default`, `maximum`, and `role_default` are deprecated values and must not be
used as `REASONING_LEVEL.VALUE` in new task packets. `role_default` may be used
only as source/policy metadata, not as a level value.

## Role defaults

```text
orchestrator: high
requirements_analyst: high
designer: xhigh
developer: high
auditor: xhigh
tester: high
technical_writer: medium
devops_setup_engineer: high
release_manager: high
```

## Gate-required floors

```text
requirements gate: xhigh
design gate: xhigh
audit gate: xhigh
final audit: xhigh
testing gate: high
setup gate: high
launch gate: high
final acceptance: xhigh
correction after audit fail: high
governance correction: xhigh
lifecycle/state/transition changes: xhigh
security/secrets policy: high
cross-link validation: high
```

## Validation rules

- `REASONING_LEVEL.VALUE` must be one of the allowed levels:
  `low`, `medium`, `high`, or `xhigh`.
- `role_default` must not be used as `REASONING_LEVEL.VALUE`; it is valid only
  as source/policy metadata that resolves to the target role default before
  gate-floor checks.
- A task packet may raise reasoning level without `OVERRIDE_REASON`.
- A task packet may lower reasoning level only for mechanical bounded tasks and
  must include `OVERRIDE_REASON`.
- A task packet must not lower below a gate-required floor.
- `low` is allowed only for mechanical bounded tasks such as formatting,
  renaming a heading, updating a single link, adding a missing file to a
  checklist, copying a template field into schema, or normalizing naming
  without changing rules.
- `low` is forbidden for design, requirements analysis, audit, correction
  after failed audit, lifecycle/state/transition changes, security/secrets
  policy, launch/release readiness, final acceptance, and cross-link
  validation.

Violations must block dispatch and route through governed correction.

## Dispatch execution compliance

Before spawning any profile agent, the orchestrator must resolve:

```text
role_default_reasoning_level
task_packet_reasoning_level
gate_required_floor
final_required_dispatch_level
requested_or_configured_reasoning_level
runner_config_evidence
```

`final_required_dispatch_level` is the highest applicable level among role
default, task packet `REASONING_LEVEL`, and gate-required floor, using:

```text
low < medium < high < xhigh
```

The handoff, spawn log, or orchestrator transcript must record:

```text
TARGET_ROLE
TASK_ID
TASK_PACKET
REASONING_LEVEL_REQUIRED
REASONING_LEVEL_SOURCE
REASONING_LEVEL_RESOLVED
RUNNER_CONFIG_EVIDENCE
REASONING_LEVEL_COMPLIANCE
SPAWN_LOG_REF or HANDOFF_LOG_REF
```

If the requested or configured runner reasoning level is below required, this
is invalid dispatch:

- worker RESULT is invalid;
- audit must fail or block and must not pass;
- post-audit checkpoint is forbidden;
- commit/push are forbidden;
- routing must enter governed correction.

## Auditor compliance check

The auditor must verify reasoning-level execution compliance from task packet,
role defaults, gate-required floor, and available runner configuration evidence
from spawn log, handoff, or orchestrator transcript. The system must not claim
knowledge of the agent's internal reasoning level unless the runner provides
verifiable evidence.

Auditor validation must check:

```text
task packet REASONING_LEVEL
role default
gate-required floor
requested or configured runner reasoning level
no downgrade below required level
evidence from spawn log, handoff, or orchestrator transcript
```

If the requested or configured runner reasoning level is lower than the
resolved required level, auditor `STATUS: pass` is invalid. The auditor must
return `STATUS: fail` or `STATUS: blocked`.

Auditor evidence must record:

```text
REASONING_LEVEL_COMPLIANCE: passed | failed | blocked
```

If checkpoint preflight or later deterministic routing detects a
reasoning-level blocker after auditor `STATUS: pass`, and the auditor had the
required spawn/handoff evidence available, the orchestrator must record
`AUDIT_FALSE_PASS_DETECTED` with `FAILURE_TYPE: audit_miss` and route correction
without staging, commit, or push.
