# Project profile: generic

## When to use

Use this profile when no more specific project profile applies, or when the project type is intentionally broad or unknown.

## Required gates and checks

- Confirm that task packets preserve universal lifecycle, runtime, state, audit, and filesystem rules.
- Check that requirements, design, implementation, testing, setup, run, launch, documentation, and handover gates are included only when relevant to scope.
- Verify that acceptance criteria are measurable and project-agnostic.
- Verify that artifacts are bounded and traceable to tasks.
- Confirm that no profile guidance weakens core governance.

## Typical artifacts

- requirements summary;
- bounded design documents;
- task packets;
- implementation artifacts when applicable;
- test or review reports;
- setup and smoke notes when applicable;
- handover notes when applicable.

## Test expectations

- Use the smallest meaningful validation for the task scope.
- Include static checks, unit tests, integration tests, manual checks, or document review as appropriate.
- Record skipped tests with a concrete reason.

## Setup considerations

- Identify required tools, services, configuration keys, and runtime assumptions.
- Keep setup steps reproducible and avoid environment-specific hardcoding.
- Reference secret keys by name only, never values.

## Launch considerations

- Confirm accepted artifacts are current.
- Confirm required audits, tests, setup checks, smoke checks, and owner decisions are complete.
- Do not treat generic readiness as approval to bypass launch governance.

## Handover considerations

- Provide source-of-truth paths, run commands, configuration key names, known limitations, and support boundaries.
- Confirm that final state is traceable through task results and accepted artifacts.
