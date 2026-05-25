# Project profile: fullstack_app

## When to use

Use this profile for applications that combine user-facing frontend surfaces with server-side APIs, persistence, background jobs, or other runtime services.

## Required gates and checks

- Apply relevant `frontend_app` and `backend_api` checks without weakening either profile.
- Verify end-to-end flow ownership across UI, API, data storage, and background processing where applicable.
- Confirm contract alignment between frontend clients and backend interfaces.
- Check environment configuration boundaries across client-visible and server-only settings.
- Verify deployment topology, startup order, health checks, and rollback expectations when launch is in scope.

## Typical artifacts

- system design or architecture notes;
- frontend pages, components, styles, or assets;
- backend service, API, and persistence artifacts;
- shared schemas, contracts, or validation rules;
- setup and runtime documentation;
- end-to-end smoke checklist.

## Test expectations

- Unit tests for isolated frontend and backend logic where supported.
- Contract tests or schema checks between client and server.
- Integration tests for service and persistence behavior.
- End-to-end smoke checks for critical user flows.
- Build, lint, and migration checks when tooling exists.

## Setup considerations

- Document installation and startup commands for each runtime component.
- Define configuration key names by component, separating public client settings from private server settings.
- Include database, queue, cache, storage, or service setup steps when in scope.
- Specify local and target environment assumptions without embedding secret values.

## Launch considerations

- Confirm backend health, frontend build, database migrations, and end-to-end smoke checks pass.
- Confirm rollback boundaries for frontend assets, backend services, and persistent data.
- Confirm observability and error reporting expectations across the stack.
- Confirm launch readiness is gated by accepted artifacts and audit results.

## Handover considerations

- Provide component map, run commands, build commands, migration commands, configuration key names, smoke commands, and operational notes.
- Identify cross-component dependencies and known failure modes.
