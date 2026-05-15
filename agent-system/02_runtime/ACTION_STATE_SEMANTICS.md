# ACTION_STATE_SEMANTICS

## Purpose

This document defines strict meanings for runtime action/state terms that are easy to confuse during orchestration.

The terms below are universal operational semantics. They do not replace `RUNTIME_STATE_SCHEMA.md`, `STATE_TRANSITION_RULES.md`, or `GOVERNANCE_AUTHORITY.md`.

## Semantic terms

| Term | Meaning | Runtime representation | Dispatch allowed? | Resume condition |
|---|---|---|---|---|
| `wait_for_owner` | The orchestrator needs a project owner decision, answer, approval, or missing input before the affected branch can continue. | `NEXT_ACTION.ACTION_TYPE: wait_for_owner`; `TARGET_ROLE: project_owner`; affected branch or project blocker recorded. | No dispatch on the dependent branch. Independent branches may continue only if transition rules and blockers allow it. | Owner response is recorded and routed through the required governed update, design, correction, or GAP flow. |
| `pause` | A temporary orchestrator-controlled no-dispatch hold that does not require owner input and is not terminal. | `PROJECT_STATUS: blocked`; `CURRENT_PHASE: blocked` or `correction`; `CURRENT_GATE.STATUS: blocked`; `NEXT_ACTION.ACTION_TYPE: update_state` or `correction`; `ACTION_SEMANTIC: pause` in `NEXT_ACTION.md`. | No normal dispatch while the pause blocker is active. | Explicit blocker clearance, prerequisite completion, or governed state update. |
| `stop_terminal` | A terminal stop instruction after finalization invariants pass, or a governed stop during unrecoverable runtime halt when transition rules permit it. | `NEXT_ACTION.ACTION_TYPE: stop`; `TARGET_ROLE: none`; `ACTION_SEMANTIC: stop_terminal`. For successful completion, terminal completion fields must also be set. | No dispatch. | None. A terminal stop cannot resume as a normal pause. |
| `completed` | The accepted final project state after orchestrator finalization. | `PROJECT_STATE.CURRENT_PHASE: completed`; `PROJECT_STATE.PROJECT_STATUS: completed`; `CURRENT_GATE.GATE_TYPE: terminal`; `CURRENT_GATE.STATUS: passed`; `NEXT_ACTION.ACTION_TYPE: stop`; `ACTION_SEMANTIC: stop_terminal`. | No dispatch. | None. Any later work starts as a new governed lifecycle, not by resuming the completed state. |

## Non-equivalence rules

- `wait_for_owner` is not a generic pause. It requires a concrete owner-facing question, decision, or missing input.
- `pause` is not terminal. It must identify the active blocker and the condition for resuming or routing correction.
- `stop_terminal` is not a temporary hold. It may not be used to wait, throttle, defer, or park work that is expected to resume.
- `completed` is not an action. It is a project state reached only after terminal finalization invariants pass.
- Profile-agent `STATUS: pass` does not imply `completed`.
- Profile-agent `STATUS: blocked` does not imply `wait_for_owner`; blocker routing determines whether owner input, designer correction, implementation correction, runtime correction, or another governed path is required.

## Audit fail semantics

An auditor `STATUS: fail` means the checked result is not accepted.

Required semantics:

- no normal next task may be dispatched from the failed result;
- no post-audit Git checkpoint may run;
- the affected branch must route to correction for the checked role, designer, or another governed correction target;
- the failed gate remains failed or blocked until corrected and re-audited;
- `NEXT_ACTION.DEPENDENCY_STATUS` for dependent work must be `blocked` until the correction path passes required gates.

## Blocked branch semantics

An active blocker must be represented consistently in runtime state:

```text
BLOCKER_ID:
BLOCKER_TYPE: owner_decision | pause | audit_fail | gap | runtime | dependency | governance | other
BLOCKS:
BLOCKED_BY:
RESOLUTION_PATH:
```

Any branch blocked by that blocker must reference the same `BLOCKER_ID`.

```text
BRANCH_ID:
STATUS: blocked
CURRENT_TASK:
CURRENT_AGENT_ROLE:
DEPENDENCIES:
BLOCKED_BY: <BLOCKER_ID>
```

The orchestrator may not dispatch dependent work while the referenced blocker remains active.

## Terminal stop invariants

`ACTION_SEMANTIC: stop_terminal` is valid only when one of these conditions is true:

- successful terminal completion invariants in `STATE_TRANSITION_RULES.md` are satisfied;
- a governed unrecoverable halt is explicitly allowed by `STATE_TRANSITION_RULES.md` and does not pretend the project is completed.

If work is expected to resume, use `pause`, `wait_for_owner`, or `correction` semantics instead of `stop_terminal`.
