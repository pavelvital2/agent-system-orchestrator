# PROJECT_LIFECYCLE

## Purpose

This document defines the universal project lifecycle for the agent-system package. It is project-agnostic and applies to any bounded project that starts from a TZ or equivalent source brief and ends with launch, handover, and final acceptance.

## Lifecycle order

```text
BOOTSTRAP
REQUIREMENTS
DESIGN
IMPLEMENTATION
AUDIT
TESTING
SETUP
RUN
LAUNCH
DOCUMENTATION
HANDOVER
FINAL_ACCEPTANCE
```

Audit is a mandatory gate after design and implementation work. Additional audit gates may be required by task packets.

## Stage map

| Stage | Main role | Output |
|---|---|---|
| Bootstrap | Orchestrator | runtime-ready task context |
| Requirements | Requirements analyst | requirements baseline or GAP |
| Design | Designer | bounded project docs and task packets |
| Implementation | Developer | scoped implementation result |
| Audit | Auditor | independent pass/fail/blocked/gap result |
| Testing | Tester | acceptance evidence |
| Setup | Devops/setup engineer | verified setup readiness |
| Run | Devops/setup engineer or tester | verified run/smoke evidence |
| Launch | Release manager | launch readiness result |
| Documentation | Technical writer | verified user or operational docs |
| Handover | Release manager and technical writer | accepted artifact and operation summary |
| Final acceptance | Orchestrator-controlled owner/project gate | accepted terminal state |

## Universal gates

A project must not move forward when:

- required source inputs are missing;
- a GAP blocks the next stage;
- an audit required by the task packet has not passed;
- testing required by the task packet has not passed;
- setup or run commands required for launch are unverified;
- launch evidence is incomplete;
- handover documentation is missing when required.

## Stage documents

- `agent-system/07_lifecycle/BOOTSTRAP_STAGE.md`
- `agent-system/07_lifecycle/REQUIREMENTS_STAGE.md`
- `agent-system/07_lifecycle/DESIGN_STAGE.md`
- `agent-system/07_lifecycle/IMPLEMENTATION_STAGE.md`
- `agent-system/07_lifecycle/TESTING_STAGE.md`
- `agent-system/07_lifecycle/SETUP_STAGE.md`
- `agent-system/07_lifecycle/RUN_STAGE.md`
- `agent-system/07_lifecycle/LAUNCH_STAGE.md`
- `agent-system/07_lifecycle/HANDOVER_STAGE.md`

## Final acceptance rule

Final acceptance requires accepted evidence for requirements, design, implementation, required audits, testing, setup, run readiness, launch readiness, documentation, and handover. The orchestrator routes this state; profile agents do not mark the whole project completed by themselves.
