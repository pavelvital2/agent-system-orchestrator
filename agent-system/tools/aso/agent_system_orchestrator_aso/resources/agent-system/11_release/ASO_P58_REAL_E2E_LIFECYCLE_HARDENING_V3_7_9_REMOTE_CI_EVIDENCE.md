# ASO P58 v3.7.9 Remote CI Evidence

## Status

```text
REPORT_STATUS: final_pushed_head_remote_ci_evidence_selector_committed
BRANCH: correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9
TARGET_HEAD: final pushed commit containing this evidence file
GITHUB_ACTIONS_RUN: select completed run after push where headSha == TARGET_HEAD
WORKFLOW: ASO Package Governance
REQUIRED_CONCLUSION: success
RUN_ID_RECORDING_POLICY: do not commit post-push run id because that would create a newer HEAD
```

## Evidence Rule

The final pushed HEAD for
`correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9` is the commit
containing this evidence file after it is committed and pushed. Remote CI
evidence is acceptable only when GitHub Actions has a completed run for
workflow `ASO Package Governance` where `headSha` equals that final pushed HEAD
and `conclusion` equals `success`.

The selected run id, timestamps, URL, and matching `headSha` are recorded in
the release RESULT after the run exists. They are intentionally not committed
here: committing those post-push values would create a newer HEAD and make the
committed evidence stale again.

## Final-Head Selection Commands

```bash
TARGET_HEAD="$(git rev-parse HEAD)"
gh run list \
  --branch correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9 \
  --workflow "ASO Package Governance" \
  --limit 5
gh run view "$SELECTED_RUN_ID" \
  --json databaseId,headSha,headBranch,name,conclusion,status,createdAt,updatedAt,url,event,workflowName
```

Accept the selected run only if:

```text
headBranch == correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9
headSha == TARGET_HEAD
workflowName == ASO Package Governance
status == completed
conclusion == success
```

## Pre-Push Baseline

The previous committed P58 task baseline before task 110 was:

```text
BRANCH: correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9
HEAD: 305ca9b4
REMOTE: origin/correction/aso-p58-real-e2e-lifecycle-hardening-v3.7.9
STATUS: baseline only; not final task-110 remote CI evidence
```

The final remote CI evidence must be selected by the final-head rule above
after task 110 changes are committed and pushed.
