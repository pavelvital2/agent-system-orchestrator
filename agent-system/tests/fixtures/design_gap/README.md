# DG4 design gap fixtures

These fixtures exercise corrected P4 design/gap governance without relying on
network access, secrets, live GitHub state, semantic TZ reading, or external
workers.

## Valid package

`valid_workspace` is a minimal designer-authored package:

- one accepted gap register;
- one audited owner-facing question card;
- one deferred owner-input gap that may continue through design;
- no owner answer yet.

`blocked_workspace` uses the same package shape but marks the gap as waiting for
owner input so implementation-stage gate verification must block until an answer
or accepted assumption exists.

## Negative packages

Each directory under `negative/` contains one intentionally invalid condition and
is expected to fail the validator or stage gate with the named rule.

| Fixture | Expected rule | Invalid condition |
| --- | --- | --- |
| `technical_question` | `DG4_QUESTION_008` | Owner card asks an engineering implementation question. |
| `missing_recommendation` | `DG4_QUESTION_004` | Owner card has no designer recommendation. |
| `missing_rationale` | `DG4_QUESTION_006` | Owner card has no plain-language recommendation reason. |
| `missing_blocking_stage` | `DG4_QUESTION_007`, `DG4_GAP_002` | Question and gap omit a concrete blocking stage. |
| `unanswered_blocking_gap_crossing_stage` | `DG4_GATE_002` | Gate attempts to enter the gap's blocking stage before owner answer or assumption. |
| `unaudited_question_presentation` | `DG4_AUDIT_001` | Question is presented/current without audit-pass evidence. |
| `orphan_owner_decision` | `DG4_ANSWER_004` | Owner decision record references a missing question. |
