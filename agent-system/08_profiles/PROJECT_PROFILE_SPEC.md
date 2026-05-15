# Project profile specification

## Purpose

Project profiles are optional extensions that add project-type-specific gates, checks, artifacts, test expectations, and setup/launch considerations.

Profiles do not replace or override universal agent-system governance. Core runtime, state transition, filesystem governance, audit flow, accepted-state locking, GAP flow, result validation, and lifecycle rules remain authoritative.

## Authority

Universal core rules have higher authority than profile guidance.

If a profile conflicts with any core rule, the core rule wins and the conflict must be treated as a task design or audit issue.

Profiles may:

- add quality gates and checks for a project type;
- clarify typical artifacts for bounded tasks;
- set expectations for setup, smoke, launch, and handover readiness;
- help designers produce project-appropriate task packets.

Profiles must not:

- bypass required audits;
- change runtime state meanings or transitions;
- alter accepted-state locking;
- weaken forbidden file, credential, or secret handling;
- introduce project-specific business terminology into universal core;
- authorize deployment, launch, or completion outside the lifecycle gates.

## Profile selection

Profile use is optional. The orchestrator, designer, or requirements analyst may reference a profile when a project type is known and the profile helps define bounded work.

When no specialized profile applies, use `generic`.

For mixed projects, combine relevant profile checks conservatively without weakening any selected profile. If combined guidance creates ambiguity, create a bounded design task or GAP instead of inventing local rules.

## Standard profile sections

Each profile should define:

- when to use it;
- required gates and checks;
- typical artifacts;
- test expectations;
- setup considerations;
- launch considerations;
- handover considerations.

## Universal gates still required

Every profile remains subject to the universal lifecycle gates:

- requirements gate;
- design gate;
- implementation audit gate;
- testing gate when required by task packet;
- setup gate when runtime setup is in scope;
- run/smoke gate when execution is in scope;
- launch readiness gate when release is in scope;
- handover gate when ownership transfer is in scope.

## Evidence expectations

Profile-related evidence should be concrete and traceable:

- changed paths or created artifacts;
- command outputs or smoke results where execution is applicable;
- test results or explicit reason tests were not applicable;
- setup notes for required configuration without exposing secret values;
- launch or handover readiness notes when those gates are in scope.

Secret names may be referenced only as required configuration keys. Secret values must never be read, printed, stored, committed, or included in evidence.
