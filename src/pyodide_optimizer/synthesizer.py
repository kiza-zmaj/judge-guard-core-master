"""
Rule-Based Synthesizer for Pyodide Small Models.
Combines retrieved context chunks with deterministic rules and templates
to maximize output quality and prevent model hallucinations.
"""

from typing import List, Dict, Any, Optional


class RuleBasedSynthesizer:
    """
    Synthesizes coherent responses from retrieved chunks when using smaller
    checkpoints (3-6-2 protocol) in resource-constrained browser contexts.
    """

    def __init__(self, max_output_tokens: int = 512):
        self.max_output_tokens = max_output_tokens

    def synthesize_response(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        fallback_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Combines retrieved context chunks into a structured, deterministic response.
        """
        if not retrieved_chunks:
            return {
                "status": "NO_CONTEXT",
                "answer": (
                    "Nedovoljno podataka u lokalnom indeksu. "
                    "Preporučuje se pozivanje Cloud/API većeg modela za ovaj upit."
                ),
                "chunks_used": 0,
                "confidence": 0.0,
            }

        # Filter and summarize chunks
        combined_facts = []
        sources = []

        for idx, chunk in enumerate(retrieved_chunks, 1):
            text = chunk.get("text", "").strip()
            source_id = chunk.get("id", f"Chunk_{idx}")
            if text:
                combined_facts.append(f"[{idx}] {text}")
                sources.append(source_id)

        context_summary = "\n".join(combined_facts)

        # Build rule-based formatted response
        answer_body = (
            f"Na osnova lokalno pronađenih informacija ({len(retrieved_chunks)} dekodirana segmenta):\n\n"
            f"{context_summary}\n\n"
            "--- \n"
            "⚡ Izvršeno lokalno unutar Pyodide WASM okruženja uz 3-6-2 optimizaciju odziva."
        )

        return {
            "status": "SUCCESS",
            "query": query,
            "answer": answer_body,
            "context_summary": context_summary,
            "chunks_used": len(retrieved_chunks),
            "sources": sources,
            "confidence": min(1.0, 0.5 + 0.15 * len(retrieved_chunks)),
        }

    def format_prompt_for_small_model(
        self, query: str, retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Formats a compact, high-precision prompt optimized for small context windows.
        """
        context_str = "\n".join(
            [f"- {c.get('text', '')}" for c in retrieved_chunks]
        )
        return (
            f"System: Odgovori kratko i tačno na upit isključivo koristeći priloženi kontekst.\n"
            f"Kontekst:\n{context_str}\n\n"
            f"Pitanje: {query}\n"
            f"Odgovor:"
        )
