"""Tests for AIL008 — RAGAntiPattern."""

from __future__ import annotations

from ailint.rules.ail008_rag_antipatterns import RAGAntiPatternRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_similarity_search_missing_k():
    """similarity_search on vectorstore without k= should trigger (missing k)."""
    source = """
        docs = vectorstore.similarity_search(query)
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    rule_ids = [f.rule_id for f in findings]
    assert "AIL008" in rule_ids
    messages = [f.message for f in findings]
    assert any("k/top_k" in m for m in messages)


def test_db_query_missing_k():
    """db.query() without k= should trigger missing k finding."""
    source = """
        results = db.query(query_text)
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert any("k/top_k" in f.message for f in findings)


def test_similarity_search_missing_score_filter():
    """similarity_search without score filtering should trigger."""
    source = """
        docs = vectorstore.similarity_search(query, k=5)
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert any("score" in f.message.lower() or "threshold" in f.message.lower() for f in findings)


def test_retrieval_missing_chunking():
    """Retrieval call with no chunking config in module should trigger."""
    source = """
        docs = vectorstore.similarity_search(query, k=5)
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert any("chunk" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_similarity_search_with_k_and_score_and_chunking():
    """similarity_search with k, score threshold, and chunking should not trigger."""
    source = """
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=500)
        docs = vectorstore.similarity_search(query, k=5)
        filtered = [d for d, score in docs if score > 0.7]
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert len(findings) == 0


def test_retrieval_with_score_threshold_kwarg():
    """Retrieval call with score_threshold kwarg should suppress score finding."""
    source = """
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=500)
        docs = vectorstore.similarity_search(query, k=5, score_threshold=0.7)
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert len(findings) == 0


def test_non_vectorstore_query_not_flagged():
    """Query call on non-vector-store object should not trigger."""
    source = """
        results = database.execute("SELECT * FROM users")
    """
    findings = parse_and_check(source, RAGAntiPatternRule)
    assert len(findings) == 0
