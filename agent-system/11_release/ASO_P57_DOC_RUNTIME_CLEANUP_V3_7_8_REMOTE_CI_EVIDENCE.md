# ASO P57 v3.7.8 Remote CI Evidence

## Status

```text
REPORT_STATUS: final_pushed_head_remote_ci_evidence_selector_committed
BRANCH: correction/aso-p57-doc-runtime-cleanup-v3.7.8
TARGET_HEAD: final pushed commit containing this evidence file
GITHUB_ACTIONS_RUN: select completed run after push where headSha == TARGET_HEAD
WORKFLOW: ASO Package Governance
REQUIRED_CONCLUSION: success
RUN_ID_RECORDING_POLICY: do not commit post-push run id because that would create a newer HEAD
```

## Evidence Rule

The final pushed HEAD for
`correction/aso-p57-doc-runtime-cleanup-v3.7.8` is the commit containing this
evidence file after it is committed and pushed. Remote CI evidence is acceptable
only when GitHub Actions has a completed run for workflow
`ASO Package Governance` where `headSha` equals that final pushed HEAD and
`conclusion` equals `success`.

The selected run id, timestamps, URL, and matching `headSha` are recorded in the
release-manager RESULT after the run exists. They are intentionally not
committed here: committing those post-push values would create a newer HEAD and
make the committed evidence stale again.

## Final-Head Selection Commands

```bash
TARGET_HEAD="$(git rev-parse HEAD)"
gh run list \
  --branch correction/aso-p57-doc-runtime-cleanup-v3.7.8 \
  --workflow "ASO Package Governance" \
  --limit 5
gh run view "$SELECTED_RUN_ID" \
  --json databaseId,headSha,headBranch,name,conclusion,status,createdAt,updatedAt,url,event,workflowName
```

Accept the selected run only if:

```text
headBranch == correction/aso-p57-doc-runtime-cleanup-v3.7.8
headSha == TARGET_HEAD
workflowName == ASO Package Governance
status == completed
conclusion == success
```

## Pre-Push Baseline

The previous P57 Task 090 release validation push completed successfully before
this evidence-sequencing correction:

```text
BRANCH: correction/aso-p57-doc-runtime-cleanup-v3.7.8
HEAD: 4b8fb045261e7c4236e34be462e30902169df10c
GITHUB_ACTIONS_RUN: 26366531038
WORKFLOW: ASO Package Governance
CONCLUSION: success
DATE: 2026-05-24T16:28:36Z
```

This pre-push baseline is not the final evidence-sequencing correction remote CI
evidence. The final correction evidence must be selected by the final-head rule
above after this file is committed and pushed.
