# Project profile: infra

## When to use

Use this profile for infrastructure, deployment configuration, service topology, runtime environments, provisioning, hosting, networking, monitoring, or operational automation.

## Required gates and checks

- Verify environment topology, resource ownership, access boundaries, and change impact.
- Check configuration, secret references, network exposure, permissions, backups, monitoring, and rollback expectations.
- Confirm idempotency, drift handling, state storage, and dependency ordering where infrastructure-as-code is in scope.
- Validate cost, capacity, availability, and security assumptions when relevant.
- Confirm no secret values are stored in configuration, logs, state artifacts, or evidence.

## Typical artifacts

- infrastructure design or topology notes;
- configuration or infrastructure-as-code files;
- environment variable key lists;
- setup and deployment runbooks;
- monitoring and alerting notes;
- rollback or recovery procedures.

## Test expectations

- Static validation or planning commands where tooling supports them.
- Policy, lint, or format checks when available.
- Dry-run or non-mutating verification before applying changes when possible.
- Smoke checks for provisioned services, health endpoints, or connectivity.
- Rollback or recovery procedure review when launch is in scope.

## Setup considerations

- Document required tools, versions, providers, state backend assumptions, and configuration key names.
- Separate local, staging, and production assumptions when relevant.
- Ensure credentials are supplied through approved secret mechanisms and never recorded.

## Launch considerations

- Confirm plan/review evidence is accepted before mutating shared environments.
- Confirm monitoring, logs, backups, rollback, and access controls are ready.
- Confirm setup, run, smoke, and launch gates are complete before release.
- Confirm owner approval is captured for high-impact or irreversible changes.

## Handover considerations

- Provide topology, runbooks, required tools, configuration key names, state location description, monitoring links or paths, rollback steps, and support boundaries.
- Document known operational risks and pending decisions.
