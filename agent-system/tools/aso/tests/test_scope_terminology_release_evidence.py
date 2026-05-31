from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_SCHEMA_DIR = REPO_ROOT / "agent-system" / "09_validators" / "schemas"
AUTHORITY_MAP = REPO_ROOT / "agent-system" / "02_runtime" / "CONTRACT_AUTHORITY_MAP.md"
README_CONTRACT_SURFACES = {
    "README.md": REPO_ROOT / "README.md",
    "agent-system/README.md": REPO_ROOT / "agent-system" / "README.md",
    "packaged resource agent-system/README.md": (
        REPO_ROOT
        / "agent-system"
        / "tools"
        / "aso"
        / "agent_system_orchestrator_aso"
        / "resources"
        / "agent-system"
        / "README.md"
    ),
}
STALE_DUPLICATE_CONTRACT_MARKER = "no duplicate `3_1_" + "1` contract file is authoritative"
P57_REMOTE_CI = (
    REPO_ROOT
    / "agent-system"
    / "11_release"
    / "ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_REMOTE_CI_EVIDENCE.md"
)
P58_REMOTE_CI = (
    REPO_ROOT
    / "agent-system"
    / "11_release"
    / "ASO_P58_REAL_E2E_LIFECYCLE_HARDENING_V3_7_9_REMOTE_CI_EVIDENCE.md"
)
RELEASE_DOCS_DIR = REPO_ROOT / "agent-system" / "11_release"
S1_180_RELEASE_EVIDENCE_FILES = {
    "ASO_STAGE1_DEFECT_REMEDIATION_V3_8_0_RELEASE_NOTES.md": RELEASE_DOCS_DIR
    / "ASO_STAGE1_DEFECT_REMEDIATION_V3_8_0_RELEASE_NOTES.md",
    "VALIDATION_REPORT.md": RELEASE_DOCS_DIR / "VALIDATION_REPORT.md",
    "REGRESSION_SUMMARY.md": RELEASE_DOCS_DIR / "REGRESSION_SUMMARY.md",
    "REMOTE_CI_EVIDENCE.md": RELEASE_DOCS_DIR / "REMOTE_CI_EVIDENCE.md",
    "STAGE2_READINESS_HANDOFF.md": RELEASE_DOCS_DIR / "STAGE2_READINESS_HANDOFF.md",
}
CURRENT_DUPLICATE_CONTRACT_WORDING = "no duplicate `3_2_0` contract file is authoritative"
STALE_DUPLICATE_CONTRACT_WORDINGS = (
    "duplicate `3_1_1` contract file is authoritative",
    "duplicate contract filename as `3_1_1`",
    "`3_1_1` duplicate-contract wording",
    "`3_1_1` duplicate contract wording",
)


class ScopeTerminologyReleaseEvidenceTests(unittest.TestCase):
    def assertNoStaleDuplicateContractWording(self, label: str, text: str) -> None:
        normalized = re.sub(r"\s+", " ", text)
        for wording in STALE_DUPLICATE_CONTRACT_WORDINGS:
            with self.subTest(file=label, stale_wording=wording):
                self.assertNotIn(wording, normalized)

    def test_e2e_scope_wording_is_filesystem_governance_not_product_generation(self) -> None:
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        install_readme = (REPO_ROOT / "README_INSTALL.md").read_text(encoding="utf-8")
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        for label, text in {
            "README.md": root_readme,
            "README_INSTALL.md": install_readme,
            "Makefile": makefile,
        }.items():
            with self.subTest(file=label):
                self.assertIn("filesystem/governance lifecycle E2E", text)
                self.assertRegex(
                    text,
                    re.compile(r"not\s+.*full automatic\s+product generation", re.IGNORECASE | re.DOTALL),
                )
                self.assertRegex(text, re.compile(r"not\s+.*live runner|not\s+.*live automation", re.IGNORECASE | re.DOTALL))

        self.assertRegex(makefile, re.compile(r"^e2e-real-tz-smoke:", re.MULTILINE))
        self.assertIn("$(MAKE) e2e-real-tz-smoke", makefile)

    def test_runtime_schema_3_2_0_maps_to_historical_3_1_0_contract_file(self) -> None:
        authority_map = AUTHORITY_MAP.read_text(encoding="utf-8")

        self.assertTrue((RUNTIME_SCHEMA_DIR / "runtime_state_3_1_0.contract.json").is_file())
        self.assertFalse((RUNTIME_SCHEMA_DIR / "runtime_state_3_2_0.contract.json").exists())
        self.assertIn("Runtime Schema `3.2.0` continues to use the packaged contract file", authority_map)
        self.assertIn("agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json", authority_map)

        for label, path in README_CONTRACT_SURFACES.items():
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=label):
                self.assertIn("Runtime Schema `3.2.0`", text)
                self.assertIn("runtime_state_3_1_0.contract.json", text)
                self.assertIn(CURRENT_DUPLICATE_CONTRACT_WORDING, text)
                self.assertNotIn(STALE_DUPLICATE_CONTRACT_MARKER, text)
                self.assertNoStaleDuplicateContractWording(label, text)

    def test_s1_180_release_evidence_uses_current_duplicate_contract_wording(self) -> None:
        self.assertEqual(len(S1_180_RELEASE_EVIDENCE_FILES), 5)

        for label, path in S1_180_RELEASE_EVIDENCE_FILES.items():
            with self.subTest(file=label):
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertNoStaleDuplicateContractWording(label, text)

        for label in (
            "ASO_STAGE1_DEFECT_REMEDIATION_V3_8_0_RELEASE_NOTES.md",
            "VALIDATION_REPORT.md",
            "REGRESSION_SUMMARY.md",
        ):
            text = S1_180_RELEASE_EVIDENCE_FILES[label].read_text(encoding="utf-8")
            normalized = re.sub(r"\s+", " ", text)
            with self.subTest(current_wording=label):
                self.assertIn("Runtime Schema `3.2.0`", normalized)
                self.assertIn(CURRENT_DUPLICATE_CONTRACT_WORDING, normalized)

    def test_remote_ci_files_are_selectors_not_committed_final_run_evidence(self) -> None:
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        install_readme = (REPO_ROOT / "README_INSTALL.md").read_text(encoding="utf-8")

        for path in (P57_REMOTE_CI, P58_REMOTE_CI):
            text = path.read_text(encoding="utf-8")
            with self.subTest(remote_ci=path.name):
                self.assertIn("REPORT_STATUS: final_pushed_head_remote_ci_evidence_selector_committed", text)
                self.assertIn("RUN_ID_RECORDING_POLICY: do not commit post-push run id", text)
                self.assertIn("headSha == TARGET_HEAD", text)
                self.assertIn("conclusion == success", text)

        for label, text in {"README.md": root_readme, "README_INSTALL.md": install_readme}.items():
            with self.subTest(file=label):
                self.assertIn("selector/procedure", text)
                self.assertIn("external release/audit RESULT", text)
                self.assertIn("final push", text)
                self.assertRegex(text, re.compile(r"infinite\s+commit/CI", re.IGNORECASE))
                self.assertNotRegex(
                    text,
                    re.compile(
                        r"post-push\s+(?:remote CI|GitHub Actions)\s+evidence"
                        r".{0,160}final pushed HEAD.{0,160}recorded\s+(?:separately\s+)?in"
                        r".{0,160}REMOTE_CI_EVIDENCE\.md",
                        re.IGNORECASE | re.DOTALL,
                    ),
                )
                self.assertNotRegex(
                    text,
                    re.compile(
                        r"in-repository\s+remote CI evidence files?"
                        r".{0,120}(?:record|records|recorded|contain|contains|capture|captures)"
                        r".{0,160}(?:final run id|final HEAD|final pushed HEAD|final post-push HEAD|URL evidence)",
                        re.IGNORECASE | re.DOTALL,
                    ),
                )

    def test_release_docs_do_not_claim_in_repo_remote_ci_final_run_evidence(self) -> None:
        release_docs = sorted(RELEASE_DOCS_DIR.glob("*.md"))
        self.assertGreater(len(release_docs), 0)

        contradiction_patterns = {
            "post-push final head recorded in remote evidence file": re.compile(
                r"post-push\s+(?:GitHub Actions|remote CI)\s+evidence"
                r".{0,160}final pushed HEAD.{0,160}recorded\s+(?:separately\s+)?in"
                r".{0,160}(?:REMOTE_CI_EVIDENCE\.md|remote CI evidence file|post-push evidence file)",
                re.IGNORECASE | re.DOTALL,
            ),
            "remote evidence file described as post-push observation": re.compile(
                r"(?:remote CI evidence|post-push evidence)\s+file"
                r".{0,120}(?:is|as)\s+a\s+post-push\s+observation",
                re.IGNORECASE | re.DOTALL,
            ),
            "final remote ci result recorded only in post-push evidence file": re.compile(
                r"FINAL_REMOTE_CI_FOR_FINAL_PUSHED_HEAD"
                r".{0,160}recorded\s+only\s+in\s+the\s+post-push\s+remote\s+CI\s+evidence\s+file",
                re.IGNORECASE | re.DOTALL,
            ),
            "in-repo evidence file records immutable final run details": re.compile(
                r"(?:in-repository|in-repo|separate)?\s*remote CI evidence files?"
                r".{0,160}(?:record|records|recorded|contain|contains|capture|captures)"
                r".{0,200}(?:final run id|final HEAD|final pushed HEAD|final post-push HEAD|URL evidence)",
                re.IGNORECASE | re.DOTALL,
            ),
        }

        for path in release_docs:
            text = path.read_text(encoding="utf-8")
            self.assertNoStaleDuplicateContractWording(path.name, text)
            for label, pattern in contradiction_patterns.items():
                with self.subTest(file=path.name, contradiction=label):
                    self.assertNotRegex(text, pattern)

        p57_release_notes = (
            RELEASE_DOCS_DIR / "ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_RELEASE_NOTES.md"
        ).read_text(encoding="utf-8")
        p57_validation_report = (
            RELEASE_DOCS_DIR / "ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_VALIDATION_REPORT.md"
        ).read_text(encoding="utf-8")

        for label, text in {
            "ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_RELEASE_NOTES.md": p57_release_notes,
            "ASO_P57_DOC_RUNTIME_CLEANUP_V3_7_8_VALIDATION_REPORT.md": p57_validation_report,
        }.items():
            with self.subTest(file=label):
                self.assertIn("selector/procedure", text)
                self.assertIn("external release/audit RESULT", text)

    def test_current_release_context_is_s1_140_3_8_0(self) -> None:
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        install_readme = (REPO_ROOT / "README_INSTALL.md").read_text(encoding="utf-8")

        self.assertIn("S1.140 enum/schema/version coherence line", root_readme)
        self.assertIn("S1.140 enum/schema/version coherence context", install_readme)
        self.assertIn("governed `3.8.0` package/governance tuple", root_readme)
        self.assertIn("package version `3.8.0`", install_readme)


if __name__ == "__main__":
    unittest.main()
