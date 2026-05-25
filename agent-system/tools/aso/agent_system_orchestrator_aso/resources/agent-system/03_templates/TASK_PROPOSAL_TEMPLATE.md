# TASK_PROPOSAL_TEMPLATE

## Purpose

This template defines a non-dispatchable task proposal.

A `TASK_PROPOSAL` is an idea, draft, or candidate future task. It is not a
bounded task packet and cannot be used for profile-agent dispatch.

To become dispatchable, the proposal must be converted into a full task packet
that conforms to:

```text
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
```

When emitted as downstream work by a solution architect or other planning task,
this file is the explicit non-dispatchable classification for the proposed
work. It must remain planning input until a separate governed task creates a
valid `# TASK PACKET`.

---

# TASK PROPOSAL

## PROPOSAL_ID

```text
<PROPOSAL_ID>
```

Rules:

- must be stable within the proposal review context;
- must not be reused as a dispatchable `TASK_ID`.

---

## PROPOSAL_STATUS

```text
draft | reviewed | accepted_for_task_packet | rejected | superseded
```

Rules:

- `accepted_for_task_packet` means a governed task may create a full task
  packet from this proposal;
- no proposal status makes this file dispatchable.

---

## PROPOSAL_TITLE

```text
<short proposal title>
```

---

## REQUESTED_BY_ROLE

```text
<requirements_analyst | solution_architect | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | orchestrator | project_owner | none>
```

---

## PURPOSE

```text
<why this candidate task may be needed>
```

---

## PROPOSED_TASK_KIND

```text
bootstrap | normal | research_dependency | design_continuation | task_continuation | correction | audit | testing | setup | launch | handover | UNKNOWN
```

---

## PROPOSED_TARGET_ROLE

```text
<requirements_analyst | solution_architect | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | UNKNOWN>
```

## PROPOSED_TASK_COMPLEXITY

```text
low | medium | high | xhigh | UNKNOWN
```

## PROPOSED_REASONING_LEVEL_REQUIRED

```text
low | medium | high | xhigh | UNKNOWN
```

## PROPOSED_AGENT_LIFECYCLE_POLICY

```text
one_agent_one_task_delete_after_result | UNKNOWN
```

---

## PROPOSED_SCOPE

```text
- <candidate scope item> | NONE
```

Rules:

- scope is advisory only;
- proposal scope must not grant file access or runtime authority;
- proposal scope must be re-authored in a full task packet before dispatch.

---

## OPEN_QUESTIONS

```text
- <question> | NONE
```

---

## DISPATCH_STATUS

```text
non_dispatchable
```

Rules:

- `TASK_PROPOSAL` files must not be referenced by `NEXT_ACTION.TASK_PACKET`;
- `TASK_PROPOSAL` files must not be sent to profile agents as dispatchable
  task packets;
- selecting a proposal for `create_agent` is an
  `invalid_task_packet_schema` blocker.
- requester-return or design-continuation routing described in a proposal is
  advisory only and does not authorize dispatch.

---

## CONVERSION_REQUIREMENTS

```text
- create a full TASK_PACKET_TEMPLATE-compatible packet before dispatch
- validate the resulting task packet with TASK_PACKET_SCHEMA_VALIDATION_RULES
- keep this proposal as non-dispatchable historical context if retained
```
