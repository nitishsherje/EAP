"""Adapter interfaces + transport DTOs (Layer 3).

Adapters are thin transport translators to existing CRISIL backends. They contain
NO business logic (no retrieval strategy, no routing, no guardrails). All physical
configuration and credentials are injected via ``AdapterConfig`` at construction;
nothing is hardcoded.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AdapterConfig:
    """Resolved, environment-bound configuration for a single adapter instance.

    ``secret`` is the *resolved* secret value (fetched by the composition root via
    the SecretsProvider from the binding's ``secret_ref``). Adapters never see the
    logical secret name, and secrets never appear in specs or bindings.
    """

    adapter: str
    endpoint: str | None = None
    secret: str | None = None
    config: dict = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 2


# --------------------------------------------------------------------------- #
# LLM                                                                          #
# --------------------------------------------------------------------------- #
@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str


@dataclass
class LLMRequest:
    deployment: str
    messages: list[Message]
    parameters: dict = field(default_factory=dict)
    structured: bool = False


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    finish_reason: str = "stop"


class LLMAdapter(ABC):
    """Transport to a chat/completions endpoint (e.g. CRISIL LLM Gateway)."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]: ...


# --------------------------------------------------------------------------- #
# Generic HTTP API (Docling, enterprise APIs)                                 #
# --------------------------------------------------------------------------- #
@dataclass
class APIRequest:
    method: str
    path: str
    body: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)


@dataclass
class APIResponse:
    status: int
    body: dict = field(default_factory=dict)


class APIAdapter(ABC):
    """Transport to an HTTP API behind an enterprise gateway."""

    @abstractmethod
    def call(self, request: APIRequest) -> APIResponse: ...


# --------------------------------------------------------------------------- #
# Vector store (Milvus)                                                        #
# --------------------------------------------------------------------------- #
@dataclass
class VectorQuery:
    text: str
    top_k: int = 10
    filters: dict = field(default_factory=dict)


@dataclass
class VectorHit:
    id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class VectorStoreAdapter(ABC):
    """Transport to a vector search backend. No retrieval strategy lives here."""

    @abstractmethod
    def search(self, collection: str, query: VectorQuery) -> list[VectorHit]: ...


# --------------------------------------------------------------------------- #
# Object storage (S3)                                                         #
# --------------------------------------------------------------------------- #
class ObjectStorageAdapter(ABC):
    @abstractmethod
    def get_object(self, key: str) -> bytes | None: ...

    @abstractmethod
    def put_object(self, key: str, data: bytes) -> None: ...
