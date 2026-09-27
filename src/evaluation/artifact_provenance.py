"""Write small, machine-readable provenance manifests for evaluation artefacts.

Scores without their input dataset, source revision and verification state are easy to
copy into a report out of context. This module deliberately keeps that information
next to every evaluation output so that a thesis result can be audited later.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


MANIFEST_SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest without loading a potentially large file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision(project_root: Path) -> str | None:
    """Return the checked-out Git revision, or ``None`` outside a Git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    revision = result.stdout.strip()
    return revision or None


def git_is_clean(project_root: Path) -> bool:
    """Return true only when the project is a Git checkout with no local changes."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return not result.stdout.strip()


def build_manifest(
    *,
    evaluation_name: str,
    project_root: Path,
    dataset_path: Path,
    output_paths: list[Path],
    configuration: dict[str, Any],
    dataset_counts: dict[str, int],
    evidence_status: str,
    evidence_status_reason: str,
) -> dict[str, Any]:
    """Build provenance for a completed evaluator run.

    ``evidence_status`` is deliberately descriptive rather than a score. Callers
    may use ``official_test_candidate`` only after an independently verified TEST
    split was selected and the evaluator was run in its guarded mode.
    """
    resolved_dataset = dataset_path.resolve()
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evaluation_name": evaluation_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_git_revision": git_revision(project_root),
        "project_git_is_clean": git_is_clean(project_root),
        "python_version": sys.version.split()[0],
        "dataset": {
            "path": str(resolved_dataset),
            "sha256": sha256_file(resolved_dataset),
            **dataset_counts,
        },
        "configuration": configuration,
        "outputs": [
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for path in output_paths
            if path.exists()
        ],
        "evidence_status": evidence_status,
        "evidence_status_reason": evidence_status_reason,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
