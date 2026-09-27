[CmdletBinding()]
param(
    [switch]$RunRetrieval,
    [switch]$RunAgentEndToEnd
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Không tìm thấy virtual environment: $Python"
}

$CheckDirectory = Join-Path $env:TEMP ("shopee-rag-baseline-" + [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $CheckDirectory -Force | Out-Null

function Invoke-PythonChecked {
    param([string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

Push-Location $ProjectRoot
try {
    Invoke-PythonChecked -Arguments @(
        "-m", "py_compile",
        "src\extract_documents.py", "src\chunk_documents_pageaware.py",
        "src\build_vector_db.py", "src\hybrid_search_shopee_v2.py",
        "src\shopee_rag_complete_v4_0_1.py", "src\shopee_chat_web_v19.py",
        "src\evaluation\artifact_provenance.py", "src\evaluation\generate_benchmark_candidate_v2.py", "src\evaluation\retrieval_eval.py", "src\evaluation\scope_eval.py",
        "src\evaluation\audit_gold_benchmark.py", "src\evaluation\lock_gold_benchmark.py",
        "src\evaluation\agent_eval.py", "src\evaluation\agent_end_to_end_eval.py", "src\evaluation\error_analysis.py", "src\evaluation\annotation_store.py",
        "src\evaluation\agent_annotation_store.py", "src\evaluation\generate_agent_benchmark_candidate_v1.py", "src\evaluation\lock_agent_benchmark.py",
        "src\agent\agent_runner.py", "src\agent\streamlit_view.py", "src\agent_demo.py", "src\annotation_workbench.py", "src\agent_annotation_workbench.py"
    )
    Invoke-PythonChecked -Arguments @("-m", "unittest", "discover", "-s", "tests")
    Invoke-PythonChecked -Arguments @("src\evaluation\scope_eval.py", "--output", (Join-Path $CheckDirectory "scope_results.csv"), "--summary", (Join-Path $CheckDirectory "scope_summary.csv"), "--manifest", (Join-Path $CheckDirectory "scope_manifest.json"))
    Invoke-PythonChecked -Arguments @("src\evaluation\audit_gold_benchmark.py", "--report", (Join-Path $CheckDirectory "gold_audit.json"), "--review-queue", (Join-Path $CheckDirectory "gold_review_queue.jsonl"))
    Invoke-PythonChecked -Arguments @("src\evaluation\lock_gold_benchmark.py", "--dataset", "src\evaluation\gold_pilot_verified.jsonl", "--output", (Join-Path $CheckDirectory "gold_pilot_locked.jsonl"), "--manifest", (Join-Path $CheckDirectory "gold_pilot_locked_manifest.json"))
    Invoke-PythonChecked -Arguments @("src\evaluation\agent_eval.py", "--output", (Join-Path $CheckDirectory "agent_results.csv"), "--summary", (Join-Path $CheckDirectory "agent_summary.csv"), "--manifest", (Join-Path $CheckDirectory "agent_manifest.json"))
    if ($RunAgentEndToEnd) {
        Invoke-PythonChecked -Arguments @("src\evaluation\agent_end_to_end_eval.py", "--split", "dev", "--output", (Join-Path $CheckDirectory "agent_e2e_results.csv"), "--summary", (Join-Path $CheckDirectory "agent_e2e_summary.csv"), "--manifest", (Join-Path $CheckDirectory "agent_e2e_manifest.json"))
    }
    if ($RunRetrieval) {
        Invoke-PythonChecked -Arguments @("src\evaluation\retrieval_eval.py", "--output", (Join-Path $CheckDirectory "retrieval_results.csv"), "--summary", (Join-Path $CheckDirectory "retrieval_summary.csv"), "--manifest", (Join-Path $CheckDirectory "retrieval_manifest.json"), "--repetitions", "1")
    }
    Invoke-PythonChecked -Arguments @("-m", "pip", "check")
    Write-Output "PASS: baseline checks completed. Artefacts: $CheckDirectory"
}
finally {
    Pop-Location
}
