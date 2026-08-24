#!/usr/bin/env python3
"""
Pyodide Small Model Optimization (3-6-2 Protocol) Demonstration.
Demonstrates low-latency TF-IDF + Fuzzy Retrieval combined with Rule-Based Synthesis.
"""

import json
from src.pyodide_optimizer.pipeline import PyodideSmallModelPipeline


DOCUMENT_INDEX = [
    {
        "id": "pyodide_ram_limits",
        "text": "Pyodide ima ograničenu RAM memoriju u browser okruženju, što čini manje modele (poput 3-6-2 checkpoint-a) jedinom održivom opcijom za lokalno izvršavanje bez eksternih zavisnosti.",
    },
    {
        "id": "lightweight_retrieval",
        "text": "Optimizacija za Pyodide zahteva lagane tehnike pretrage kao što su TF-IDF i fuzzy matching (Levenshtein/fuzzywuzzy) kako bi se postigao odziv u realnom vremenu.",
    },
    {
        "id": "rule_based_generation",
        "text": "Kombinovanje pretraženih segmenata sa pravilima vođenom generacijom (Rule-Based Generation) sprečava halucinacije i osigurava tačnost odgovora kod manjih modela.",
    },
    {
        "id": "cloud_hybrid_fallback",
        "text": "Kada su potrebni složeni više-koracni zaključci ili generisanje sa velikim kontekstom, sistem može automatski preusmeriti upit na eksterni Cloud LLM API.",
    },
]


def main():
    print("=" * 70)
    print("🚀 PYODIDE SMALL MODEL OPTIMIZER (3-6-2 PROTOCOL DEMO)")
    print("=" * 70)

    pipeline = PyodideSmallModelPipeline(DOCUMENT_INDEX)

    queries = [
        "Kako optimizovati Pyodide pretragu sa manjim modelom?",
        "Šta uraditi zbog ograničene RAM memorije u Pyodide-u?",
        "Zašto koristiti rule based generation?",
    ]

    for q in queries:
        print(f"\n❓ UPIT: {q}")
        res = pipeline.run(q, top_k=2)
        print(f"⏱️ Latencija: {res['latency_ms']} ms")
        print(f"📊 Mod: {res['pipeline_mode']} [{res['protocol']}]")
        print(f"📝 Odgovor:\n{res['answer']}")
        print("-" * 50)

    print("\n✅ Demo uspešno završen!")


if __name__ == "__main__":
    main()
