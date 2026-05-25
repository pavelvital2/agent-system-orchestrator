# PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT

## Version Boundary

P5.4 is the planner dispatchability gate correction for the ASO package.

```text
PACKAGE_VERSION: 3.7.4
GOVERNANCE_RULESET_VERSION: 3.7.4
RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

Runtime Schema `3.1.1` and Artifact Package Schema `1.1.0` are preserved.
P5.4 changes the planner recommendation contract only; it does not redefine
runtime sidecar envelopes, artifact package manifests, RESULT packages, or
AUDIT_RESULT packages.

## Dispatchability Gate

`CREATE_AGENT` is a dispatch recommendation. `plan-next` may return it only
when `can_dispatch_agent()` proves the current action is dispatchable.

This gate is a planning contract only. Passing the gate means the orchestrator
may create a fresh profile-agent context through the governed conveyor flow; it
does not execute a daemon, run a live queue worker, perform checkpoint work, or
mutate project artifacts.

`can_dispatch_agent()` must require all of the following:

- `NEXT_ACTION.ACTION_TYPE` is dispatch-capable.
- `NEXT_ACTION.TARGET_ROLE` is a profile execution role.
- `NEXT_ACTION.TARGET_ROLE` is not a control or pseudo role such as
  `orchestrator`, `owner`, `project_owner`, or `none`.
- `NEXT_ACTION.TASK_ID` exists and is not `NONE`.
- `NEXT_ACTION.TASK_PACKET` exists and is not `NONE`.
- The referenced task packet file exists.
- The referenced task packet validates as a dispatchable task packet, not a
  task proposal or malformed document.
- The task registry entry is compatible with the target task and task kind.
- The current gate permits dispatch.
- Blocking rules do not prevent dispatch.
- Workspace identity, repository lock, baseline tracking, and runtime schema
  checks pass, unless an explicit first-bootstrap exception is documented by
  the active runtime contract.

## Machine Contract

Validators and command tests may parse the following JSON block as the P5.4
dispatchability contract. The block is intentionally small and deterministic;
it defines role classes, action classes, required inputs, required checks,
reason codes, and the canonical invalid tuple.

```json
{
  "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
  "contract_version": "1.0.0",
  "report_schema_ref": "agent-system/09_validators/schemas/dispatchability_gate.schema.json",
  "output_object": "dispatchability",
  "profile_execution_roles": [
    "requirements_analyst",
    "solution_architect",
    "designer",
    "developer",
    "auditor",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager"
  ],
  "deprecated_profile_role_aliases": {
    "designer": "solution_architect"
  },
  "control_or_pseudo_roles": [
    "orchestrator",
    "project_owner",
    "owner",
    "none"
  ],
  "none_values": [
    "",
    "NONE",
    "none",
    "null",
    "UNKNOWN"
  ],
  "dispatch_capable_action_types": [
    "create_agent"
  ],
  "non_dispatch_action_types": {
    "correction": "CORRECTION_REQUIRED",
    "update_state": "UPDATE_STATE",
    "wait_for_owner": "ASK_OWNER",
    "finalize": "FINALIZE",
    "stop": "STOP",
    "route_result": "ROUTE_RESULT"
  },
  "dispatch_recommendations": {
    "non_auditor_profile_role": "CREATE_AGENT",
    "auditor_profile_role": "CREATE_AUDITOR"
  },
  "create_auditor_contract": {
    "action_type": "create_agent",
    "recommended_next_action": "CREATE_AUDITOR",
    "canonical_action_type": false,
    "valid_only_when": [
      "target_role_is_auditor",
      "audit_route_is_required",
      "audit_task_packet_exists_and_is_dispatch_valid",
      "all_dispatchability_checks_pass"
    ]
  },
  "non_dispatch_recommendations": [
    "CORRECTION_REQUIRED",
    "UPDATE_STATE",
    "ASK_OWNER",
    "FREEZE",
    "BOOTSTRAP_PREP",
    "STOP",
    "ROUTE_RESULT",
    "FINALIZE",
    "CHECKPOINT_PREFLIGHT",
    "NONE"
  ],
  "required_inputs": [
    {
      "name": "action_type",
      "source": "NEXT_ACTION.content.action_type"
    },
    {
      "name": "target_role",
      "source": "NEXT_ACTION.content.target_role"
    },
    {
      "name": "task_id",
      "source": "NEXT_ACTION.content.task_id"
    },
    {
      "name": "task_packet",
      "source": "NEXT_ACTION.content.task_packet"
    },
    {
      "name": "dependency_status",
      "source": "NEXT_ACTION.content.dependency_status"
    },
    {
      "name": "current_gate_status",
      "source": "CURRENT_GATE.content.status"
    },
    {
      "name": "blocking_rules",
      "source": "plan-next.blocking_rules"
    },
    {
      "name": "task_registry_entry",
      "source": "TASK_REGISTRY.content.tasks[task_id]"
    },
    {
      "name": "resolved_reasoning_level",
      "source": "ORCHESTRATOR_RUNTIME_CONTRACT.reasoning_floor_by_role + task packet TASK_COMPLEXITY/REASONING_LEVEL_REQUIRED"
    },
    {
      "name": "dispatch_receipt_contract",
      "source": "agent-system/09_validators/schemas/dispatch_receipt.schema.json"
    },
    {
      "name": "workspace_identity_status",
      "source": "PROJECT_STATE.content.identity_validation_status"
    },
    {
      "name": "repository_lock_status",
      "source": "PROJECT_STATE.content.repository_lock_status"
    },
    {
      "name": "baseline_tracking_status",
      "source": "PROJECT_STATE.content.baseline_tracking_status"
    }
  ],
  "required_checks": [
    {
      "check_id": "DG54_ACTION_TYPE_DISPATCH_CAPABLE",
      "reason_code_on_fail": "action_type_not_dispatch_capable"
    },
    {
      "check_id": "DG54_TARGET_ROLE_PROFILE_EXECUTION",
      "reason_code_on_fail": "target_role_not_profile_execution"
    },
    {
      "check_id": "DG54_TARGET_ROLE_NOT_CONTROL",
      "reason_code_on_fail": "target_role_control_or_pseudo"
    },
    {
      "check_id": "DG54_TASK_ID_PRESENT",
      "reason_code_on_fail": "task_id_none"
    },
    {
      "check_id": "DG54_TASK_PACKET_PRESENT",
      "reason_code_on_fail": "task_packet_none"
    },
    {
      "check_id": "DG54_TASK_PACKET_EXISTS",
      "reason_code_on_fail": "task_packet_missing"
    },
    {
      "check_id": "DG54_TASK_PACKET_DISPATCH_VALID",
      "reason_code_on_fail": "task_packet_not_dispatch_valid"
    },
    {
      "check_id": "DG54_REASONING_FLOOR_RESOLVED",
      "reason_code_on_fail": "reasoning_floor_unresolved"
    },
    {
      "check_id": "DG54_BOOTSTRAP_REASONING_FIELDS_PRESENT",
      "reason_code_on_fail": "bootstrap_reasoning_fields_missing"
    },
    {
      "check_id": "DG54_TASK_REGISTRY_COMPATIBLE",
      "reason_code_on_fail": "task_registry_incompatible"
    },
    {
      "check_id": "DG54_CURRENT_GATE_PERMITS_DISPATCH",
      "reason_code_on_fail": "current_gate_blocks_dispatch"
    },
    {
      "check_id": "DG54_NO_BLOCKING_RULES",
      "reason_code_on_fail": "blocking_rules_present"
    },
    {
      "check_id": "DG54_WORKSPACE_IDENTITY_READY",
      "reason_code_on_fail": "workspace_identity_not_ready"
    },
    {
      "check_id": "DG54_REPOSITORY_LOCK_READY",
      "reason_code_on_fail": "repository_lock_not_ready"
    },
    {
      "check_id": "DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION",
      "reason_code_on_fail": "baseline_not_ready"
    }
  ],
  "reason_codes": [
    "action_type_not_dispatch_capable",
    "target_role_not_profile_execution",
    "target_role_control_or_pseudo",
    "task_id_none",
    "task_packet_none",
    "task_packet_missing",
    "task_packet_not_dispatch_valid",
    "reasoning_floor_unresolved",
    "bootstrap_reasoning_fields_missing",
    "task_registry_incompatible",
    "current_gate_blocks_dispatch",
    "blocking_rules_present",
    "workspace_identity_not_ready",
    "repository_lock_not_ready",
    "baseline_not_ready"
  ],
  "create_agent_invariants": [
    "recommended_next_action_CREATE_AGENT_requires_dispatchable_true",
    "recommended_next_action_CREATE_AGENT_requires_action_type_create_agent",
    "recommended_next_action_CREATE_AGENT_requires_non_auditor_profile_role",
    "recommended_next_action_CREATE_AGENT_requires_task_id_present",
    "recommended_next_action_CREATE_AGENT_requires_task_packet_present_and_dispatch_valid",
    "recommended_next_action_CREATE_AGENT_requires_resolved_reasoning_level",
    "recommended_next_action_CREATE_AGENT_requires_dispatch_receipt_contract",
    "recommended_next_action_CREATE_AGENT_requires_no_failed_required_checks",
    "recommended_next_action_CREATE_AGENT_must_not_perform_live_dispatch"
  ],
  "canonical_invalid_tuple": {
    "input": {
      "action_type": "correction",
      "target_role": "orchestrator",
      "task_id": "NONE",
      "task_packet": "NONE"
    },
    "expected": {
      "dispatchable": false,
      "verdict": "not_dispatchable",
      "recommended_next_action": "CORRECTION_REQUIRED",
      "status": "correction_required",
      "required_reason_codes": [
        "action_type_not_dispatch_capable",
        "target_role_not_profile_execution",
        "target_role_control_or_pseudo",
        "task_id_none",
        "task_packet_none"
      ],
      "forbidden_recommended_next_actions": [
        "CREATE_AGENT",
        "CREATE_AUDITOR"
      ]
    }
  }
}
```

## Role And Action Classes

Profile execution roles accepted by historical task packet schemas are:

```text
requirements_analyst
solution_architect
designer
developer
auditor
tester
technical_writer
devops_setup_engineer
release_manager
```

`designer` is a deprecated compatibility alias. The dispatchability gate must
normalize `TARGET_ROLE: designer` and task-packet `TARGET_ROLE: designer` to
`solution_architect` for planner output and compatibility checks. A
`CREATE_AGENT` dispatchability report must use `target_role: solution_architect`;
it must not expose direct `target_role: designer` dispatch.

Control and routing pseudo-roles include:

```text
orchestrator
project_owner
owner
none
```

Control and routing pseudo-roles are valid runtime routing targets in some
states, but they are never dispatchable profile execution roles. A
`TARGET_ROLE` of `orchestrator`, `project_owner`, `owner`, or `none` must make
`can_dispatch_agent()` fail.

The only dispatch-capable `NEXT_ACTION.ACTION_TYPE` for profile-agent creation
is:

```text
create_agent
```

`correction` is not a dispatch action. It is an internal recovery/correction
route until a governed state update selects a concrete dispatchable correction
task packet with `ACTION_TYPE: create_agent`, a profile `TARGET_ROLE`, a real
`TASK_ID`, and a real `TASK_PACKET`.

The following action types are non-dispatch routes:

| `NEXT_ACTION.ACTION_TYPE` | Required recommendation class |
| --- | --- |
| `correction` | `CORRECTION_REQUIRED` or `UPDATE_STATE` |
| `update_state` | `UPDATE_STATE` |
| `wait_for_owner` | `ASK_OWNER` |
| `route_result` | `ROUTE_RESULT` |
| `finalize` | `FINALIZE` |
| `stop` | `STOP` |

Incident, owner/GAP blocker, bootstrap, and invalid-state handling may return
`FREEZE`, `ASK_OWNER`, `BOOTSTRAP_PREP`, `CORRECTION_REQUIRED`, `UPDATE_STATE`,
`STOP`, or `NONE`, but not `CREATE_AGENT`.

## Canonical Readiness Status Values

Dispatchability readiness checks must use the canonical `PROJECT_STATE` schema
values for the fields they read:

| Check | Field | Ready values |
| --- | --- | --- |
| `DG54_WORKSPACE_IDENTITY_READY` | `PROJECT_STATE.content.identity_validation_status` | `passed` |
| `DG54_REPOSITORY_LOCK_READY` | `PROJECT_STATE.content.repository_lock_status` | `accepted` |
| `DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION` | `PROJECT_STATE.content.baseline_tracking_status` | `passed`, or the first-bootstrap exception when no profile-agent dispatch has been recorded |

`not_required` is not a valid `PROJECT_STATE` value for those three fields and
must not make a DG54 readiness check pass. Requirement flags such as
`NEXT_ACTION.content.workspace_identity_required=false` and
`NEXT_ACTION.content.repository_lock_required=false` may make the corresponding
check pass without changing the canonical `PROJECT_STATE` status vocabulary.
Those requirement flags are exemptions from readiness, not exemptions from
schema validation: if `state verify` rejects
`PROJECT_STATE.content.identity_validation_status` or
`PROJECT_STATE.content.repository_lock_status` as an invalid enum value, the
matching DG54 readiness condition must also be reported as not passed.

`WORKSPACE_IDENTITY.content.identity_validation_status` and
`WORKSPACE_IDENTITY.content.repository_lock_status` are diagnostic compatibility
fields. They may retain historical diagnostic values while the dispatchability
authority remains the canonical `PROJECT_STATE` fields above.

## Command Output Contract

`aso plan-next --json-out ...` must expose either:

- a top-level `dispatchability` object that conforms to
  `agent-system/09_validators/schemas/dispatchability_gate.schema.json`; or
- equivalent top-level fields with the same semantics until the command output
  is migrated to the nested object.

The dispatchability evidence must include:

- `dispatchable`: boolean verdict;
- `verdict`: `dispatchable` or `not_dispatchable`;
- `recommended_next_action`;
- `status`;
- `target_role`;
- `role_class`;
- `action_type`;
- `action_class`;
- `task_id`;
- `task_packet`;
- `resolved_reasoning_level` and `reasoning_source`;
- dispatch receipt schema, receipt path template, writer command template, and
  external runner command template;
- `checks[]` with stable `check_id`, `passed`, `severity`, `reason_code`, and
  `evidence`;
- `reasons[]` with stable `reason_code`, `message`, and `input_ref`;
- `live_dispatch_performed: false`.

If `recommended_next_action` is `CREATE_AGENT`, all required checks must pass,
`dispatchable` must be `true`, `verdict` must be `dispatchable`, `role_class`
must be `profile_execution`, `action_class` must be `dispatch`, `target_role`
must be a non-auditor profile execution role, `task_id` and `task_packet` must
not be a none value, and `live_dispatch_performed` must be `false`.

For every dispatchable recommendation, the report must also name the required
dispatch receipt path template:

```text
project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json
```

ASO does not execute Codex directly in this P58 boundary. The external dispatch
contract is:

```text
codex exec -C <WORKSPACE_ROOT> -m <MODEL> -c model_reasoning_effort="<REASONING_EFFORT>" - < <PROMPT_REF>
```

The orchestrator or external launcher must write a `DISPATCH_RECEIPT`
conforming to `agent-system/09_validators/schemas/dispatch_receipt.schema.json`
before profile-agent execution evidence is accepted.

The JSON Schema rejects CREATE_AGENT reports that violate those report-level
invariants. Implementation validators remain responsible for proving filesystem
facts and runtime facts behind those checks, including task packet existence,
dispatch-valid task packet content, registry compatibility, current gate state,
blocking rules, workspace identity, repository lock, and baseline readiness.

If `target_role` is `auditor` and the route is dispatchable, the recommendation
must be `CREATE_AUDITOR`, not `CREATE_AGENT`. `CREATE_AUDITOR` is still a
profile-agent dispatch recommendation and must satisfy the same dispatchability
checks, including task packet role/kind compatibility, task registry role/kind
compatibility, and current gate task/packet/role compatibility.

`CREATE_AUDITOR` is a recommendation label under the dispatchable
`ACTION_TYPE: create_agent` flow. It is not an independent canonical
`ACTION_TYPE`. The tuple is valid only when `TARGET_ROLE` is `auditor`, an audit
route is required by the planner, a valid audit task packet exists, and all
dispatchability checks pass. A non-dispatchable report must not recommend
`CREATE_AUDITOR`.

`aso orchestrator next --json-out ...` must surface the same dispatchability
verdict or a directly nested copy of the latest `plan-next` verdict. It must
not transform a non-dispatchable `NEXT_ACTION` tuple into `CREATE_AGENT`.

`aso orchestrator status --json-out ...` must summarize dispatchability without
weakening it. If the current tuple is non-dispatchable, status may report normal
conveyor health as pass, but its next-route summary must still identify the
route as non-dispatchable and include or reference the reason codes.

## Required Failure Route

If `can_dispatch_agent()` fails, `plan-next` must not return `CREATE_AGENT`.
It must return a non-dispatch recommendation and machine-readable evidence for
the failed dispatchability checks.

Allowed non-dispatch recommendations include:

- `CORRECTION_REQUIRED`
- `UPDATE_STATE`
- `ASK_OWNER`
- `FREEZE`
- `BOOTSTRAP_PREP`
- `STOP`

The planner may use another documented non-dispatch recommendation when the
runtime transition contract explicitly permits it. The response status must
make the route non-dispatchable, for example `blocked` or
`correction_required`.

For this canonical invalid tuple:

```text
NEXT_ACTION.ACTION_TYPE: correction
NEXT_ACTION.TARGET_ROLE: orchestrator
NEXT_ACTION.TASK_ID: NONE
NEXT_ACTION.TASK_PACKET: NONE
```

`plan-next`, `orchestrator next`, and any `orchestrator status` next-route
summary must return or preserve a non-dispatch recommendation. They must not
recommend `CREATE_AGENT`.

## Non-Goals

P5.4 does not add a daemon, live dispatch executor, checkpoint executor, ASO
Studio, distributed workers, external queue infrastructure, product-intake
engine, product generator, semantic raw-TZ interpretation, or automatic task
execution.

P5.4 does not authorize the orchestrator to implement code, tests, schemas, or
profile-agent outputs directly. The orchestrator remains a conveyor over
validated runtime state, task packets, artifact packages, audit results,
receipts, and checkpoint/preflight evidence.

## Filesystem Boundary

The following roots remain forbidden as tracked package files:

```text
project-input/
project-runtime/
project-archive/
.venv/
```
