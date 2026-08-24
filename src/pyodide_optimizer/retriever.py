"""
Lightweight Retriever for Pyodide Environments.
Supports TF-IDF and Fuzzy Matching without heavy C-extensions.
Optimized for low-latency, memory-constrained browser execution.
"""

import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple


def tokenize(text: str) -> List[str]:
    """Simple lowercasing and alphanumeric tokenization."""
    return re.findall(r"\w+", text.lower())


def levenshtein_ratio(s1: str, s2: str) -> float:
    """
    Pure Python Levenshtein distance similarity ratio (0.0 to 1.0).
    Zero dependencies, compatible with Pyodide WASM runtime.
    """
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    dp = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, len2 + 1):
            temp = dp[j]
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = temp

    distance = dp[len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


class TFIDFRetriever:
    """Pure-Python TF-IDF indexer and retriever."""

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_vectors: List[Dict[str, float]] = []

    def fit_documents(self, docs: List[Dict[str, Any]]) -> "TFIDFRetriever":
        """Pre-indexes and vectorizes documents in advance to minimize query latency."""
        self.documents = docs
        doc_count = len(docs)
        if doc_count == 0:
            return self

        term_doc_freq: Counter = Counter()
        self.doc_vectors = []

        for doc in docs:
            tokens = tokenize(doc.get("text", ""))
            counts = Counter(tokens)
            total_tokens = len(tokens) or 1
            tf = {term: count / total_tokens for term, count in counts.items()}
            self.doc_vectors.append(tf)
            for term in tf.keys():
                term_doc_freq[term] += 1

        # Compute IDF with smoothing
        self.idf = {
            term: math.log((1 + doc_count) / (1 + df)) + 1.0
            for term, df in term_doc_freq.items()
        }

        return self

    def search(self, query: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """Search documents using TF-IDF cosine similarity."""
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents:
            return []

        q_counts = Counter(query_tokens)
        q_len = len(query_tokens)
        q_vec = {
            term: (count / q_len) * self.idf.get(term, 0.0)
            for term, count in q_counts.items()
            if term in self.idf
        }

        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        scores = []
        for idx, doc_tf in enumerate(self.doc_vectors):
            doc_vec = {
                term: tf * self.idf.get(term, 0.0)
                for term, tf in doc_tf.items()
                if term in q_vec
            }
            dot_product = sum(q_vec[term] * doc_vec[term] for term in doc_vec)
            doc_norm = math.sqrt(
                sum(
                    (tf * self.idf.get(term, 0.0)) ** 2
                    for term, tf in doc_tf.items()
                )
            ) or 1.0

            similarity = dot_product / (q_norm * doc_norm)
            if similarity > 0.0:
                scores.append((self.documents[idx], similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class FuzzyRetriever:
    """Lightweight Fuzzy matching retriever for typo-tolerant queries."""

    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents

    def search(self, query: str, top_k: int = 3, min_ratio: float = 0.4) -> List[Tuple[Dict[str, Any], float]]:
        """Search documents using sliding fuzzy match over tokens/phrases."""
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents:
            return []

        query_phrase = " ".join(query_tokens)
        results = []

        for doc in self.documents:
            text = doc.get("text", "")
            doc_tokens = tokenize(text)
            if not doc_tokens:
                continue

            max_score = 0.0
            # Sliding window fuzzy comparison
            window_size = len(query_tokens)
            for i in range(max(1, len(doc_tokens) - window_size + 1)):
                window_phrase = " ".join(doc_tokens[i : i + window_size])
                ratio = levenshtein_ratio(query_phrase, window_phrase)
                if ratio > max_score:
                    max_score = ratio

            if max_score >= min_ratio:
                results.append((doc, max_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class LightweightRetriever:
    """
    Hybrid retriever combining TF-IDF and Fuzzy matching.
    Designed specifically for memory-constrained browser WASM environments.
    """

    def __init__(self, documents: List[Dict[str, Any]] = None):
        self.documents = documents or []
        self.tfidf = TFIDFRetriever()
        self.fuzzy = FuzzyRetriever(self.documents)
        if self.documents:
            self.tfidf.fit_documents(self.documents)

    def set_documents(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.tfidf.fit_documents(documents)
        self.fuzzy = FuzzyRetriever(documents)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Perform hybrid search (TF-IDF primary + Fuzzy fallback)."""
        tfidf_results = self.tfidf.search(query, top_k=top_k)

        # If TF-IDF yields high confidence results, return them
        if tfidf_results and tfidf_results[0][1] >= 0.2:
            return [doc for doc, _ in tfidf_results]

        # Hybrid merge with fuzzy search for typos / partial matches
        fuzzy_results = self.fuzzy.search(query, top_k=top_k)
        combined: Dict[str, Dict[str, Any]] = {}

        for doc, score in tfidf_results:
            doc_id = str(doc.get("id", doc.get("text", "")))
            combined[doc_id] = doc

        for doc, score in fuzzy_results:
            doc_id = str(doc.get("id", doc.get("text", "")))
            if doc_id not in combined:
                combined[doc_id] = doc

        return list(combined.values())[:top_k]
