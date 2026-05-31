# ASO Stage 1 Defect Remediation v3.8.0 Remote CI Evidence Procedure

## Status

```text
REPORT_STATUS: final_pushed_head_remote_ci_evidence_selector_committed
BRANCH: correction/aso-stage1-defect-remediation-v3.8.0
BASE_EVIDENCE_HEAD: 5e90edffdba8872543ce663f2ffb4cefab8e21e5
TARGET_HEAD: final pushed S1_180 commit containing this evidence file
GITHUB_ACTIONS_RUN: select completed run after push where headSha == TARGET_HEAD
WORKFLOW: ASO Package Governance
REQUIRED_CONCLUSION: success
RUN_ID_RECORDING_POLICY: record run id/head/status/URL in external release/audit RESULT only
```

## Evidence Rule

The implementation agent for S1_180 must not commit or push. Therefore this
file is a selector/procedure for the orchestrator, tester, or auditor after the
real S1_180 commit is pushed.

Accept remote CI only when GitHub Actions has a completed run for workflow
`ASO Package Governance` where:

```text
headBranch == correction/aso-stage1-defect-remediation-v3.8.0
headSha == TARGET_HEAD
workflowName == ASO Package Governance
status == completed
conclusion == success
Python 3.10 matrix job == success
Python 3.11 matrix job == success
Python 3.12 matrix job == success
```

## Selection Commands

```bash
TARGET_HEAD="$(git rev-parse HEAD)"
gh run list \
  --repo pavelvital2/agent-system-orchestrator \
  --branch correction/aso-stage1-defect-remediation-v3.8.0 \
  --workflow "ASO Package Governance" \
  --limit 10
gh run view "$SELECTED_RUN_ID" \
  --repo pavelvital2/agent-system-orchestrator \
  --json databaseId,headSha,headBranch,name,conclusion,status,createdAt,updatedAt,url,event,workflowName,jobs
```

## Current Remote Baseline Before S1_180 Commit

At S1_180 implementation start, local and remote branch heads matched:

```text
HEAD: 5e90edffdba8872543ce663f2ffb4cefab8e21e5
REMOTE_HEAD: 5e90edffdba8872543ce663f2ffb4cefab8e21e5
LATEST_REMOTE_WORKFLOW_OBSERVED: run 26711093846 for TASK_ASO_S1_170, completed success, 8m9s, created 2026-05-31T11:16:18Z
```

That baseline run is not S1_180 evidence. The S1_180 CI run must be selected
after the release evidence commit is pushed.
