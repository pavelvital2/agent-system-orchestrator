# ASO P4.1 Incident Replay Notes

```text
REPORT_ID: ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_INCIDENT_REPLAY_NOTES
PACKAGE_VERSION: 3.6.1
GOVERNANCE_RULESET_VERSION: 3.6.1
RUNTIME_SCHEMA_VERSION: 3.1.0
DATE: 2026-05-22
```

## Purpose

These notes map the P4.1 incident replay requirements to executable fixtures,
tests, and release validation commands. They are release evidence only; they
do not redefine Runtime Schema `3.1.0` and do not make Markdown runtime views
canonical.

## Incident 001: Workspace Root Checked As Package

Failure mode:

```text
Package-mode validation was requested against a generated workspace root and
reported package-layout blockers instead of the mode mismatch.
```

Corrected behavior:

```text
Invalid mode: package checks were requested for workspace root.
Use --mode workspace.
```

Coverage:

```text
FIXTURE: agent-system/tools/aso/tests/fixtures/hotfix_p4_1/incident_001_workspace_root
TESTS:
- agent-system/tools/aso/tests/test_status.py::StatusCommandTests::test_package_status_rejects_workspace_root_with_mode_guard
- agent-system/tools/aso/tests/test_lint.py::LintCommandTests::test_package_lint_rejects_workspace_root_with_mode_guard
- agent-system/tools/aso/tests/test_doctor.py::DoctorCommandTests::test_package_doctor_rejects_workspace_root_with_mode_guard
COMMANDS:
- python3 agent-system/tools/aso/aso.py status --root agent-system/tools/aso/tests/fixtures/hotfix_p4_1/incident_001_workspace_root --mode workspace
- python3 agent-system/tools/aso/aso.py status --root agent-system/tools/aso/tests/fixtures/hotfix_p4_1/incident_001_workspace_root --mode package
```

Expected replay result: workspace mode is the valid mode for the generated
workspace fixture; package mode fails with a mode error and workspace-mode
recommendation.

## Incident 002: JSON Sidecars Without Markdown Views

Failure mode:

```text
Valid Runtime Schema 3.1.0 JSON sidecars existed, but required
project-runtime/*.md compatibility views were absent and no repair path was
clear.
```

Corrected behavior:

```text
Runtime markdown views are missing but JSON sidecars are valid.
Run aso state render --root WORKSPACE --confirm-write.
```

Coverage:

```text
TEST:
- agent-system/tools/aso/tests/test_state_render.py::StateRenderCommandTests::test_confirm_write_materializes_markdown_views_from_json_sidecars
COMMANDS:
- python3 agent-system/tools/aso/aso.py state init --root /tmp/aso-p41-materialize --project-slug p41-materialize --confirm-write
- python3 agent-system/tools/aso/aso.py lint --root /tmp/aso-p41-materialize --mode workspace --strict
- python3 agent-system/tools/aso/aso.py state render --root /tmp/aso-p41-materialize --confirm-write
- python3 agent-system/tools/aso/aso.py lint --root /tmp/aso-p41-materialize --mode workspace --strict
- python3 agent-system/tools/aso/aso.py doctor --root /tmp/aso-p41-materialize --mode workspace --strict
```

Expected replay result: strict lint fails before materialization with
`LINT_IO_004` and the render repair command; after `state render
--confirm-write`, derived Markdown views exist, include the derived-view
banner, and strict workspace lint/doctor pass.

## Incident 003: RESULT Routed Before Agent Termination

Failure mode:

```text
A profile-agent RESULT could proceed toward audit routing without an explicit
agent termination lifecycle event.
```

Corrected behavior:

```text
RESULT_RECEIVED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

Coverage:

```text
TESTS:
- agent-system/tools/aso/tests/test_lifecycle.py::LifecycleCommandTests::test_terminate_agent_writes_agent_terminated_event
- agent-system/tools/aso/tests/test_lifecycle.py::LifecycleCommandTests::test_terminate_agent_requires_existing_result
- agent-system/tools/aso/tests/test_lint.py lifecycle LINT_AGENT_003 positive and negative guards
COMMANDS:
- python3 agent-system/tools/aso/aso.py lifecycle terminate-agent --root WORKSPACE --from-result project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md --confirm-write
- python3 agent-system/tools/aso/aso.py lint --root WORKSPACE --mode workspace --strict
```

Expected replay result: a RESULT without a matching termination event fails
`LINT_AGENT_003`; a matching `AGENT_TERMINATED` event with the same task,
agent instance, and result reference allows strict workspace lint to proceed.
Wrong task IDs or result references remain blockers.

## Release Validation Commands

The final P4.1 validation report records the release-level execution of:

```bash
make test
make smoke
bash install.sh
make verify-install
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict
git diff --check
git ls-files project-input project-runtime project-archive .venv
```
