# RESEARCH_RESULT_TEMPLATE

## Purpose

Use this template for the research-output section of a profile-agent RESULT
when `TASK_KIND: research_dependency`.

The agent must still return the full `AGENT_RESULT_TEMPLATE.md` RESULT. These
fields are additional required research fields for research dependency tasks.

```text
RESEARCH_QUESTION_ID:
<id from research request>

RESEARCH_SUMMARY:
- <concise answer or finding>

SOURCES_USED:
- <bounded path, URL, document ref, command class, or NONE>

EVIDENCE_MATRIX:
- QUESTION: <question id or text>
  SOURCE: <source ref>
  FINDING: <finding>
  CONFIDENCE: low | default | high | maximum
  LIMITATION: <limitation or NONE>

UNRESOLVED_FINDINGS:
- <finding requiring more research, GAP, blocker, or NONE>

RISKS:
- <risk or NONE>

DESIGN_OR_TASK_IMPLICATIONS:
- <implication for requester continuation or NONE>

RECOMMENDED_NEXT_ACTION:
- <advisory action only>
```

## Rules

- `RECOMMENDED_NEXT_ACTION` is advisory and never replaces orchestrator
  routing.
- Research results must cite the allowed sources used.
- Research results must not include secret values.
- Research results must classify owner decisions as GAP and execution obstacles
  as BLOCKER.
- Research results must not be used by requester continuation until an
  independent auditor returns `STATUS: pass`.
