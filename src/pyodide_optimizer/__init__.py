"""
Pyodide Small Model Optimizer Package (3-6-2 Protocol)
Lightweight retrieval, TF-IDF/Fuzzy indexing, rule-based generation, and hybrid RAG.
"""

from .retriever import LightweightRetriever, TFIDFRetriever, FuzzyRetriever
from .synthesizer import RuleBasedSynthesizer
from .pipeline import PyodideSmallModelPipeline

__all__ = [
    "LightweightRetriever",
    "TFIDFRetriever",
    "FuzzyRetriever",
    "RuleBasedSynthesizer",
    "PyodideSmallModelPipeline",
]
