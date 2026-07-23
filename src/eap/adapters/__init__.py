"""Adapters (Layer 3) - thin transport to existing CRISIL capabilities.

Factories translate an environment-bound CapabilityBinding into a configured
adapter instance, resolving the secret *value* from the SecretsProvider using the
binding's logical ``secret_ref``. Backend selection (fake vs. real) is driven by
Settings so the same code runs locally and against CRISIL infra.
"""

from __future__ import annotations

from eap.adapters.base import (
    AdapterConfig,
    APIAdapter,
    APIRequest,
    APIResponse,
    LLMAdapter,
    LLMRequest,
    LLMResponse,
    Message,
    ObjectStorageAdapter,
    VectorHit,
    VectorQuery,
    VectorStoreAdapter,
)
from eap.common.config import Settings
from eap.security import SecretsProvider
from eap.specifications.binding import CapabilityBinding


def build_adapter_config(binding: CapabilityBinding, secrets: SecretsProvider) -> AdapterConfig:
    spec = binding.spec
    secret_value = secrets.get_secret(spec.auth.secret_ref) if spec.auth.secret_ref else None
    return AdapterConfig(
        adapter=spec.adapter,
        endpoint=spec.endpoint,
        secret=secret_value,
        config=dict(spec.config),
        timeout_seconds=spec.timeout_seconds,
        max_retries=spec.max_retries,
    )


def build_llm_adapter(
    binding: CapabilityBinding, secrets: SecretsProvider, settings: Settings
) -> LLMAdapter:
    cfg = build_adapter_config(binding, secrets)
    if settings.llm_backend == "gateway":
        from eap.adapters.llm_gateway import CrisilLLMGatewayAdapter

        return CrisilLLMGatewayAdapter(cfg)
    from eap.adapters.llm_gateway import FakeLLMAdapter

    return FakeLLMAdapter(cfg)


def build_api_adapter(
    binding: CapabilityBinding, secrets: SecretsProvider, settings: Settings
) -> APIAdapter:
    cfg = build_adapter_config(binding, secrets)
    adapter_id = binding.spec.adapter
    if adapter_id == "docling":
        if settings.docling_backend == "gateway":
            from eap.adapters.docling import DoclingGatewayAdapter

            return DoclingGatewayAdapter(cfg)
        from eap.adapters.docling import FakeDoclingAdapter

        return FakeDoclingAdapter(cfg)
    # enterprise_api (default)
    if settings.api_backend == "real":
        from eap.adapters.enterprise_api import EnterpriseAPIAdapter

        return EnterpriseAPIAdapter(cfg)
    from eap.adapters.enterprise_api import FakeEnterpriseAPIAdapter

    return FakeEnterpriseAPIAdapter(cfg)


def build_vector_adapter(
    binding: CapabilityBinding, secrets: SecretsProvider, settings: Settings
) -> VectorStoreAdapter:
    cfg = build_adapter_config(binding, secrets)
    if settings.vector_backend == "milvus":
        from eap.adapters.milvus import MilvusAdapter

        return MilvusAdapter(cfg)
    from eap.adapters.milvus import InMemoryVectorAdapter

    return InMemoryVectorAdapter(cfg)


__all__ = [
    "APIAdapter",
    "APIRequest",
    "APIResponse",
    "AdapterConfig",
    "LLMAdapter",
    "LLMRequest",
    "LLMResponse",
    "Message",
    "ObjectStorageAdapter",
    "VectorHit",
    "VectorQuery",
    "VectorStoreAdapter",
    "build_adapter_config",
    "build_api_adapter",
    "build_llm_adapter",
    "build_vector_adapter",
]
