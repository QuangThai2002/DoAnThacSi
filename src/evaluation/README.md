# Shopee RAG Evaluation

This folder contains the thesis-facing evaluation pipeline. It is intentionally
separate from the Streamlit demo and does not use UI quick paths, hard-coded
answers, static citations, conversation state, or Ollama generation.

The first goal is to measure retrieval quality on a fixed benchmark. Retrieval
evaluation only uses `answerable=true` records:

- BM25
- Dense retrieval
- Hybrid retrieval without query-specific bonus rules
- Hybrid retrieval with heuristic reranking

Primary metrics:

- Hit@1
- Hit@3
- Hit@5
- Recall@1/3/5/10
- unique-document Recall@K
- MRR@10
- nDCG@5
- Page Hit@5, only for records with page labels
- retrieval median and p95 latency after warm-up

When the input includes a `split` field, the output summary also contains
separate DEV / TEST / CHALLENGE rows. `--split` restricts a run to a given
split, and `--require-verified` prevents an official run from accidentally
using any record whose `gold_verified` field is false.

Scope evaluation is separate from retrieval evaluation. It uses all records and
measures whether the system classifies a query as:

- answerable
- private shop data
- out of scope

Run:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py
.\.venv\Scripts\python.exe src\evaluation\scope_eval.py
```

Example for a locked official TEST run:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py `
  --dataset src\evaluation\gold_benchmark_v1_locked.jsonl `
  --split test `
  --require-verified `
  --output data\processed\official_test_results.csv `
  --summary data\processed\official_test_summary.csv `
  --repetitions 3
```

The current dataset is a seed benchmark. Treat it as a reviewable starting
point, not as final scientific ground truth until each item has been checked
against the source document/page.

## Agent benchmark and end-to-end evaluation

`agent_benchmark_candidate_v1.jsonl` contains 32 Agent review candidates with
a deterministic split: DEV 16, TEST 10 and CHALLENGE 6. The candidate is
derived from the legacy routing seed and every row deliberately starts with
`gold_verified=false`; the split is useful for process discipline but is not
itself independent gold evidence.

The Agent has two evaluators:

- `agent_eval.py` checks planner intent and ordered tool route.
- `agent_end_to_end_eval.py` executes the Agent and checks the trace, citation
  contract, mock-data disclaimer, refusal, period, latency and, after review,
  citation document / answer-marker correctness.

Run a development or regression check:

```powershell
.\.venv\Scripts\python.exe src\evaluation\agent_eval.py --split dev
.\.venv\Scripts\python.exe src\evaluation\agent_end_to_end_eval.py --split dev
```

Before an official TEST run, review the candidate in
`src/agent_annotation_workbench.py`. The guarded flag then validates not only
`gold_verified`, but reviewer/note, RAG reference-source confirmation and
document IDs, and deterministic answer markers for mock-shop/calculation
tasks. `lock_agent_benchmark.py` can then write a TEST-only locked copy and
snapshot the corpus plus all mock-shop CSV hashes. See
[agent_annotation_protocol.md](../../docs/agent_annotation_protocol.md).

## Gold Benchmark v1 Draft

`gold_benchmark_v1.jsonl` is a 120-item draft benchmark generated from
`data/processed/chunks.jsonl` using:

```powershell
.\.venv\Scripts\python.exe src\evaluation\generate_gold_benchmark_v1.py
```

Distribution:

- DEV: 72
- TEST: 24
- CHALLENGE: 24

The draft follows the Document -> Page -> Evidence -> Reference answer ->
Question route. However, every item currently has `gold_verified=false`.
Before locking TEST or reporting thesis-grade results, each item must be
manually checked against the source PDF/page and rewritten where the generated
question is too lexical, too generic, or too close to the evidence text.

`benchmark_candidate_v2.jsonl` is a separate 34-item AI-assisted review
candidate. Its source/page/evidence linkage and mechanical audit checks are
tested, but all records intentionally remain `gold_verified=false`. Use it to
start human review faster; do not report its measurements as thesis results
until the reviewed copy has been verified and locked.

Smoke-test outputs for this draft are written to:

- `data/processed/gold_v1_retrieval_eval_results.csv`
- `data/processed/gold_v1_retrieval_eval_summary.csv`

Do not treat those smoke-test scores as final experimental results. Because the
draft questions are automatically derived from evidence snippets, lexical
methods such as BM25 may be advantaged.

## Verified annotation pilot

`gold_pilot_verified.jsonl` contains six records manually checked against
rendered source PDF pages. It demonstrates the intended annotation standard and
the lock workflow, but it is deliberately too small and narrow to report as a
thesis experiment. Use it only for tooling smoke checks and reviewer training.

## Audit before annotation

Run the audit before reviewing or locking a benchmark split:

```powershell
.\.venv\Scripts\python.exe src\evaluation\audit_gold_benchmark.py
```

It writes an audit report and a JSONL review queue under `data/processed/`.
The audit never edits gold labels. It flags items whose question leaks a page
number/title, has high lexical overlap with evidence, includes navigation/OCR
boilerplate, or cannot be linked back to a processed chunk. A record with no
automated flag is still not final until a reviewer checks the original PDF/page
and changes `gold_verified` deliberately.

## Locking a reviewed benchmark

After all review flags have been resolved and every record has been checked
against its original document/page, create the candidate locked benchmark:

```powershell
.\.venv\Scripts\python.exe src\evaluation\lock_gold_benchmark.py `
  --dataset src\evaluation\gold_benchmark_v1_reviewed.jsonl `
  --output src\evaluation\gold_benchmark_v1_locked.jsonl `
  --manifest src\evaluation\gold_benchmark_v1_locked_manifest.json
```

The command refuses to write a locked file if a split is missing, any record is
not `gold_verified`, or the audit still raises a quality flag. The manifest
stores SHA-256 values for both dataset and `chunks.jsonl`; save its Git commit
hash with the final TEST result. Existing locked output is never overwritten
unless `--force` is explicitly supplied.

## Error analysis after an experiment

```powershell
.\.venv\Scripts\python.exe src\evaluation\error_analysis.py `
  --input data\processed\official_dev_results.csv `
  --variant hybrid_without_query_bonus `
  --output data\processed\official_dev_error_analysis.md
```

The report classifies misses as not retrieved in top 10, relevant but below top
5, partial multi-document retrieval, wrong page, or top-1 ranking error. Use
the report to decide a DEV-only intervention, then rerun all variants.
