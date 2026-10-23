"""SQLite persistence for queries the HR assistant could not answer.

A query is considered "unanswered" when:
  - the RAG path returns the configured "not enough information" response, or
  - generation produced an error / empty answer.

These are stored permanently so HR can review and fill policy gaps.
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_DIR = os.environ.get("UNANSWERED_DB_DIR", "./data")
DB_PATH = os.environ.get("UNANSWERED_DB_PATH", os.path.join(DB_DIR, "unanswered_queries.db"))

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unanswered_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT,
                route TEXT,
                used_rag INTEGER DEFAULT 0,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                source TEXT DEFAULT 'chat'
            )
            """
        )
        conn.commit()


def record_unanswered(
    query: str,
    answer: str = "",
    route: str = "",
    used_rag: bool = False,
    reason: str = "",
    source: str = "chat",
) -> Dict[str, Any]:
    """Insert a permanently-stored unanswered query."""
    init_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    with _lock, _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO unanswered_queries
                (timestamp, query, answer, route, used_rag, reason, status, source)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (timestamp, query, answer, route, 1 if used_rag else 0, reason, source),
        )
        conn.commit()
        row_id = cur.lastrowid
    return {
        "id": row_id,
        "timestamp": timestamp,
        "query": query,
        "answer": answer,
        "route": route,
        "used_rag": used_rag,
        "reason": reason,
        "status": "open",
        "source": source,
    }


def list_unanswered(limit: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    query = "SELECT * FROM unanswered_queries"
    params: List[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "query": r["query"],
            "answer": r["answer"],
            "route": r["route"],
            "used_rag": bool(r["used_rag"]),
            "reason": r["reason"],
            "status": r["status"],
            "source": r["source"],
        }
        for r in rows
    ]


def update_status(query_id: int, status: str) -> bool:
    init_db()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "UPDATE unanswered_queries SET status = ? WHERE id = ?",
            (status, query_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_unanswered(query_id: int) -> bool:
    init_db()
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM unanswered_queries WHERE id = ?", (query_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_unanswered() -> int:
    init_db()
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM unanswered_queries")
        conn.commit()
        return cur.rowcount


def count_unanswered(status: Optional[str] = None) -> int:
    init_db()
    with _connect() as conn:
        if status:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM unanswered_queries WHERE status = ?", (status,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS c FROM unanswered_queries").fetchone()
    return int(row["c"]) if row else 0


def summary() -> Dict[str, Any]:
    """Return counts and a small recent sample for dashboards."""
    init_db()
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM unanswered_queries").fetchone()["c"]
        open_count = conn.execute(
            "SELECT COUNT(*) AS c FROM unanswered_queries WHERE status = 'open'"
        ).fetchone()["c"]
        resolved = conn.execute(
            "SELECT COUNT(*) AS c FROM unanswered_queries WHERE status != 'open'"
        ).fetchone()["c"]
        recent = conn.execute(
            "SELECT * FROM unanswered_queries ORDER BY id DESC LIMIT 10"
        ).fetchall()
    return {
        "total": int(total),
        "open": int(open_count),
        "resolved": int(resolved),
        "recent": [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "query": r["query"],
                "route": r["route"],
                "used_rag": bool(r["used_rag"]),
                "reason": r["reason"],
                "status": r["status"],
                "source": r["source"],
            }
            for r in recent
        ],
    }
