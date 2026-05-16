# Project profile: backend_api

## When to use

Use this profile for services that expose programmatic interfaces, handle server-side business logic, or provide data access through API endpoints.

## Required gates and checks

- Verify API contract ownership, versioning expectations, request/response schemas, and error formats.
- Check authentication, authorization, input validation, rate limiting, and sensitive data handling where applicable.
- Confirm persistence, migration, transaction, idempotency, and rollback expectations when data storage is in scope.
- Validate observability expectations for logs, metrics, tracing, and operational diagnostics.
- Confirm that runtime configuration is documented without exposing secret values.

## Typical artifacts

- API contract or endpoint specification;
- data model or schema notes;
- migration artifacts when storage changes are in scope;
- service configuration notes;
- error handling and validation rules;
- operational runbook or smoke checklist.

## Test expectations

- Unit tests for core service logic and validation.
- Contract or integration tests for endpoints and external dependencies.
- Migration tests or rollback checks when schemas change.
- Negative tests for invalid input and unauthorized access where applicable.
- Smoke checks for health, readiness, and representative API calls.

## Setup considerations

- Document required runtime, package manager, database, queue, cache, and service dependencies.
- Define local startup commands and required configuration key names.
- Include migration, seed, or fixture setup steps when needed.
- Keep generated credentials, tokens, and connection strings out of artifacts and logs.

## Launch considerations

- Confirm migrations are reviewed and reversible or otherwise explicitly accepted.
- Confirm health/readiness endpoints and smoke calls pass in the target environment.
- Confirm monitoring, logging, backup, and rollback expectations are addressed when in scope.
- Confirm API compatibility risks are recorded before release.

## Handover considerations

- Provide endpoint documentation, configuration keys, run commands, migration commands, smoke commands, and operational notes.
- Identify known external dependencies and failure modes without including secret values.
