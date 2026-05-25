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
- help `solution_architect` produce project-appropriate task packets.

Profiles must not:

- bypass required audits;
- change runtime state meanings or transitions;
- alter accepted-state locking;
- treat candidate artifact packages, raw artifacts, rejected artifacts, or raw
  agent chat as accepted project truth;
- weaken forbidden file, credential, or secret handling;
- introduce project-specific business terminology into universal core;
- authorize deployment, launch, or completion outside the lifecycle gates.

## Profile selection

Profile use is optional. The orchestrator, `solution_architect`, or requirements analyst may reference a profile when a project type is known and the profile helps define bounded work.

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

Profile-agent task output is candidate artifact package output until accepted
by the orchestrator. Downstream profile guidance and task packets must cite
accepted artifact packages under `project-runtime/artifacts/accepted/` or
rendered runtime views under `project-runtime/rendered/` for context. The
required completion ordering remains:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

`AUDIT_ROUTE_READY` is only readiness evidence for audit routing; profiles must
not interpret it as live dispatch, checkpoint execution, deployment authority,
or final acceptance.

Secret names may be referenced only as required configuration keys. Secret values must never be read, printed, stored, committed, or included in evidence.
