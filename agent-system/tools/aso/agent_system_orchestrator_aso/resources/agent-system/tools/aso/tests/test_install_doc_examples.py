from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ACTIVE_DOCS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "README_INSTALL.md",
    REPO_ROOT / "agent-system" / "README.md",
)

FORBIDDEN_ACTIVE_MANIFEST_PATTERNS = (
    re.compile(r"artifacts/candidates/.*/artifact_package_manifest\.json"),
    re.compile(r"candidates/TASK_ID/artifact_package_manifest\.json"),
)


class InstallDocExampleTests(unittest.TestCase):
    def test_active_docs_use_canonical_manifest_path(self) -> None:
        for doc in ACTIVE_DOCS:
            text = doc.read_text(encoding="utf-8")
            with self.subTest(doc=str(doc.relative_to(REPO_ROOT))):
                self.assertIn("manifest.json", text)
                for pattern in FORBIDDEN_ACTIVE_MANIFEST_PATTERNS:
                    self.assertIsNone(pattern.search(text))

    def test_install_doc_real_tz_workflow_cleans_install_paths_before_clean_install(self) -> None:
        text = (REPO_ROOT / "README_INSTALL.md").read_text(encoding="utf-8")

        self.assertIn(
            'rm -rf "$WORK" /tmp/aso_clean_install_venv /tmp/aso_clean_install_src',
            text,
        )
        self.assertIn(
            'install_aso_clean.sh --source "$ASO_ROOT" --venv /tmp/aso_clean_install_venv --fresh --source-copy /tmp/aso_clean_install_src --with-test',
            text,
        )


if __name__ == "__main__":
    unittest.main()
