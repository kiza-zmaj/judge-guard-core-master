"""
Unit tests for Antigravity CLI & Hermes-Notebook RAG Suite.
"""

import pytest
from antigravity_cli.agents.retriever import GroundedRAGRetriever
from antigravity_cli.agents.orchestrator import HermesOrchestrator, Citation, CitedAnswer
from antigravity_cli.self_heal import execute_with_healing


def test_grounded_rag_retriever():
    retriever = GroundedRAGRetriever(db_path="./test_vector_db")
    texts = [
        "Hermes-3 ima napredne mogućnosti za tool-calling i roleplay.",
        "Pydantic parsere osiguravaju 'No Source, No Comment' pravilo.",
    ]
    retriever.ingest_texts(texts, sources=["DOC_1", "DOC_2"])

    results = retriever.retrieve("tool-calling", top_k=2)
    assert len(results) > 0
    assert results[0]["source_id"] == "DOC_1"


def test_hermes_orchestrator():
    orchestrator = HermesOrchestrator()
    chunks = [{"source_id": "SRC_101", "text": "Metapodaci definisani u RAG indeksu."}]

    result = orchestrator.synthesize("Šta su metapodaci?", chunks)
    assert isinstance(result, CitedAnswer)
    assert result.is_grounded is True
    assert len(result.citations) == 1
    assert result.citations[0].source_id == "SRC_101"
    assert len(result.cove_questions) == 3


def test_self_healing_engine():
    attempts_counter = 0

    def FlakyTask(query: str, err_ctx: str):
        nonlocal attempts_counter
        attempts_counter += 1
        if attempts_counter < 2:
            raise ValueError("Privremena greška u parsiranju JSON-a")
        return CitedAnswer(
            query=query,
            answer="Uspešno opravljen odgovor.",
            citations=[Citation(source_id="S1", claim="Fakat")],
            is_grounded=True,
        )

    res = execute_with_healing(FlakyTask, "Test upit")
    assert res["status"] == "SUCCESS"
    assert res["attempts"] == 2
    assert res["output"].is_grounded is True
