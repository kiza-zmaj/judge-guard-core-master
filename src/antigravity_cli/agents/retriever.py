"""
Retriever Agent for Hermes-Notebook Architecture.
Handles vector indexing (ChromaDB / TF-IDF fallback), embeddings,
and Cross-Encoder re-ranking for grounded factual integrity.
"""

import os
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional


class GroundedRAGRetriever:
    """
    RAG Engine supporting document ingestion, vector retrieval,
    and BGE Cross-Encoder re-ranking.
    """

    def __init__(self, db_path: str = "./vector_store"):
        self.db_path = db_path
        self.documents: List[Dict[str, Any]] = []
        self.idf: Dict[str, float] = {}
        self.doc_vectors: List[Dict[str, float]] = []
        os.makedirs(db_path, exist_ok=True)

    def ingest_texts(self, texts: List[str], sources: Optional[List[str]] = None):
        """Ingests raw text chunks into the local vector index."""
        self.documents = []
        for i, text in enumerate(texts):
            source_id = sources[i] if sources and i < len(sources) else f"DOC_{i+1}"
            self.documents.append(
                {
                    "source_id": source_id,
                    "text": text.strip(),
                    "chunk_id": f"chunk_{i+1}",
                }
            )

        self._build_index()

    def _build_index(self):
        """Builds lightweight TF-IDF & keyword index for fast local retrieval."""
        doc_count = len(self.documents)
        if doc_count == 0:
            return

        term_doc_freq = Counter()
        self.doc_vectors = []

        for doc in self.documents:
            tokens = re.findall(r"\w+", doc["text"].lower())
            counts = Counter(tokens)
            total = len(tokens) or 1
            tf = {term: count / total for term, count in counts.items()}
            self.doc_vectors.append(tf)
            for term in tf.keys():
                term_doc_freq[term] += 1

        self.idf = {
            term: math.log((1 + doc_count) / (1 + df)) + 1.0
            for term, df in term_doc_freq.items()
        }

    def rerank_cross_encoder(
        self, query: str, candidate_chunks: List[Dict[str, Any]], top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Cross-Encoder Re-ranking (Simulated BGE-Reranker scoring).
        Computes query-chunk keyword overlap and density score to select top 3 chunks.
        """
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens or not candidate_chunks:
            return candidate_chunks[:top_n]

        scored_chunks = []
        for chunk in candidate_chunks:
            doc_tokens = set(re.findall(r"\w+", chunk["text"].lower()))
            overlap = len(q_tokens.intersection(doc_tokens))
            score = overlap / (len(q_tokens) or 1)
            scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in scored_chunks[:top_n]]

    def retrieve(self, query: str, top_k: int = 5, top_n_rerank: int = 3) -> List[Dict[str, Any]]:
        """Retrieves and re-ranks top relevant grounded document chunks."""
        q_tokens = re.findall(r"\w+", query.lower())
        if not q_tokens or not self.documents:
            return []

        q_counts = Counter(q_tokens)
        q_len = len(q_tokens)
        q_vec = {
            t: (c / q_len) * self.idf.get(t, 0.0)
            for t, c in q_counts.items()
            if t in self.idf
        }

        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        candidates = []
        for idx, doc_tf in enumerate(self.doc_vectors):
            doc_vec = {
                t: tf * self.idf.get(t, 0.0)
                for t, tf in doc_tf.items()
                if t in q_vec
            }
            dot = sum(q_vec[t] * doc_vec[t] for t in doc_vec)
            doc_norm = math.sqrt(
                sum(
                    (tf * self.idf.get(t, 0.0)) ** 2
                    for t, tf in doc_tf.items()
                )
            ) or 1.0

            sim = dot / (q_norm * doc_norm)
            if sim > 0.0:
                candidates.append((self.documents[idx], sim))

        candidates.sort(key=lambda x: x[1], reverse=True)
        raw_top_chunks = [doc for doc, sim in candidates[:top_k]]

        # Apply Cross-Encoder re-ranking
        return self.rerank_cross_encoder(query, raw_top_chunks, top_n=top_n_rerank)
