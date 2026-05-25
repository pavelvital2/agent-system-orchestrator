# ASO Proposal Apply P3 v3.5.0 Validation Report

```text
REPORT_ID: ASO_PROPOSAL_APPLY_P3_V3_5_0_VALIDATION_REPORT
TASK_ID: TASK_ASO_PA3_100_FINAL_VALIDATION_CLEANUP
AGENT_INSTANCE_ID: TASK_ASO_PA3_100_FINAL_VALIDATION_CLEANUP_PROFILE_AGENT_20260521
AGENT_ROLE: release_manager
DATE: 2026-05-21
BRANCH: upgrade/proposal-apply-p3-v3.5.0
VALIDATION_HEAD_BEFORE_REPORT: 508b8b60a47b9d74e45592b4717f9e08fcf28d12
REMOTE_TRACKING_BRANCH: origin/upgrade/proposal-apply-p3-v3.5.0
REMOTE_HEAD_BEFORE_REPORT: 508b8b60a47b9d74e45592b4717f9e08fcf28d12
FINAL_REPORT_COMMIT_PENDING: yes
REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_ORCHESTRATOR_PUSH: yes
GITHUB_ACTIONS_SUCCESS_CLAIMED: no
PACKAGE_VERSION: 3.5.0
GOVERNANCE_RULESET_VERSION: 3.5.0
RUNTIME_SCHEMA_VERSION: 3.1.0
VALIDATION_STATUS: passed
```

## Summary

Proposal Apply P3 v3.5.0 local validation passed for CLI help coverage,
unit tests, smoke tests, editable install verification, strict package
lint/doctor/package-layout checks, checkpoint preflight, whitespace checks,
publication-boundary tracked-file checks, Runtime Schema 3.1.0
state init/verify/render smoke, P3 proposal/apply dry-runs, confirmed apply in
a temporary workspace, Project Factory reference and vendored creation, clean
repository verification, GitHub dry-run planning, and wizard dry-run planning.

No commit, push, tag, merge, staging operation, owner-root publication, or
`project-input/aso_upgrade_proposal_apply_p3_v3_5_0` cleanup was performed by
the profile agent. GitHub Actions success is not claimed because this report
has not yet been committed and pushed by the orchestrator.

Validation logs were captured under:

```text
/tmp/aso-pa3-100-validation-20260521-204530/
```

## Branch And Commit Evidence

```text
COMMAND: git rev-parse --abbrev-ref HEAD
EXIT_CODE: 0
OUTPUT: upgrade/proposal-apply-p3-v3.5.0

COMMAND: git rev-parse HEAD
EXIT_CODE: 0
OUTPUT: 508b8b60a47b9d74e45592b4717f9e08fcf28d12

COMMAND: git ls-remote origin refs/heads/upgrade/proposal-apply-p3-v3.5.0
EXIT_CODE: 0
OUTPUT: 508b8b60a47b9d74e45592b4717f9e08fcf28d12 refs/heads/upgrade/proposal-apply-p3-v3.5.0

INTERPRETATION: Before this report was created, local HEAD and remote branch
HEAD matched at 508b8b60a47b9d74e45592b4717f9e08fcf28d12. After the
orchestrator commits and pushes this report, remote HEAD and GitHub Actions
must be verified again against the final report commit.
```

## Local Validation Evidence

```text
COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
EXIT_CODE: 0
OUTCOME: passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py propose --help
EXIT_CODE: 0
OUTCOME: passed; next-task, transition, and checkpoint subcommands are exposed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py apply --help
EXIT_CODE: 0
OUTCOME: passed; --proposal, --dry-run, --confirm-apply, and --json-out are exposed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make test
EXIT_CODE: 0
OUTCOME: passed; SOURCE_HYGIENE_RESULT passed; 249 ASO tool tests passed; 5 agent-system tests passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make smoke
EXIT_CODE: 0
OUTCOME: passed; package status, strict lint, strict doctor, package-layout verify, validators, state verify/render, plan-next, dashboard, checkpoint-preflight, and governance smoke passed. Governance smoke result: passed, 18 assertions.

COMMAND: PYTHONDONTWRITEBYTECODE=1 bash install.sh
EXIT_CODE: 0
OUTCOME: passed; editable install completed under .venv for agent_system_orchestrator 3.5.0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make verify-install
EXIT_CODE: 0
OUTCOME: passed; installed CLI and strict package checks passed from .venv.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
EXIT_CODE: 0
OUTCOME: passed; canonical package path and root duplicate package check passed, findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; ELIGIBLE dry-run/read-only; blocking rules 0; warnings 0.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed before report creation; no whitespace errors.

COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty
OUTCOME: passed; no owner roots, runtime roots, archive roots, or .venv paths are tracked.
```

## Smoke Example Evidence

```text
COMMAND: state init/verify/render in /tmp
EXIT_CODE: 0
OUTCOME: passed; state init wrote 9 Runtime Schema 3.1.0 sidecars in a temporary workspace, strict state verify passed, and markdown render was written.

COMMAND: propose next-task dry-run with JSON validation
EXIT_CODE: 0
OUTCOME: passed; proposal JSON was written under /tmp and parsed by python3 -m json.tool.

COMMAND: propose transition dry-run with JSON validation
EXIT_CODE: 0
OUTCOME: passed; p2_valid_workspace fixture gate evidence was marked passed in /tmp, transition proposal JSON was written under /tmp, and JSON parsing passed.

COMMAND: propose checkpoint dry-run with JSON validation
EXIT_CODE: 0
OUTCOME: passed; checkpoint proposal JSON was written under /tmp and parsed by python3 -m json.tool.

COMMAND: apply dry-run with JSON validation
EXIT_CODE: 0
OUTCOME: passed; apply plan JSON was written under /tmp and parsed by python3 -m json.tool.

COMMAND: confirmed apply in temporary workspace
EXIT_CODE: 0
OUTCOME: passed; a valid next-task proposal was generated from the P3 valid workspace fixture, --confirm-apply wrote one receipt and project-runtime/reports/next-task-proposal.json inside the temporary workspace, receipt JSON parsed, and strict state verify passed after apply.

COMMAND: project create --local --engine-mode reference and project verify-clean --strict
EXIT_CODE: 0
OUTCOME: passed; reference project created in /tmp and clean verification reported tracked forbidden paths 0 and violations 0.

COMMAND: project create --local --engine-mode vendored and project verify-clean --strict
EXIT_CODE: 0
OUTCOME: passed; vendored project created in /tmp and clean verification reported tracked forbidden paths 0, nested Git paths 0, and violations 0.

COMMAND: project create --github --dry-run --engine-mode reference with JSON validation
EXIT_CODE: 0
OUTCOME: passed; GitHub plan JSON was written under /tmp and parsed by python3 -m json.tool; no live repository creation, git commit, or push was performed.

COMMAND: wizard --answers "$ANSWERS" --dry-run --json-out "$PLAN" with JSON validation
EXIT_CODE: 0
OUTCOME: passed; wizard GitHub/reference dry-run plan JSON was written under /tmp, parsed by python3 -m json.tool, and the target project directory remained absent.
```

One initial transition smoke using `agent-system/tests/fixtures/proposal_apply_p3/valid_workspace`
returned exit 1 while writing schema-valid blocked proposal JSON because the
fixture had no transition gate evidence. That was treated as a valid negative
guard observation, then the happy-path transition dry-run above was rerun using
the P2 transition fixture with gate evidence marked passed under `/tmp`.

## Publication Boundary

Publication boundary rules checked:

```text
Forbidden package publication roots:
- project-input/**
- project-runtime/**
- project-archive/**
- .venv/**

Allowed package roots include:
- README.md
- README_INSTALL.md
- Makefile
- install.sh
- install.ps1
- pyproject.toml
- .github/**
- .devcontainer/**
- agent-system/**
```

```text
COMMAND: git ls-files project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: empty
PUBLICATION_BOUNDARY_STATUS: passed; no forbidden owner/runtime/archive/venv root is tracked.

COMMAND: git status --short project-input project-runtime project-archive .venv
EXIT_CODE: 0
OUTPUT: ?? .venv/
INTERPRETATION: .venv was created by the required install validation and remains untracked. It is a local cleanup item for the orchestrator after audit/checkpoint/commit/push/CI observation.
```

The owner input package `project-input/aso_upgrade_proposal_apply_p3_v3_5_0`
was not removed. Runtime proposal/apply smoke artifacts were created only in
temporary workspaces under `/tmp`.

## Cleanup Handoff

Profile-agent cleanup intentionally not performed:

```text
project-input/aso_upgrade_proposal_apply_p3_v3_5_0
.venv
```

After final audit pass, checkpoint, commit, push, remote HEAD verification, and
GitHub Actions observation, the orchestrator should perform the documented
cleanup:

```bash
rm -rf project-input/aso_upgrade_proposal_apply_p3_v3_5_0
rm -rf .venv
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
git status --short
git ls-files project-input project-runtime project-archive .venv
```

## Residual Risks

```text
REMOTE_HEAD_AFTER_FINAL_PUSH: not verified by profile agent; orchestrator must verify after committing and pushing this report.
GITHUB_ACTIONS_FINAL_STATUS: not claimed by profile agent; orchestrator must observe the final pushed workflow run before final success claim.
LOCAL_UNTRACKED_VENV: present after required install validation; must remain untracked and should be removed by orchestrator during final cleanup.
OWNER_INPUT_PACKAGE: preserved as required; must remain local/untracked until orchestrator cleanup.
```
