"""
Unit tests for BrainCore Tier 1 SQLite FTS5 Memory Engine (antigravity_rag.db).
"""

import os
import pytest
from src.antigravity_cli.braincore_fts5 import BrainCoreTier1Memory


def test_braincore_fts5_memory_speed_and_bm25():
    test_db = "test_antigravity_rag.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    memory = BrainCoreTier1Memory(db_path=test_db)

    # Ingest facts
    memory.add_memory("F_01", "Pyodide WASM", "Pyodide ima ograničeni RAM u pregledaču uz 3-6-2 protocol.", "architecture")
    memory.add_memory("F_02", "BrainCore Tier 1", "SQLite FTS5 RAG baza antigravity_rag.db sa pod-5ms latencijom.", "memory")
    memory.add_memory("F_03", "NotebookLM Tier 2", "NotebookLM ID 56ec350e-8900-4a95-a1ff-10eb518045f0 je autoritativni izvor.", "memory")

    # Perform search
    res = memory.search_memory("antigravity_rag.db", limit=2)

    assert res["count"] > 0
    assert res["latency_under_5ms"] is True
    assert res["results"][0]["source_id"] == "F_02"

    if os.path.exists(test_db):
        os.remove(test_db)
