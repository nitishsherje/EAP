"""KnowledgeSpec - a governed knowledge source with retrieval + access policy.

    knowledge://ratings-knowledge/2.0.0

Agents reference the logical knowledge source; they never know the Milvus
hostname, collection, or credentials. Retrieval intelligence lives in the
Knowledge Service, not in the backend adapter. Milvus (and any DB/S3/API) is an
implementation backend selected by binding.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from eap.specifications.envelope import EapResource, ResourceKind


class RetrievalStrategy(str, Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"  # vector + keyword
    KEYWORD = "keyword"


class RerankConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    model: str | None = None  # logical reranker id, resolved at bind time
    top_n: int = 5


class KnowledgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Logical backend family; concrete endpoint/collection comes from binding.
    source: str = "vector-store"  # vector-store | database | document-store | api
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    embedding_profile: str | None = None  # logical embedding model id
    top_k: int = 10
    rerank: RerankConfig = Field(default_factory=RerankConfig)
    # Access control applied during retrieval (permission filtering).
    permission_scoped: bool = True
    classification: str = "internal"
    citations: bool = True


class Knowledge(EapResource):
    expected_kind: ClassVar[ResourceKind] = ResourceKind.KNOWLEDGE

    kind: ResourceKind = ResourceKind.KNOWLEDGE
    spec: KnowledgeSpec
