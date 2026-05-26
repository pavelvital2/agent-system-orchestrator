# ASO P58F1 v3.7.9 Remote CI Evidence Procedure

## Status

```text
REPORT_STATUS: final_pushed_head_remote_ci_evidence_selector_committed
BRANCH: correction/aso-p58-no-upgrade-working-state-fixpack-v3.7.9
TARGET_HEAD: final pushed task-110 commit containing this evidence file
GITHUB_ACTIONS_RUN: select completed run after push where headSha == TARGET_HEAD
WORKFLOW: ASO Package Governance
REQUIRED_CONCLUSION: success
RUN_ID_RECORDING_POLICY: record run id/head/status/URL in external release/audit RESULT only
```

## Evidence Rule

The final pushed HEAD for
`correction/aso-p58-no-upgrade-working-state-fixpack-v3.7.9` is the commit
containing this evidence file after it is committed and pushed. Remote CI
evidence is acceptable only when GitHub Actions has a completed run for
workflow `ASO Package Governance` where `headSha` equals that final pushed HEAD
and `conclusion` equals `success`.

The selected run id, matching final HEAD, status, URL, and matrix result are
recorded in the external release/audit RESULT after the run exists. They are
intentionally not committed here: committing post-push values would create a
newer HEAD and make the committed evidence stale again.

## Final-Head Selection Commands

```bash
TARGET_HEAD="$(git rev-parse HEAD)"
gh run list \
  --repo pavelvital2/agent-system-orchestrator \
  --branch correction/aso-p58-no-upgrade-working-state-fixpack-v3.7.9 \
  --workflow "ASO Package Governance" \
  --limit 10
gh run view "$SELECTED_RUN_ID" \
  --repo pavelvital2/agent-system-orchestrator \
  --json databaseId,headSha,headBranch,name,conclusion,status,createdAt,updatedAt,url,event,workflowName,jobs
```

Accept the selected run only if:

```text
headBranch == correction/aso-p58-no-upgrade-working-state-fixpack-v3.7.9
headSha == TARGET_HEAD
workflowName == ASO Package Governance
status == completed
conclusion == success
Python 3.10 matrix job == success
Python 3.11 matrix job == success
Python 3.12 matrix job == success
```

## Pre-Push Baseline

The accepted baseline before task 110 was:

```text
BRANCH: correction/aso-p58-no-upgrade-working-state-fixpack-v3.7.9
HEAD: f1a2a64599a5ca3338d500ab462610176a7cd483
REMOTE_HEAD: f1a2a64599a5ca3338d500ab462610176a7cd483
CI_RUN: 26458283855
CI_RESULT: success
STATUS: baseline only; not final task-110 remote CI evidence
```

The final remote CI evidence must be selected by the final-head rule above
after task 110 changes are committed and pushed.

