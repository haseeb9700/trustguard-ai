# TrustGuard AI

**Enterprise AI Governance & Hallucination Detection Platform**

TrustGuard AI is a full-stack AI governance platform that makes LLM responses trustworthy and explainable. It grounds answers in trusted documents using Retrieval-Augmented Generation (RAG), evaluates each response for hallucination risk, assigns a governance risk rating, and records every interaction in an audit log.

---

## Why It Exists

Large Language Models can generate confident but unsupported answers. In compliance-heavy domains — immigration, AI governance, finance, healthcare — hallucinated information creates real risk. TrustGuard AI addresses this by allowing answers only from ingested, trusted sources and by scoring, explaining, and logging every response.

## Key Features

- **Dynamic knowledge ingestion** — scrape, chunk, and embed any trusted URL on demand
- **Multi-agent RAG workflow** — query rewriting, retrieval, answering, evaluation, risk scoring, and audit logging as dedicated agents
- **Semantic search** — BGE embeddings with cosine similarity over a PostgreSQL (Supabase) vector store
- **Cross-encoder reranking** — improves retrieval precision before answer generation
- **Hallucination detection** — every answer is scored 0–2 for grounding against retrieved context
- **Risk scoring** — Low / Medium / High governance ratings with human-readable reasons
- **Audit logging** — full traceability of every query, answer, and risk decision
- **Human feedback loop** — correct / partially correct / incorrect ratings captured for future improvement
- **Full-stack dashboard** — Next.js frontend with a FastAPI backend

## Architecture

```text
User
 └── Next.js Frontend
      └── FastAPI Backend
           ├── Query Rewrite Agent   (retrieval-friendly reformulation)
           ├── Retrieval Agent       (BGE embeddings → cosine similarity)
           ├── Reranker              (cross-encoder, ms-marco-MiniLM)
           ├── Answer Agent          (GPT-4o-mini, context-grounded only)
           ├── Evaluation Agent      (hallucination score 0–2)
           ├── Risk Agent            (Low / Medium / High rating)
           └── Audit Agent           (Supabase audit_logs table)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (React, TypeScript) |
| Backend | FastAPI (Python) |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | BAAI/bge-small-en-v1.5 (Sentence Transformers) |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Vector store | Supabase (PostgreSQL) |
| Scraping | Requests + BeautifulSoup |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/analyze` | Run the full governance workflow for a question |
| `POST` | `/ingest-url` | Scrape, chunk, embed, and store a trusted URL |
| `POST` | `/feedback` | Record human feedback on an answer |
| `GET` | `/audit-logs` | Retrieve recent audit entries and top questions |
| `GET` | `/cache-stats` | Answer/embedding cache hit-rate statistics |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key and a Supabase (PostgreSQL) database

### Backend

```bash
cd trustguard-ai
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Run the API:

```bash
uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:3000`.

## Performance & Caching

Repeated questions skip the entire rewrite → retrieve → answer → verify → score
pipeline via a process-local LRU cache (`modules/cache.py`):

- **Answer cache** — full workflow results keyed by the normalized question
  (TTL-bounded). Cleared automatically whenever a source is ingested or
  deleted, so cached answers never go stale against the knowledge base.
- **Embedding cache** — query embeddings keyed by text. Knowledge-base
  independent, so it persists across ingestions.

The audit log is still written on every request, including cache hits, so the
governance trail stays complete. `GET /cache-stats` exposes live hit rates.
Tunable via env: `CACHE_ENABLED`, `ANSWER_CACHE_TTL`, `EMBED_CACHE_SIZE`,
`ANSWER_CACHE_SIZE`.

## Evaluation

The claim-level hallucination detector is benchmarked against a labeled
dataset so its accuracy is a measured number, not an assertion. The harness
decomposes each answer, verifies it against its sources, and reports
precision / recall / F1 per verdict class plus a confusion matrix.

```bash
python -m eval.run_eval                    # production verifier (needs OPENAI_API_KEY)
python -m eval.run_eval --verifier lexical # offline word-overlap baseline (no key/cost)
python -m eval.run_eval --verifier oracle  # sanity-check the scoring math
```

On the 30-case benchmark, the naive lexical baseline scores 0.55 macro-F1 and
**0.00 F1 on contradictions** — the failure mode the hierarchical claim
verifier is designed to fix.

Retrieval quality is measured separately against a labeled corpus + query
relevance set, reporting hit-rate@k, recall@k, precision@k, MRR, and nDCG@k —
because a RAG system's answers are only as good as what it retrieves.

```bash
python -m eval.run_retrieval_eval                     # bge-small + cosine (real path)
python -m eval.run_retrieval_eval --ranker lexical    # offline word-overlap baseline
python -m eval.run_retrieval_eval --ranker oracle     # sanity-check the metric math
```

The lexical baseline scores 0.60 hit-rate@1 / 0.74 MRR on the paraphrased query
set, leaving clear headroom the embedding retriever should recover. See
[`eval/README.md`](eval/README.md) for both harnesses.

## Project Structure

```text
trustguard-ai/
├── app.py                  # FastAPI application and endpoints
├── eval/                   # Hallucination-detection benchmark (dataset + metrics + runner)
├── agents/                 # Multi-agent workflow
│   ├── orchestrator.py     # Pipeline coordinator
│   ├── query_rewrite_agent.py
│   ├── retrieval_agent.py
│   ├── answer_agent.py
│   ├── evaluation_agent.py
│   ├── risk_agent.py
│   └── audit_agent.py
├── modules/                # Core services
│   ├── rag_pipeline.py     # Embedding retrieval
│   ├── reranker.py         # Cross-encoder reranking
│   ├── hallucination_checker.py
│   ├── risk_score.py
│   ├── url_ingestor.py     # Scrape → chunk → embed → store
│   ├── audit_logger.py / supabase_logger.py
│   └── feedback_logger.py
├── frontend/               # Next.js dashboard
├── scripts/                # Data preparation utilities
└── reports/                # Local audit and feedback logs
```

## Author

**Mohammed Abdul Haseeb** — [m.haseeb311@gmail.com](mailto:m.haseeb311@gmail.com)
