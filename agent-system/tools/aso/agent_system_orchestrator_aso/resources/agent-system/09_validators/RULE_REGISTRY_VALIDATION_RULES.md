# RULE_REGISTRY_VALIDATION_RULES

## Purpose

This document defines the machine-readable governance rule registry schema and
the read-only validation behavior for:

```text
agent-system/09_validators/rules/governance_rules.json
```

The registry is an index of governing rules and source documents. It does not
replace the Markdown governance documents.

## Registry object

The registry root must be a JSON object with:

```text
schema_version: non-empty string
registry_id: non-empty string
rules: non-empty array of rule objects
```

## Rule object

Every rule object must include:

```text
id: stable, unique, non-empty string using A-Z, 0-9, underscore, and hyphen
severity: one of info, warning, error, critical
source_docs: non-empty array of repository-relative Markdown paths
check_target: non-empty string naming the governed surface
trigger: non-empty string describing when the rule applies
expected_action: non-empty string or array of allowed action tokens
rationale: non-empty string explaining why the rule exists
```

## Allowed action tokens

`expected_action` values must be selected from:

```text
block
warn
record_gap
redact
reject
require_audit_pass
require_checkpoint_preflight
require_correction
require_identity_pass
require_owner_input
require_repository_lock
route_to_auditor
stop
validate_schema
validate_scope
validate_traceability
validate_transition
```

## Source document validation

Each `source_docs` entry must be repository-relative, must not use parent path
traversal, and must point to an existing file under the validated root.

## Validator behavior

`aso validate-rules --root . --strict --json-out <path>` must:

- read the registry from the validated root;
- validate registry shape, rule IDs, allowed severities, allowed actions,
  source document existence, and non-empty rationale;
- return exit 0 when no errors are present;
- return nonzero for malformed registries;
- write the JSON report only when `--json-out` is explicitly provided;
- avoid mutating the registry, source documents, runtime state, Git state, or
  project governance documents.

`--strict` treats warnings as failures. The current schema reserves warnings
for compatibility checks; structural and semantic violations are errors.
