# PRODUCT_CAPABILITY_GATE_EXAMPLES

These examples show how to record product capability gates without confusing a
task or audit pass with product readiness.

## Capability Matrix Example

| CAPABILITY_ID | CAPABILITY_NAME | TASK_PACKET_REFS | SKELETON_STATUS | TASK_STATUS | CAPABILITY_STATUS | PRODUCT_GATE_STATUS | MVP_REQUIRED | FINAL_ACCEPTANCE_REQUIRED | EVIDENCE_REFS | OPEN_GAPS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CAP_AUTH_001` | Sign in and session handling | `TASK_DEV_AUTH_001`, `TASK_TEST_AUTH_001` | `passed` | `task_pass` | `capability_pass` | `partial` | `yes` | `yes` | developer result, auditor result, tester result | `NONE` |
| `CAP_BILLING_001` | Paid plan checkout | `TASK_DEV_BILLING_SKELETON_001` | `passed` | `task_pass` | `partial` | `partial` | `no` | `no` | skeleton task result and audit | `GAP_BILLING_PROVIDER_DECISION` |
| `CAP_IMPORT_001` | CSV import workflow | `TASK_DEV_IMPORT_001`, `TASK_TEST_IMPORT_001` | `passed` | `task_pass` | `capability_pass` | `product_pass` | `yes` | `yes` | implementation, audit, and test refs | `NONE` |

The billing row has a passed skeleton and a passed task, but it remains
`partial`. It cannot be used as `mvp_ready`.

## Task Packet Mapping Example

Use existing task packet sections to map work to capability IDs:

```text
## SCOPE_IN

- Implement CSV import validation for CAP_IMPORT_001.
- Update project capability matrix row CAP_IMPORT_001 with result and audit refs.

## ACCEPTANCE_CRITERIA

- CAP_IMPORT_001 task acceptance is met for CSV validation.
- Result records TASK_STATUS: task_pass.
- Result does not claim PRODUCT_GATE_STATUS: product_pass or MVP_READY: true.

## EVIDENCE_REQUIREMENTS

- Capability matrix row CAP_IMPORT_001 references this task result and audit result.
```

## Skeleton Is Not MVP Ready

Valid skeleton-only outcome:

```text
CAPABILITY_ID: CAP_BILLING_001
SKELETON_STATUS: passed
TASK_STATUS: task_pass
CAPABILITY_STATUS: partial
PRODUCT_GATE_STATUS: partial
MVP_READY: false
FINAL_ACCEPTANCE: pending
```

Invalid skeleton-only outcome:

```text
CAPABILITY_ID: CAP_BILLING_001
SKELETON_STATUS: passed
TASK_STATUS: task_pass
CAPABILITY_STATUS: capability_pass
PRODUCT_GATE_STATUS: product_pass
MVP_READY: true
```

The invalid example has no accepted capability, product, MVP, test, or
documentation evidence beyond the skeleton task.

## Product Gate Before Final Acceptance

Final acceptance may be considered only after the product gate evidence is
complete:

```text
PRODUCT_GATE_STATUS: product_pass
MVP_READY: true
FINAL_ACCEPTANCE: pending
FINAL_ACCEPTANCE_REQUIRED_REFS:
- project-docs/.../CAPABILITY_MATRIX.md
- project-runtime/results/TASK_TEST_MVP_FLOW_001.md
- project-runtime/audits/TASK_TEST_MVP_FLOW_001.md
- project-docs/.../HANDOVER_CHECKLIST.md
```

`FINAL_ACCEPTANCE: passed` belongs to the orchestrator-controlled final
acceptance gate, not to an implementation, testing, or documentation task
result by itself.
