# ASO Project Factory P0 v3.2.0 Validation Report

```text
REPORT_ID: ASO_PROJECT_FACTORY_P0_V3_2_0_VALIDATION_REPORT
TASK_ID: TASK_ASO_PF_070_FINAL_VALIDATION_CLEANUP
AGENT_INSTANCE_ID: TASK_ASO_PF_070_FINAL_VALIDATION_CLEANUP_PROFILE_AGENT_20260521
DATE: 2026-05-21
BRANCH: upgrade/project-factory-p0-v3.2.0
VALIDATION_HEAD: 0d926964c3286a8176858b5293ff51642c6ce431
REMOTE_TRACKING_BRANCH: origin/upgrade/project-factory-p0-v3.2.0
REMOTE_HEAD_MATCHED_BEFORE_REPORT: yes
FINAL_REPORT_COMMIT_PENDING: yes
REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_ORCHESTRATOR_PUSH: yes
MAIN_MERGE_CLAIMED: no
PACKAGE_VERSION: 3.2.0
GOVERNANCE_RULESET_VERSION: 3.2.0
RUNTIME_SCHEMA_VERSION: 3.0.0
VALIDATION_STATUS: passed
```

## Summary

Project Factory P0 local validation passed for direct ASO command coverage,
package lint/doctor/package-layout checks, tests, smoke, installed-command
verification, generated-project smoke, checkpoint preflight, and
publication-boundary tracked-file checks.

`make verify-install` passed after running `bash install.sh`, which created a
local `.venv` and installed `agent-system-orchestrator-3.2.0` in editable mode.
The local `.venv` was removed after evidence collection and must not be staged
or published.

Per owner instruction for this task, `project-input/aso_upgrade_project_factory_p0`
was not removed by this profile agent. Final local owner-input cleanup remains
orchestrator-owned after this report and audit.

## Branch And Commit Evidence

```text
COMMAND: git branch --show-current
EXIT_CODE: 0
OUTPUT: upgrade/project-factory-p0-v3.2.0

COMMAND: git rev-parse HEAD
EXIT_CODE: 0
OUTPUT: 0d926964c3286a8176858b5293ff51642c6ce431

COMMAND: git status --short --branch
EXIT_CODE: 0
OUTPUT: ## upgrade/project-factory-p0-v3.2.0...origin/upgrade/project-factory-p0-v3.2.0
```

Task commit list on `main..HEAD` before this report:

```text
0d92696 docs(release): document project factory v3.2.0 [TASK_ASO_PF_060]
03f9ee9 chore(install): add bootstrap install support [TASK_ASO_PF_050]
503b6d4 feat(aso): add clean project verification [TASK_ASO_PF_040]
565aadc feat(aso): add local project creation [TASK_ASO_PF_030]
c0b3e4c feat(aso): add aso lock schema [TASK_ASO_PF_020]
21eeaa1 feat(aso): add project factory contract [TASK_ASO_PF_010]
```

## Command Evidence Summary

```text
COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help >/dev/null
EXIT_CODE: 0
OUTCOME: passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py status --root . --mode package
EXIT_CODE: 0
OUTCOME: passed; package consistency PASS; findings 0; generated roots reported project-runtime=absent, project-input=present-untracked, project-archive=absent.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; errors 0, warnings 0, findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
EXIT_CODE: 0
OUTCOME: passed; canonical package agent-system/tools/aso/agent_system_orchestrator_aso; findings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py project create --help >/dev/null
EXIT_CODE: 0
OUTCOME: passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py project verify-clean --help >/dev/null
EXIT_CODE: 0
OUTCOME: passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make test
EXIT_CODE: 0
OUTCOME: passed; source_hygiene passed; 136 ASO tool tests passed; 5 agent-system tests passed.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make smoke
EXIT_CODE: 0
OUTCOME: passed; CLI help, package status, Project Factory help, strict lint, strict doctor, package-layout verify, design/context-pack validators, validate-rules, state verify, plan-next, dashboard render, checkpoint-preflight, and governance smoke passed. Governance smoke result: passed, 18 assertions.

COMMAND: PYTHONDONTWRITEBYTECODE=1 bash install.sh
EXIT_CODE: 0
OUTCOME: passed; built and installed editable wheel `agent_system_orchestrator-3.2.0`, verified ASO package-layout, and reported `ASO editable install complete`.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make verify-install
EXIT_CODE: 0
OUTCOME: passed; `.venv/bin/aso` existed and installed ASO status, Project Factory create/verify-clean help, strict lint, strict doctor, and strict package-layout verification all passed.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed; no whitespace errors before report creation.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed after report creation; no whitespace errors in the uncommitted report.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict --json-out /tmp/aso-project-factory-final-checkpoint-preflight.json
EXIT_CODE: 0
OUTCOME: passed; ELIGIBLE dry-run/read-only; blocking rules 0; warnings 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 make ci
EXIT_CODE: 0
OUTCOME: passed; test, smoke, doctor, lint, and git diff --check completed successfully.
```

## Generated-Project Smoke Evidence

Temporary directory used and removed:

```text
/tmp/tmp.FqdfkKuZu8
```

Create command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py project create --local --target /tmp/tmp.FqdfkKuZu8/demo-project --name "Demo Project" --slug "demo-project" --profile generic --repo-url "https://github.com/example/demo-project.git" --branch main
```

Create output summary:

```text
ASO project create
Target: /tmp/tmp.FqdfkKuZu8/demo-project
Project: Demo Project (demo-project)
Engine mode: vendored
Package version: 3.2.0
Runtime schema: 3.0.0
Created entries:
- .gitignore
- README.md
- agent-system/
- aso.lock
- project-archive/
- project-input/
- project-runtime/
Vendored files: 321
```

Verify command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py project verify-clean --root /tmp/tmp.FqdfkKuZu8/demo-project --strict
```

Verify output:

```text
ASO project verify-clean: PASS
Root: /tmp/tmp.FqdfkKuZu8/demo-project
Lockfile: pass
Gitignore: pass
Repository metadata: skipped_not_git_repo
Package version: 3.2.0
Runtime schema: 3.0.0
Engine mode: vendored
Tracked forbidden paths: 0
Nested Git paths: 0
Violations: 0
```

Essential generated files observed:

```text
/tmp/tmp.FqdfkKuZu8/demo-project/.gitignore
/tmp/tmp.FqdfkKuZu8/demo-project/README.md
/tmp/tmp.FqdfkKuZu8/demo-project/agent-system/README.md
/tmp/tmp.FqdfkKuZu8/demo-project/aso.lock
```

The temporary directory was removed after evidence collection.

## Publication Boundary Evidence

```text
COMMAND: git status --short --untracked-files=all project-input project-runtime project-archive
EXIT_CODE: 0
OUTPUT: empty

COMMAND: git ls-files project-input project-runtime project-archive
EXIT_CODE: 0
OUTPUT: empty
```

Interpretation:

```text
No files under project-input/, project-runtime/, or project-archive/ are staged or tracked.
The local project-input root is still present as ignored owner-input state, matching the task-level instruction that orchestrator performs final owner-input cleanup after this report/audit.
```

## Acceptance Criteria Status

```text
Project create help: pass.
Project verify-clean help: pass.
Generated project create smoke: pass.
Generated project verify-clean strict: pass.
Generated project contains aso.lock, .gitignore, and README: pass.
Generated project nested Git metadata check: pass; verify-clean reported Nested Git paths: 0.
Package version: pass; 3.2.0.
Runtime schema version: pass; 3.0.0.
make test: pass.
make smoke: pass.
make verify-install: pass after `bash install.sh`.
make ci: pass.
Strict lint: pass.
Strict doctor: pass.
Package-layout verify: pass.
Checkpoint preflight: pass, dry-run/read-only eligible.
Publication boundary tracked files: pass; git ls-files output empty.
Main merge: not performed and not claimed.
Commit/push/stage/tag by profile agent: not performed.
```

## Known Limitations And Handoff Items

```text
1. This profile agent did not commit, push, stage, tag, or mutate git state by instruction.
2. This report itself is pending orchestrator audit, commit, checkpoint, and push.
3. Local owner-input cleanup was intentionally not performed by the profile agent. The orchestrator must remove project-input/aso_upgrade_project_factory_p0 after report/audit and then rerun publication-boundary checks.
4. Remote HEAD verification and remote CI cannot be claimed after this uncommitted report until orchestrator-owned push/CI completes.
```
