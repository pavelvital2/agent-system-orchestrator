# PRODUCT_CAPABILITY_GATE_POLICY

## Purpose

This policy separates governance/task completion from product readiness.

A profile agent, auditor, smoke test, or lint command may prove that a bounded
work item followed the rules. That proof does not by itself prove that the
product is ready for MVP, launch, or final acceptance.

## Gate Vocabulary

Use these gate names when recording readiness claims:

```text
governance_pass
task_pass
capability_pass
product_pass
mvp_ready
final_acceptance
```

Definitions:

| Gate | Meaning | Does not mean |
| --- | --- | --- |
| `governance_pass` | Required process checks passed: role, scope, lifecycle, filesystem, result format, audit routing, and checkpoint policy. | The product capability works. |
| `task_pass` | A bounded task met its task packet acceptance criteria and required audit path. | The whole capability or product is ready. |
| `capability_pass` | One named capability ID has complete accepted evidence for its declared scope. | Other capabilities or full product readiness passed. |
| `product_pass` | All capability IDs required for the current product gate passed and integration evidence is accepted. | MVP is ready unless the MVP gate says so. |
| `mvp_ready` | The accepted MVP boundary is satisfied by passed capabilities, tests, documentation, and known limitation handling. | Final project acceptance or launch approval. |
| `final_acceptance` | The orchestrator-controlled final acceptance gate has accepted product, documentation, handover, and owner-facing evidence. | A profile agent can self-complete the project. |

`skeleton` is an implementation maturity label, not a product readiness gate.
A skeleton pass, scaffolding pass, CLI smoke pass, or placeholder workflow pass
must not be recorded as `mvp_ready`, `product_pass`, or
`final_acceptance` unless the product gates below are also satisfied.

## Capability Matrix Format

Product readiness must be tracked with a capability matrix when a project
claims `capability_pass`, `product_pass`, `mvp_ready`, or
`final_acceptance`.

Minimum matrix fields:

```text
CAPABILITY_ID:
CAPABILITY_NAME:
PRODUCT_SCOPE:
TASK_PACKET_REFS:
REQUIREMENT_REFS:
SKELETON_STATUS: not_started | partial | passed | not_applicable
TASK_STATUS: not_started | in_progress | task_pass | blocked | failed | not_applicable
CAPABILITY_STATUS: not_started | partial | capability_pass | blocked | failed | deferred
PRODUCT_GATE_STATUS: not_started | partial | product_pass | blocked | failed | deferred
MVP_REQUIRED: yes | no
FINAL_ACCEPTANCE_REQUIRED: yes | no
EVIDENCE_REFS:
AUDIT_REFS:
TEST_REFS:
DOC_REFS:
OPEN_GAPS:
LIMITATIONS:
OWNER_DECISION_REFS:
LAST_UPDATED:
```

Markdown table form is acceptable when it preserves the same fields:

| CAPABILITY_ID | TASK_PACKET_REFS | SKELETON_STATUS | TASK_STATUS | CAPABILITY_STATUS | PRODUCT_GATE_STATUS | MVP_REQUIRED | EVIDENCE_REFS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CAP_AUTH_001` | `TASK_DEV_AUTH_001` | `passed` | `task_pass` | `partial` | `partial` | `yes` | `result + audit refs` |

Rules:

- capability IDs must be stable within the active project scope;
- every `capability_pass` must cite accepted task, audit, and verification
  evidence;
- every `product_pass` must cite the capability IDs included in the product
  gate and the integration evidence that connects them;
- every `mvp_ready` claim must cite the accepted `MVP_BOUNDARY`, required
  capability IDs, non-goals, limitations, tests, and documentation evidence;
- every `final_acceptance` claim must cite `mvp_ready` or a stricter accepted
  product gate plus handover/final acceptance evidence;
- unknown, deferred, blocked, or failed capabilities must remain visible and
  must not be hidden by a task or governance pass.

## Required Gate Order

The allowed readiness progression is:

```text
governance_pass -> task_pass -> capability_pass -> product_pass -> mvp_ready -> final_acceptance
```

Some tasks are governance-only or documentation-only and never claim product
capability. Such tasks may stop at `governance_pass` or `task_pass` and record
`CAPABILITY_STATUS: not_applicable` with a reason.

Product gates must be checked before final acceptance. The orchestrator must
not route to `final_acceptance` when any MVP-required capability is missing,
blocked, failed, unaudited, undocumented where documentation is required, or
represented only by skeleton/scaffold evidence.

## Task Packet Mapping

Task packets may map to capability IDs without changing the dispatchable task
packet schema. The mapping may appear in `PURPOSE`, `SCOPE_IN`,
`ACCEPTANCE_CRITERIA`, `EVIDENCE_REQUIREMENTS`, or `NOTES`.

Recommended wording:

```text
Capability mapping:
- CAPABILITY_ID: CAP_AUTH_001
- CAPABILITY_MATRIX_REF: project-docs/.../CAPABILITY_MATRIX.md
- GATE_INTENT: task_pass only; no product_pass or mvp_ready claim
```

Task packets must not claim `capability_pass`, `product_pass`, `mvp_ready`, or
`final_acceptance` unless the required matrix row and evidence refs are part of
their acceptance criteria or downstream gate evidence.

## Examples

Skeleton-only result:

```text
SKELETON_STATUS: passed
TASK_STATUS: task_pass
CAPABILITY_STATUS: partial
PRODUCT_GATE_STATUS: partial
MVP_READY: false
```

This is valid when the task packet asked only for scaffold creation. It is not
MVP-ready.

Capability pass:

```text
CAPABILITY_ID: CAP_IMPORT_001
TASK_PACKET_REFS:
- TASK_DEV_IMPORT_001
- TASK_TEST_IMPORT_001
CAPABILITY_STATUS: capability_pass
EVIDENCE_REFS:
- project-runtime/results/worker/RESULT_TASK_DEV_IMPORT_001_ATTEMPT_1.md
- project-runtime/results/audit/AUDIT_RESULT_TASK_DEV_IMPORT_001_ATTEMPT_1.md
- project-runtime/results/worker/RESULT_TASK_TEST_IMPORT_001_ATTEMPT_1.md
```

Product pass:

```text
PRODUCT_GATE_STATUS: product_pass
CAPABILITY_IDS:
- CAP_IMPORT_001
- CAP_EXPORT_001
INTEGRATION_EVIDENCE_REFS:
- project-runtime/results/worker/RESULT_TASK_TEST_IMPORT_EXPORT_FLOW_001_ATTEMPT_1.md
MVP_READY: false
```

This is a product slice pass, not MVP readiness, unless the accepted MVP
boundary says these are all MVP-required capabilities and all MVP evidence is
accepted.

Final acceptance candidate:

```text
MVP_READY: true
FINAL_ACCEPTANCE: pending
FINAL_ACCEPTANCE_REQUIRED_REFS:
- accepted capability matrix
- accepted test report
- accepted documentation/handover evidence
- owner decisions or explicit none
```

`FINAL_ACCEPTANCE: passed` is allowed only after the final acceptance gate
checks those refs.

Additional examples are maintained in:

```text
agent-system/10_examples/PRODUCT_CAPABILITY_GATE_EXAMPLES.md
```

## Lint And Report Behavior

`aso lint` currently implements a conservative skeleton/product guard:

```text
LINT_PRODUCT_001
```

It reports an error when a task packet, result, or runtime file records
`SKELETON_STATUS: passed` or a positive `SKELETON_PASS` value together with a
positive product/MVP/final marker such as `CAPABILITY_PASS`, `PRODUCT_PASS`,
`PRODUCT_STATUS`, `MVP_READY`, `MVP_STATUS`, or `FINAL_ACCEPTANCE`.

Current lint behavior is read-only. It reports findings and must not mutate
task packets, results, runtime files, or capability matrices.

Queued report behavior for a future bounded tooling task:

- detect missing capability matrix refs when `capability_pass`,
  `product_pass`, `mvp_ready`, or `final_acceptance` is claimed;
- report MVP-required capability rows that are blocked, failed, missing audit
  refs, or represented only by skeleton evidence;
- include a product gate summary in read-only ASO reports without changing
  runtime state.
