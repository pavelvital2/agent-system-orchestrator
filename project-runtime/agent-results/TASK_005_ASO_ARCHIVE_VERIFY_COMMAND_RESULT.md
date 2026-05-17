# RESULT

TASK_ID: TASK_005_ASO_ARCHIVE_VERIFY_COMMAND

AGENT_INSTANCE_ID: codex_TASK_005_ASO_ARCHIVE_VERIFY_COMMAND_attempt_001

SUMMARY:
Implemented read-only `aso archive verify` for `.zip`, `.tgz`, `.tar.gz`, and
`.tar`. It checks archive readability, required directories, manifest
presence/validity, accepted artifact inclusion or manifest exclusion with
reason, commit hash evidence, and classifies missing product/code folders as
`packaging_error` when runtime evidence says they should be included. Added
`--json-out`.

CHANGED_FILES:
- agent-system/tools/aso/aso.py
- agent-system/tools/aso/commands/archive_verify.py
- agent-system/tools/aso/tests/test_archive_verify.py

COMMANDS_RUN:
- `sed -n ... TASK_005_ASO_ARCHIVE_VERIFY_COMMAND.md`
- `sed -n ... 08_ASO_CLI_SPEC.md`
- `python3 -m py_compile agent-system/tools/aso/aso.py agent-system/tools/aso/commands/archive_verify.py`
- `python3 agent-system/tools/aso/aso.py archive verify --help`
- `git diff --check`
- `git status --short`

TESTS_RUN:
- `python3 -m unittest agent-system/tools/aso/tests/test_archive_verify.py` passed.
- `python3 -m unittest discover agent-system/tools/aso/tests` passed, 13 tests.

RISKS:
- Manifest schema is intentionally flexible because no canonical archive
  manifest schema exists yet.
- `python` is not installed in this environment; verification used `python3`.

LIMITATIONS:
- `generated_at` ordering after checkpoint is not enforced because TASK_005 did
  not require it and runtime timestamp semantics are not canonical yet.
- Archive exclusions require a manifest reason to be treated as explicit.

REUSE_ALLOWED: false

AGENT_TERMINATION_REQUIRED: true

AGENT_TERMINATION_EVIDENCE:
The orchestrator closed profile agent `019e3790-1ecc-7c00-a36d-2b6d9ad5f33c`
after receiving this RESULT. The agent must not be reused.
