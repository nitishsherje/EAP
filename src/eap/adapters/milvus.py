"""Milvus adapter - transport to the enterprise Milvus vector store.

Milvus is an implementation backend. Retrieval strategy, reranking and permission
filtering live in the Knowledge Service, not here. ``InMemoryVectorAdapter`` powers
local/dev with a trivial keyword-overlap score.
"""

from __future__ import annotations

from eap.adapters.base import AdapterConfig, VectorHit, VectorQuery, VectorStoreAdapter
from eap.common.errors import AdapterError

# A tiny seeded corpus so the walking skeleton returns plausible hits.
_SEED_CORPUS: dict[str, list[dict]] = {
    "ratings_knowledge_v2": [
        {
            "id": "doc-1",
            "text": "Rating methodology weighs leverage, coverage and liquidity ratios.",
            "metadata": {"source": "ratings-methodology.pdf", "classification": "confidential"},
        },
        {
            "id": "doc-2",
            "text": "Auditor findings on revenue recognition can affect the rating outlook.",
            "metadata": {"source": "audit-guidance.pdf", "classification": "confidential"},
        },
        {
            "id": "doc-3",
            "text": "Material misstatements require re-evaluation of the credit assessment.",
            "metadata": {"source": "credit-policy.pdf", "classification": "confidential"},
        },
    ]
}


class InMemoryVectorAdapter(VectorStoreAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config

    def search(self, collection: str, query: VectorQuery) -> list[VectorHit]:
        corpus = _SEED_CORPUS.get(collection, [])
        terms = {t.lower() for t in query.text.split() if len(t) > 2}
        scored: list[VectorHit] = []
        for row in corpus:
            words = {w.lower().strip(".,") for w in row["text"].split()}
            overlap = len(terms & words)
            score = overlap / (len(terms) or 1)
            scored.append(
                VectorHit(id=row["id"], text=row["text"], score=round(score, 4), metadata=row["metadata"])
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[: query.top_k]


class MilvusAdapter(VectorStoreAdapter):
    def __init__(self, config: AdapterConfig) -> None:
        if not config.endpoint:
            raise AdapterError("Milvus endpoint is required")
        self._config = config

    def search(self, collection: str, query: VectorQuery) -> list[VectorHit]:  # pragma: no cover
        raise NotImplementedError(
            "Wire pymilvus here (embed query via embedding profile, then search). "
            "Install the 'adapters' extra and set EAP_VECTOR_BACKEND=milvus."
        )
