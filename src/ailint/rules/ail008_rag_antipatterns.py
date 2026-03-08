"""AIL008 — RAG Anti-Patterns: vector store calls missing limits/filtering."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line, has_keyword

# Method names that suggest vector store retrieval.
_RETRIEVAL_METHODS: set[str] = {
    "similarity_search", "query", "search",
    "similarity_search_with_score", "similarity_search_by_vector",
    "as_retriever", "get_relevant_documents", "invoke",
}

# Object names that suggest a vector store.
_STORE_NAMES: set[str] = {
    "vectorstore", "vector_store", "db", "index", "retriever",
    "store", "chroma", "faiss", "pinecone", "weaviate", "qdrant",
    "milvus", "collection",
}

# Names indicating chunking configuration is present.
_CHUNKING_INDICATORS: set[str] = {
    "chunk_size", "RecursiveCharacterTextSplitter",
    "TokenTextSplitter", "CharacterTextSplitter", "TextSplitter",
    "chunk_overlap", "split_documents", "split_text",
}


@registry.register
class RAGAntiPatternRule(BaseRule):
    rule_id = "AIL008"
    name = "RAGAntiPattern"
    description = "Vector store retrieval missing limits, score filtering, or chunking"
    severity = Severity.WARNING

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []
        has_chunking = self._module_has_chunking(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not self._is_retrieval_call(node):
                continue

            # Sub-pattern 1: missing k / top_k limit
            if not (has_keyword(node, "k") or has_keyword(node, "top_k")):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        severity=self.severity,
                        message="Vector store retrieval missing k/top_k limit",
                        location=Location(
                            file=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                        ),
                        fix_suggestion="Add k=5 or top_k=5 to limit the number of retrieved documents",
                        source_line=get_source_line(source_lines, node.lineno),
                    )
                )

            # Sub-pattern 2: no score threshold (check enclosing function/module)
            if not self._has_score_filtering(tree, node):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        severity=self.severity,
                        message="Retrieved documents lack score/relevance threshold filtering",
                        location=Location(
                            file=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                        ),
                        fix_suggestion=(
                            "Filter retrieved documents by relevance score "
                            "before passing to LLM"
                        ),
                        source_line=get_source_line(source_lines, node.lineno),
                    )
                )

            # Sub-pattern 3: no chunking in module
            if not has_chunking:
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        severity=self.severity,
                        message="No document chunking configuration found in module",
                        location=Location(
                            file=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                        ),
                        fix_suggestion=(
                            "Use RecursiveCharacterTextSplitter or similar to "
                            "chunk documents before indexing"
                        ),
                        source_line=get_source_line(source_lines, node.lineno),
                    )
                )

        return findings

    def _is_retrieval_call(self, node: ast.Call) -> bool:
        """Check if the call is on a vector store object with a retrieval method."""
        if not isinstance(node.func, ast.Attribute):
            return False
        if node.func.attr not in _RETRIEVAL_METHODS:
            return False

        # Check if the object name suggests a vector store
        obj_name = self._get_obj_name(node.func.value)
        return obj_name.lower() in _STORE_NAMES

    def _get_obj_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def _has_score_filtering(self, tree: ast.AST, call_node: ast.Call) -> bool:
        """Check if there's score filtering logic in the module."""
        source = ast.dump(tree)
        # Look for score-related comparisons
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                compare_str = ast.dump(node)
                if "score" in compare_str.lower() or "threshold" in compare_str.lower():
                    return True
            # Check for score_threshold keyword in the retrieval call itself
            if node is call_node:
                if has_keyword(node, "score_threshold"):
                    return True
        return False

    def _module_has_chunking(self, tree: ast.AST) -> bool:
        """Check if the module references any chunking utilities."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in _CHUNKING_INDICATORS:
                return True
            if isinstance(node, ast.Attribute) and node.attr in _CHUNKING_INDICATORS:
                return True
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name in _CHUNKING_INDICATORS:
                        return True
            if isinstance(node, ast.keyword) and node.arg in _CHUNKING_INDICATORS:
                return True
        return False
