# HR RAG Chatbot (FastAPI + React UI)

A second, non-Streamlit UI built with **React (Vite)** on top of the existing FastAPI backend.
The original Streamlit app (`app.py`) is untouched.

## Features
- **Chat page** — calls `POST /chat`, shows the answer, routing decision (RAG vs Direct LLM),
  retrieved context, and the per-response Evaluator scores (relevance / faithfulness / overall + verdict).
- **Evaluation Dashboard** — persists every evaluation and visualizes RAG metrics with Recharts:
  KPIs (pass rate, average scores, RAG/Direct split), score trend over time, routing distribution,
  verdict breakdown, RAG-vs-Direct comparison, and a recent-evaluations table.
- **Batch evaluation** — a button runs 10 standard HR questions through the full agent pipeline
  (route → generate → evaluate) to quickly populate the dashboard.
- **Unanswered queries** — every question the assistant cannot ground in the HR policies is stored
  permanently in a **SQLite** database (`data/unanswered_queries.db`) and surfaced in a dashboard
  section for HR follow-up (review / resolve / delete).

## Project layout
```
api/
  main.py            # FastAPI app + endpoints (/metrics, /history, /unanswered, /evaluate/batch)
  eval_store.py      # JSON persistence + aggregation of evaluation results
  unanswered_store.py # SQLite persistence for unanswered queries
frontend/            # Vite + React app (Chat + Dashboard), built to frontend/dist
eval_results/        # generated: evaluation_history.json
data/unanswered_queries.db  # generated: SQLite store of unanswered queries
```

## Run the API (serves the built React UI at /app)
```powershell
.\venv\Scripts\python.exe run_api.py
# UI:      http://127.0.0.1:8000/app/
# Old UI:  http://127.0.0.1:8000/      (Jinja template)
# API docs: http://127.0.0.1:8000/docs
```

## Develop the React UI (hot reload, proxies API to :8000)
```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # rebuild frontend/dist (re-served by FastAPI)
```

## API endpoints
| Method | Path               | Purpose                                          |
|--------|--------------------|--------------------------------------------------|
| POST   | `/chat`            | Ask a question; also records the evaluation       |
| GET    | `/metrics`         | Aggregated RAG evaluation metrics for the dashboard |
| GET    | `/history`         | Recent evaluation records (`?limit=50`)          |
| DELETE | `/history`         | Clear all evaluation history                     |
| GET    | `/unanswered`      | Unanswered queries from SQLite (`?limit`, `?status`) |
| PATCH  | `/unanswered/{id}` | Update status: `open` / `reviewing` / `resolved`  |
| DELETE | `/unanswered/{id}` | Delete a single unanswered query                  |
| DELETE | `/unanswered`      | Clear all unanswered queries                      |
| POST   | `/evaluate/batch`  | Run a canned/staged set of questions and record  |
| GET    | `/health`          | Health check + knowledge-base status             |
| POST   | `/admin/reload`    | Rebuild the RAG chain after re-running `ingest.py` |

## Troubleshooting
- **"Error generating RAG answer: ... collection ..."** — the server keeps a cached ChromaDB
  handle. Re-running `python ingest.py` deletes/recreates the collection. The agent now
  auto-rebuilds and retries once, but you can also force it with `POST /admin/reload` or by
  restarting `run_api.py`. Check `GET /health` to confirm `knowledge_base.ok` and chunk count.
- If `chunks` is 0 or PDFs are missing, run `python ingest.py` (requires `pypdf`, installed via
  `requirements.txt`).

## Also available
- Streamlit: `streamlit run app.py`
- CLI: `python main.py`
- Ingest: `python ingest.py`
