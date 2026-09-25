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

Smoke-test outputs for this draft are written to:

- `data/processed/gold_v1_retrieval_eval_results.csv`
- `data/processed/gold_v1_retrieval_eval_summary.csv`

Do not treat those smoke-test scores as final experimental results. Because the
draft questions are automatically derived from evidence snippets, lexical
methods such as BM25 may be advantaged.

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
