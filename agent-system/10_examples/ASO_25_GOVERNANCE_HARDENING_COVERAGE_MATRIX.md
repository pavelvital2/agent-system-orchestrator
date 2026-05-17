# ASO 25 Governance Hardening Coverage Matrix

TOTAL_FIXES: 25
REQUIRED_COVERAGE: 25/25

This tracked smoke fixture records the v2.0.0 governance hardening coverage
surface so `run_governance_smoke_tests.sh` is reproducible from committed
package files only.

| Fix | Coverage area | Smoke or rule evidence |
| --- | --- | --- |
| 1 | workspace identity gate | wrong_remote fixture blocks repository mismatch |
| 2 | workspace identity manifest fields | project_state fixtures include expected and actual identity fields |
| 3 | repository lock default push policy | push_not_allowed fixture blocks push without accepted lock |
| 4 | workspace type behavior | package_repo fixtures exercise package-specific path rules |
| 5 | wrong remote and branch blockers | wrong_remote and wrong_branch fixtures block checkpoint |
| 6 | canonical GitHub remote comparison | https and git SSH canonical forms compare by owner/repo |
| 7 | identity leakage blocker | package workspace fixture prevents project-doc pollution |
| 8 | owner-approved SSH aliases | approved_ssh_alias fixture accepts bounded alias evidence |
| 9 | checkpoint eligibility separation | preflight receipt separates audit and checkpoint status |
| 10 | preflight before staging | smoke uses dry-run preflight before any git add |
| 11 | changed file allowlist | fixture task packets constrain ALLOWED_FILE_CHANGES |
| 12 | forbidden file scope | preflight checks FORBIDDEN_FILE_CHANGES before checkpoint |
| 13 | package repo project-doc guard | package_repo_with_project_docs fixture blocks project-docs changes |
| 14 | active task packet schema | preflight invokes validate_task_packet.py |
| 15 | full mandatory task sections | smoke-generated packets include full template sections |
| 16 | invalid task packet blocker | invalid_task_packet fixture reports invalid_task_packet_schema |
| 17 | task proposal non-dispatchability | validator rules classify proposals separately from packets |
| 18 | runtime schema checkpoint fields | preflight checks checkpoint runtime schema fields |
| 19 | secret path scan | secret_file_present fixture blocks sensitive path |
| 20 | secret content scan | preflight scans bounded text content for credential patterns |
| 21 | push policy validation | push_requested fixtures validate PUSH_ALLOWED and lock status |
| 22 | no network push in smoke | smoke uses local dry-run temporary repositories only |
| 23 | version tuple coherence | smoke verifies package, governance, and runtime versions are 2.0.0 |
| 24 | accepted changelog status | smoke requires accepted v2.0.0 changelog entries |
| 25 | reproducible tracked coverage | this tracked matrix asserts 25/25 coverage |
