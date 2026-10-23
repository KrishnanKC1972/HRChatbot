"""Persistent store for chat + RAG evaluation results used by the metrics dashboard."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

EVAL_DIR = os.environ.get("EVAL_RESULTS_DIR", "./eval_results")
EVAL_FILE = os.path.join(EVAL_DIR, "evaluation_history.json")

_lock = threading.Lock()


def _ensure_file() -> None:
    os.makedirs(EVAL_DIR, exist_ok=True)
    if not os.path.exists(EVAL_FILE):
        with open(EVAL_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_history() -> List[Dict[str, Any]]:
    _ensure_file()
    try:
        with open(EVAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(records: List[Dict[str, Any]]) -> None:
    _ensure_file()
    tmp = EVAL_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    os.replace(tmp, EVAL_FILE)


def record_interaction(
    query: str,
    answer: str,
    routing: Optional[Dict[str, Any]],
    used_rag: bool,
    evaluation: Optional[Dict[str, Any]],
    source: str = "chat",
) -> Dict[str, Any]:
    """Append one chat/evaluation record to the history file."""
    record = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "answer": answer,
        "routing": routing or {},
        "used_rag": used_rag,
        "route": "rag" if used_rag else "direct",
        "evaluation": evaluation,
        "source": source,
    }
    with _lock:
        records = load_history()
        records.append(record)
        save_history(records)
    return record


def clear_history() -> None:
    with _lock:
        save_history([])


def _score(record: Dict[str, Any], key: str) -> Optional[float]:
    ev = record.get("evaluation") or {}
    val = ev.get(key)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def compute_metrics() -> Dict[str, Any]:
    """Aggregate evaluation history into dashboard metrics."""
    records = load_history()
    scored = [r for r in records if r.get("evaluation") and "error" not in (r.get("evaluation") or {})]

    def avg(vals):
        return round(sum(vals) / len(vals), 4) if vals else None

    relevance = [v for v in (_score(r, "relevance_score") for r in scored) if v is not None]
    faithfulness = [v for v in (_score(r, "faithfulness_score") for r in scored) if v is not None]
    overall = [v for v in (_score(r, "overall_score") for r in scored) if v is not None]

    verdicts: Dict[str, int] = {}
    for r in scored:
        verdict = (r.get("evaluation") or {}).get("verdict", "UNKNOWN")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    rag_count = sum(1 for r in records if r.get("used_rag"))
    direct_count = len(records) - rag_count

    by_source: Dict[str, int] = {}
    for r in records:
        src = r.get("source", "chat")
        by_source[src] = by_source.get(src, 0) + 1

    # Score trend over time (only scored records, chronological)
    trend = []
    for r in scored:
        ev = r["evaluation"]
        trend.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "relevance": ev.get("relevance_score"),
            "faithfulness": ev.get("faithfulness_score"),
            "overall": ev.get("overall_score"),
            "verdict": ev.get("verdict"),
            "route": r.get("route"),
        })

    # Bucket averages per route
    def route_avg(key):
        rag_vals = [v for v in (_score(r, key) for r in scored if r.get("used_rag")) if v is not None]
        direct_vals = [v for v in (_score(r, key) for r in scored if not r.get("used_rag")) if v is not None]
        return {"rag": avg(rag_vals), "direct": avg(direct_vals)}

    total_verdicts = sum(verdicts.values())
    pass_count = verdicts.get("PASS", 0)

    return {
        "total_queries": len(records),
        "scored_queries": len(scored),
        "failed_evaluations": len(records) - len(scored),
        "rag_queries": rag_count,
        "direct_queries": direct_count,
        "pass_count": pass_count,
        "fail_count": verdicts.get("FAIL", 0),
        "pass_rate": round(pass_count / total_verdicts, 4) if total_verdicts else None,
        "avg_relevance": avg(relevance),
        "avg_faithfulness": avg(faithfulness),
        "avg_overall": avg(overall),
        "verdicts": verdicts,
        "by_source": by_source,
        "score_trend": trend,
        "route_comparison": {
            "relevance": route_avg("relevance_score"),
            "faithfulness": route_avg("faithfulness_score"),
            "overall": route_avg("overall_score"),
        },
    }


def get_history(limit: Optional[int] = None, newest_first: bool = True) -> List[Dict[str, Any]]:
    records = load_history()
    if newest_first:
        records = list(reversed(records))
    if limit is not None:
        records = records[:limit]
    return records
