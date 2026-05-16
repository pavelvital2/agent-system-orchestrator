# REASONING_LEVEL_VALIDATION_RULES

## Purpose

This document defines validation checks for explicit reasoning level governance.

## Allowed levels

```text
low
default
high
maximum
role_default
```

## Role defaults

```text
orchestrator: default
requirements_analyst: maximum
designer: maximum
developer: default
auditor: high
tester: high
technical_writer: default
devops_setup_engineer: high
release_manager: high
```

## Gate-required floors

```text
requirements gate: maximum
design gate: maximum
audit gate: high
final audit: maximum
testing gate: high
setup gate: high
launch gate: high
final acceptance: maximum
correction after audit fail: high
governance correction: maximum
lifecycle/state/transition changes: maximum
security/secrets policy: high
cross-link validation: high
```

## Validation rules

- `REASONING_LEVEL.VALUE` must be one of the allowed levels.
- `role_default` resolves to the target role default before gate-floor checks.
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
