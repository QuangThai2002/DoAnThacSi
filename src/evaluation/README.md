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
