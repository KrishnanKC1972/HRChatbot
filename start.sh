#!/bin/sh
set -e

if [ ! -f chroma_db/chroma.sqlite3 ]; then
  echo "ChromaDB not found, running ingestion..."
  python ingest.py
fi

exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
