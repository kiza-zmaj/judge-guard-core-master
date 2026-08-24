"""
Unit tests for Pyodide Small Model Optimizer (3-6-2 Protocol).
"""

import pytest
from src.pyodide_optimizer.retriever import TFIDFRetriever, FuzzyRetriever, LightweightRetriever
from src.pyodide_optimizer.synthesizer import RuleBasedSynthesizer
from src.pyodide_optimizer.pipeline import PyodideSmallModelPipeline


SAMPLE_DOCS = [
    {
        "id": "doc1",
        "text": "Pyodide ima ograničenu RAM memoriju u pregledaču. Manji modeli poput 3-6-2 checkpointa su idealni.",
    },
    {
        "id": "doc2",
        "text": "TF-IDF i fuzzy matching omogućavaju brzu pretragu bez eksternih C-ekstenzija u WASM okruženju.",
    },
    {
        "id": "doc3",
        "text": "Veći modeli u cloudu se koriste za složeno zaključivanje i multi-modalne upite preko API-ja.",
    },
]


def test_tfidf_retriever():
    retriever = TFIDFRetriever()
    retriever.fit_documents(SAMPLE_DOCS)
    results = retriever.search("Pyodide RAM registar", top_k=2)
    assert len(results) > 0
    assert results[0][0]["id"] == "doc1"


def test_fuzzy_retriever():
    retriever = FuzzyRetriever(SAMPLE_DOCS)
    # Typo: "Pyodida" instead of "Pyodide"
    results = retriever.search("Pyodida", top_k=1)
    assert len(results) > 0
    assert "Pyodide" in results[0][0]["text"]


def test_hybrid_retriever():
    retriever = LightweightRetriever(SAMPLE_DOCS)
    res = retriever.retrieve("brzu pretragu fuzzy matching", top_k=1)
    assert len(res) == 1
    assert res[0]["id"] == "doc2"


def test_rule_based_synthesizer():
    synthesizer = RuleBasedSynthesizer()
    res = synthesizer.synthesize_response("Šta je Pyodide?", [SAMPLE_DOCS[0]])
    assert res["status"] == "SUCCESS"
    assert "Pyodide" in res["answer"]
    assert res["chunks_used"] == 1


def test_pyodide_pipeline():
    pipeline = PyodideSmallModelPipeline(SAMPLE_DOCS)
    output = pipeline.run("Kako optimizovati Pyodide pretragu?", top_k=2)
    
    assert output["pipeline_mode"] == "PYODIDE_LOCAL_SMALL_MODEL"
    assert output["protocol"] == "3-6-2 Loptica"
    assert output["retrieved_count"] > 0
    assert output["verification"]["low_latency_passed"] is True
    assert "small_model_prompt" in output
