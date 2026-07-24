"""Knowledge Service (Layer 4) - retrieval intelligence over knowledge backends.

Retrieval strategy, query planning, (optional) reranking, permission filtering and
citation assembly live HERE, not in the Milvus adapter. Agents reference
``knowledge://...`` and never see hostnames, collections or credentials. Milvus is
one backend selected by the binding.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from eap.adapters import VectorQuery, build_vector_adapter
from eap.adapters.base import VectorHit
from eap.common.config import Settings
from eap.common.errors import EapError, ErrorCode
from eap.observability import Telemetry, get_logger
from eap.security import DataClassification, Principal, SecretsProvider
from eap.specifications.knowledge import RetrievalStrategy
from eap.specifications.resolved_definition import ResolvedDefinition

_log = get_logger("eap.knowledge")

# Roles permitted to see each classification level.
_RESTRICTED_ROLES = {"platform-admin", "data-steward"}


@dataclass
class Chunk:
    id: str
    text: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    knowledge: str
    query: str
    chunks: list[Chunk] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, hits: list[VectorHit], top_n: int) -> list[VectorHit]: ...


class ScoreReranker(Reranker):
    """Default reranker: order by backend score and truncate. Pluggable."""

    def rerank(self, query: str, hits: list[VectorHit], top_n: int) -> list[VectorHit]:
        return sorted(hits, key=lambda h: h.score, reverse=True)[:top_n]


class KnowledgeService:
    def __init__(
        self,
        settings: Settings,
        secrets: SecretsProvider,
        reranker: Reranker | None = None,
        telemetry: Telemetry | None = None,
    ) -> None:
        self._settings = settings
        self._secrets = secrets
        self._reranker = reranker or ScoreReranker()
        self._telemetry = telemetry or Telemetry()

    def retrieve(
        self,
        rd: ResolvedDefinition,
        knowledge_ref: str,
        query: str,
        principal: Principal | None = None,
    ) -> RetrievalResult:
        principal = principal or Principal.system()
        pinned = rd.pin(knowledge_ref)
        knowledge = rd.bundle.knowledge.get(pinned)
        if knowledge is None:
            raise EapError(
                f"knowledge {pinned} not in resolved definition", code=ErrorCode.NOT_FOUND
            )
        binding = rd.binding_for(knowledge_ref)
        if binding is None:
            raise EapError(f"no binding for knowledge {pinned}", code=ErrorCode.BINDING_MISSING)

        collection = binding.spec.config.get("collection", knowledge.metadata.name)
        spec = knowledge.spec

        with self._telemetry.span("knowledge.retrieve", knowledge=knowledge.metadata.name):
            hits = self._backend_search(binding, collection, query, spec)
            hits = self._filter_permissions(hits, spec, principal)
            if spec.rerank.enabled:
                hits = self._reranker.rerank(query, hits, spec.rerank.top_n)

        chunks = [
            Chunk(
                id=h.id,
                text=h.text,
                score=h.score,
                source=h.metadata.get("source", ""),
                metadata=h.metadata,
            )
            for h in hits
        ]
        citations = self._assemble_citations(chunks) if spec.citations else []
        return RetrievalResult(knowledge=pinned, query=query, chunks=chunks, citations=citations)

    # --- internals ---
    def _backend_search(self, binding, collection, query, spec) -> list[VectorHit]:  # noqa: ANN001
        # Query planning: choose backend behaviour per strategy. Vector/hybrid both
        # use the vector adapter in MVP1; a keyword-only path would use a DB adapter.
        adapter = build_vector_adapter(binding, self._secrets, self._settings)
        vq = VectorQuery(text=query, top_k=spec.top_k)
        hits = adapter.search(collection, vq)
        if spec.strategy == RetrievalStrategy.KEYWORD:
            _log.debug("keyword strategy requested; using vector backend as fallback in MVP1")
        return hits

    def _filter_permissions(self, hits, spec, principal) -> list[VectorHit]:  # noqa: ANN001
        if not spec.permission_scoped:
            return hits
        allowed: list[VectorHit] = []
        for hit in hits:
            classification = hit.metadata.get("classification", "internal")
            if classification == DataClassification.RESTRICTED.value and not (
                principal.roles & _RESTRICTED_ROLES
            ):
                continue
            allowed.append(hit)
        return allowed

    @staticmethod
    def _assemble_citations(chunks: list[Chunk]) -> list[str]:
        seen: list[str] = []
        for chunk in chunks:
            if chunk.source and chunk.source not in seen:
                seen.append(chunk.source)
        return seen


__all__ = ["Chunk", "KnowledgeService", "Reranker", "RetrievalResult", "ScoreReranker"]
