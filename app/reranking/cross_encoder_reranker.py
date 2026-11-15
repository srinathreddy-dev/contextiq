
import re

from dataclasses import dataclass

from app.retrieval.bm25_retriever import RetrievalResult


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by",
    "for", "from", "how", "in", "is", "it", "of", "on",
    "or", "that", "the", "this", "to", "was", "what",
    "when", "where", "which", "who", "why", "with",
    "company", "companies",
}


# Focused terminology groups.
# These are curated lexical relationships, not learned embeddings.

CONCEPTS = {
    "attendance": {
        "attendance",
        "tardiness",
        "tardy",
        "absence",
        "absences",
        "late",
        "arrive",
        "arrival",
        "punctuality",
        "workday",
    },

    "expectation": {
        "expectation",
        "expectations",
        "expected",
        "expect",
        "required",
        "requirement",
        "requirements",
        "responsibility",
        "responsibilities",
    },

    "vacation": {
        "vacation",
        "pto",
        "holiday",
        "timeoff",
    },

    "insurance": {
        "insurance",
        "coverage",
        "medical",
        "health",
        "benefit",
        "benefits",
    },

    "retirement": {
        "retirement",
        "savings",
        "pension",
        "contribution",
        "contributions",
    },

    # Security concepts are deliberately separated.

    "password_policy": {
        "password",
        "passwords",
        "credential",
        "credentials",
        "passcode",
        "passcodes",
    },

    "mfa_authentication": {
        "mfa",
        "authentication",
        "authenticator",
        "authenticators",
        "multifactor",
        "factor",
        "factors",
        "verification",
        "verify",
        "verified",
    },

    "access_control": {
        "access",
        "permission",
        "permissions",
        "authorization",
        "authorized",
        "authorize",
        "role",
        "roles",
        "request",
        "requests",
        "manager",
        "managers",
        "provision",
        "provisioning",
    },

    "device_protection": {
        "device",
        "devices",
        "computer",
        "computers",
        "laptop",
        "laptops",
        "lock",
        "locking",
        "software",
        "updates",
        "update",
        "protection",
        "protect",
        "protecting",
        "data",
        "encryption",
    },

    "incident_reporting": {
        "incident",
        "incidents",
        "report",
        "reports",
        "reporting",
        "reported",
        "phishing",
        "lost",
        "unauthorized",
        "exposure",
        "breach",
        "breaches",
        "notify",
        "notification",
    },

    "dental_vision": {
        "dental",
        "vision",
        "optical",
    },

    "sick_leave": {
        "sick",
        "illness",
        "ill",
        "medical",
        "absence",
        "absences",
    },
}


@dataclass(frozen=True)
class RerankedResult:
    """A retrieved chunk with its reranking score."""

    result: RetrievalResult
    score: float


class CrossEncoderReranker:
    """
    Rerank retrieved chunks using direct lexical matching,
    focused concept coverage, and the original retrieval score.

    This is an explainable heuristic, not a trained cross-encoder.
    """

    def _tokenize(self, text: str) -> set[str]:
        """Extract lowercase tokens and remove possessive endings."""

        normalized_text = re.sub(
            r"\b([a-z]+)'s\b",
            r"\1",
            text.lower(),
        )

        tokens = re.findall(r"\b[a-z]+\b", normalized_text)

        return {
            token
            for token in tokens
            if token not in STOPWORDS and len(token) > 1
        }

    def _normalize_match_terms(self, terms: set[str]) -> set[str]:
        """
        Normalize selected word variants for matching
        without changing the original tokenizer output.
        """

        normalized = set(terms)

        if "passwords" in normalized:
            normalized.add("password")

        return normalized

    def _query_concepts(
        self,
        query_terms: set[str],
    ) -> dict[str, set[str]]:
        """Identify focused concepts represented in the query."""

        return {
            concept: terms
            for concept, terms in CONCEPTS.items()
            if query_terms & terms
        }

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RerankedResult]:
        """Rank candidates using lexical and focused concept relevance."""

        if not query.strip():
            return []

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        if not results:
            return []

        query_terms = self._tokenize(query)

        if not query_terms:
            return [
                RerankedResult(
                    result=result,
                    score=float(result.score),
                )
                for result in results[:top_k]
            ]

        query_concepts = self._query_concepts(query_terms)

        normalized_query_terms = self._normalize_match_terms(
            query_terms
        )

        reranked_results = []

        for result in results:
            document_terms = self._tokenize(result.chunk.text)

            normalized_document_terms = self._normalize_match_terms(
                document_terms
            )

            direct_overlap = len(
                normalized_query_terms & normalized_document_terms
            )

            direct_score = (
                direct_overlap / len(normalized_query_terms)
            )

            if query_concepts:
                matched_concepts = sum(
                    bool(concept_terms & document_terms)
                    for concept_terms in query_concepts.values()
                )

                concept_score = (
                    matched_concepts / len(query_concepts)
                )
            else:
                concept_score = direct_score

            lexical_score = (
                0.75 * concept_score
                + 0.25 * direct_score
            )

            combined_score = (
                0.65 * lexical_score
                + 0.35 * float(result.score)
            )

            reranked_results.append(
                RerankedResult(
                    result=result,
                    score=float(combined_score),
                )
            )

        reranked_results.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return reranked_results[:top_k]
