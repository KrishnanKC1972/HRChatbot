from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os

from src.agent import HRAgent
from api import eval_store, unanswered_store

app = FastAPI(title="HR Agentic RAG Chatbot API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if exist
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

agent = HRAgent(evaluate=True)

DEFAULT_BATCH_QUESTIONS = [
    "How many paid leave days do employees get per year?",
    "What is the company's expense reimbursement policy?",
    "Is working from home allowed?",
    "How should I report a security incident?",
    "What is the code of conduct regarding harassment?",
    "What are the office working hours?",
    "Can I encash my unused leave?",
    "Hello, how are you today?",
    "What is the capital of France?",
    "How do I apply for casual leave?",
]


class QueryRequest(BaseModel):
    query: str
    evaluate: Optional[bool] = True


class QueryResponse(BaseModel):
    answer: str
    routing: Dict[str, Any]
    used_rag: bool
    context: str
    sources: List[Dict[str, Any]] = []
    evaluation: Optional[Dict[str, Any]] = None
    unanswered: bool = False
    unanswered_reason: str = ""


class BatchEvalRequest(BaseModel):
    questions: Optional[List[str]] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/chat", response_model=QueryResponse)
async def chat(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = await run_in_threadpool(agent.answer, req.query, True)
    evaluation = result.get("evaluation")
    eval_store.record_interaction(
        query=req.query,
        answer=result.get("answer", ""),
        routing=result.get("routing", {}),
        used_rag=result.get("used_rag", False),
        evaluation=evaluation if isinstance(evaluation, dict) else None,
        source="chat",
    )
    if result.get("unanswered"):
        unanswered_store.record_unanswered(
            query=req.query,
            answer=result.get("answer", ""),
            route="rag" if result.get("used_rag") else "direct",
            used_rag=result.get("used_rag", False),
            reason=result.get("unanswered_reason", ""),
            source="chat",
        )
    return QueryResponse(
        answer=result.get("answer", ""),
        routing=result.get("routing", {}),
        used_rag=result.get("used_rag", False),
        context=result.get("context", ""),
        sources=result.get("sources", []),
        evaluation=evaluation,
        unanswered=result.get("unanswered", False),
        unanswered_reason=result.get("unanswered_reason", ""),
    )


@app.get("/metrics")
async def metrics():
    data = eval_store.compute_metrics()
    data["unanswered"] = unanswered_store.summary()
    return data


@app.get("/history")
async def history(limit: Optional[int] = None):
    return {"records": eval_store.get_history(limit=limit)}


@app.delete("/history")
async def clear_history():
    eval_store.clear_history()
    return {"status": "cleared"}


@app.get("/unanswered")
async def unanswered(limit: Optional[int] = None, status: Optional[str] = None):
    return {
        "summary": unanswered_store.summary(),
        "records": unanswered_store.list_unanswered(limit=limit, status=status),
    }


@app.patch("/unanswered/{query_id}")
async def update_unanswered(query_id: int, body: Dict[str, Any]):
    status = body.get("status")
    if status not in ("open", "reviewing", "resolved"):
        raise HTTPException(status_code=400, detail="status must be one of: open, reviewing, resolved")
    if not unanswered_store.update_status(query_id, status):
        raise HTTPException(status_code=404, detail="Unanswered query not found")
    return {"status": status, "id": query_id}


@app.delete("/unanswered/{query_id}")
async def delete_unanswered(query_id: int):
    if not unanswered_store.delete_unanswered(query_id):
        raise HTTPException(status_code=404, detail="Unanswered query not found")
    return {"status": "deleted", "id": query_id}


@app.delete("/unanswered")
async def clear_unanswered():
    count = unanswered_store.clear_unanswered()
    return {"status": "cleared", "deleted": count}


@app.post("/evaluate/batch")
async def evaluate_batch(req: BatchEvalRequest):
    questions = [q for q in (req.questions or DEFAULT_BATCH_QUESTIONS) if q and q.strip()]
    if not questions:
        raise HTTPException(status_code=400, detail="No questions provided")

    def run_all():
        results = []
        for q in questions:
            result = agent.answer(q)
            evaluation = result.get("evaluation")
            record = eval_store.record_interaction(
                query=q,
                answer=result.get("answer", ""),
                routing=result.get("routing", {}),
                used_rag=result.get("used_rag", False),
                evaluation=evaluation if isinstance(evaluation, dict) else None,
                source="batch",
            )
            if result.get("unanswered"):
                unanswered_store.record_unanswered(
                    query=q,
                    answer=result.get("answer", ""),
                    route="rag" if result.get("used_rag") else "direct",
                    used_rag=result.get("used_rag", False),
                    reason=result.get("unanswered_reason", ""),
                    source="batch",
                )
            results.append(record)
        return results

    records = await run_in_threadpool(run_all)
    data = eval_store.compute_metrics()
    data["unanswered"] = unanswered_store.summary()
    return {"count": len(records), "records": records, "metrics": data}


@app.get("/health")
async def health():
    info: Dict[str, Any] = {"status": "ok", "api": True}
    try:
        from src.rag import load_vector_store
        vs = load_vector_store()
        info["knowledge_base"] = {"ok": True, "chunks": vs._collection.count()}
    except Exception as e:
        info["status"] = "degraded"
        info["knowledge_base"] = {"ok": False, "error": str(e)}
    return info


@app.post("/admin/reload")
async def reload_agent():
    """Rebuild the agent's RAG chain (use after re-running ingest.py while the server is up)."""
    agent._rebuild_rag_chain()
    return {"status": "reloaded", "rag_chain": agent.rag_chain is not None}


# Serve the built React frontend (frontend/dist) last so API routes take precedence
FRONTEND_DIST = os.path.join("frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
