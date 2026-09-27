from __future__ import annotations

"""Generate an honest, shareable readiness report before a thesis defense.

This is a diagnostic, not an evaluator: it never creates labels, locks a
benchmark, starts Streamlit, or downloads a model.  A report separates a
technical-demo warning from a scientific-evidence blocker so a missing Ollama
service cannot be confused with an unverified TEST benchmark.
"""

import argparse
import json
import platform
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "src" / "evaluation"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_OUTPUT = PROCESSED_DIR / "defense_preflight_report.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class Check:
    status: str  # PASS, WARN, BLOCK
    name: str
    detail: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def benchmark_summary(path: Path) -> dict[str, int]:
    records = read_jsonl(path)
    verified = sum(bool(record.get("gold_verified", False)) for record in records)
    test = sum(str(record.get("split", "")).strip().lower() == "test" for record in records)
    verified_test = sum(
        bool(record.get("gold_verified", False))
        and str(record.get("split", "")).strip().lower() == "test"
        for record in records
    )
    return {"total": len(records), "verified": verified, "test": test, "verified_test": verified_test}


def path_check(name: str, path: Path, *, blocker_when_missing: bool = True) -> Check:
    if path.exists():
        return Check("PASS", name, f"Có: {path.relative_to(PROJECT_ROOT)}")
    return Check(
        "BLOCK" if blocker_when_missing else "WARN",
        name,
        f"Thiếu: {path.relative_to(PROJECT_ROOT)}",
    )


def evidence_check(name: str, candidate: Path, reviewed: Path, locked: Path) -> Check:
    if locked.is_file():
        summary = benchmark_summary(locked)
        if summary["total"] and summary["verified"] == summary["total"]:
            return Check("PASS", name, f"TEST locked: {summary['total']} record đã verified.")
        return Check("BLOCK", name, "Có file locked nhưng không chứa toàn bộ record verified.")

    source = reviewed if reviewed.is_file() else candidate
    summary = benchmark_summary(source)
    location = source.relative_to(PROJECT_ROOT) if source.exists() else source.name
    if not summary["total"]:
        return Check("BLOCK", name, f"Chưa tìm thấy dataset review/candidate: {location}")
    return Check(
        "BLOCK",
        name,
        f"Chưa có TEST locked. {summary['verified_test']}/{summary['test']} TEST verified trong {location}.",
    )


def ollama_check(url: str) -> Check:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=2) as response:
            if 200 <= response.status < 300:
                return Check("PASS", "Ollama local", f"Sẵn sàng tại {url}.")
            return Check("WARN", "Ollama local", f"Phản hồi HTTP {response.status} từ {url}.")
    except (OSError, urllib.error.URLError) as exc:
        return Check(
            "WARN",
            "Ollama local",
            f"Không kết nối được ({exc.reason if isinstance(exc, urllib.error.URLError) else exc}). Agent CLI/RAG retrieval vẫn là phương án dự phòng.",
        )


def build_checks(*, check_ollama: bool, ollama_url: str) -> list[Check]:
    checks = [
        Check(
            "PASS" if sys.version_info >= (3, 11) else "BLOCK",
            "Python runtime",
            f"Python {platform.python_version()}.",
        ),
        path_check("Dependency manifest", PROJECT_ROOT / "requirements.txt"),
        path_check("Canonical Streamlit app", PROJECT_ROOT / "src" / "shopee_chat_web_v19.py"),
        path_check("Hybrid retrieval module", PROJECT_ROOT / "src" / "hybrid_search_shopee_v2.py"),
        path_check("Agent runner", PROJECT_ROOT / "src" / "agent" / "agent_runner.py"),
        path_check("Processed chunks", PROCESSED_DIR / "chunks.jsonl"),
        path_check("Chroma vector index", PROJECT_ROOT / "data" / "vector_db"),
        path_check("Mock shop CSV", PROJECT_ROOT / "data" / "shop_mock"),
        evidence_check(
            "RAG experiment evidence",
            EVALUATION_DIR / "benchmark_candidate_v2.jsonl",
            PROCESSED_DIR / "benchmark_review" / "benchmark_candidate_v2_reviewed.jsonl",
            EVALUATION_DIR / "benchmark_candidate_v2_locked.jsonl",
        ),
        evidence_check(
            "Agent experiment evidence",
            EVALUATION_DIR / "agent_benchmark_candidate_v1.jsonl",
            PROCESSED_DIR / "agent_benchmark_review" / "agent_benchmark_candidate_v1_reviewed.jsonl",
            EVALUATION_DIR / "agent_benchmark_test_locked.jsonl",
        ),
    ]
    if check_ollama:
        checks.append(ollama_check(ollama_url))
    return checks


def render_report(checks: list[Check]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    grouped = {status: [check for check in checks if check.status == status] for status in ("PASS", "WARN", "BLOCK")}
    lines = [
        "# Defense preflight report",
        "",
        f"Generated (UTC): `{now}`",
        "",
        "This report does not create scientific labels or turn a regression run into thesis evidence.",
        "",
    ]
    headings = {
        "PASS": "## Sẵn sàng",
        "WARN": "## Cảnh báo demo (có phương án dự phòng)",
        "BLOCK": "## Blocker cho số liệu luận văn chính thức",
    }
    for status in ("PASS", "WARN", "BLOCK"):
        lines.extend([headings[status], ""])
        if grouped[status]:
            lines.extend(f"- **{check.name}:** {check.detail}" for check in grouped[status])
        else:
            lines.append("- Không có.")
        lines.append("")
    lines.extend(
        [
            "## Lệnh trước khi demo",
            "",
            "```powershell",
            ".\\scripts\\verify_baseline.ps1 -RunAgentEndToEnd",
            ".\\.venv\\Scripts\\streamlit.exe run src\\shopee_chat_web_v19.py",
            "```",
            "",
            "Nếu còn BLOCK, có thể demo hệ thống nhưng không trình bày score regression như kết quả thực nghiệm chính thức.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-ollama", action="store_true", help="Probe the local Ollama endpoint for demo readiness.")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--require-official-evidence",
        action="store_true",
        help="Exit non-zero when retrieval or Agent TEST evidence is still blocked.",
    )
    args = parser.parse_args()

    checks = build_checks(check_ollama=args.check_ollama, ollama_url=args.ollama_url)
    report = render_report(checks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    for check in checks:
        print(f"{check.status}: {check.name} — {check.detail}")
    print(f"Wrote defense preflight report to {args.output}")
    if args.require_official_evidence and any(check.status == "BLOCK" for check in checks):
        raise SystemExit("Official evidence is incomplete; inspect the preflight report.")


if __name__ == "__main__":
    main()
