from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from artifact_provenance import build_manifest, sha256_file, write_manifest  # noqa: E402


class ArtifactProvenanceTests(unittest.TestCase):
    def test_manifest_binds_dataset_and_outputs_with_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            output = root / "result.csv"
            manifest_path = root / "manifest.json"
            dataset.write_text('{"id":"one"}\n', encoding="utf-8")
            output.write_text("metric,value\nhit_at_5,1.0\n", encoding="utf-8")

            manifest = build_manifest(
                evaluation_name="unit_test",
                project_root=root,
                dataset_path=dataset,
                output_paths=[output],
                configuration={"require_verified": True},
                dataset_counts={"verified_selected_records": 1},
                evidence_status="official_test_candidate",
                evidence_status_reason="unit-test only",
            )
            write_manifest(manifest_path, manifest)

            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["dataset"]["sha256"], sha256_file(dataset))
            self.assertEqual(saved["outputs"][0]["sha256"], sha256_file(output))
            self.assertEqual(saved["evidence_status"], "official_test_candidate")
            self.assertFalse(saved["project_git_is_clean"])


if __name__ == "__main__":
    unittest.main()
