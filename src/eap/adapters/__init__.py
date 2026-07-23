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


def build_adapter_config(
    binding: CapabilityBinding,
    secrets: SecretsProvider,
    settings: Settings | None = None,
    *,
    correlation_id: str = "",
) -> AdapterConfig:
    spec = binding.spec
    secret_value = secrets.get_secret(spec.auth.secret_ref) if spec.auth.secret_ref else None
    cfg = dict(spec.config)
    headers = dict(cfg.pop("headers", {}) or {})
    endpoint = spec.endpoint
    timeout = spec.timeout_seconds
    path = cfg.get("path")
    method = str(cfg.get("method", "POST"))
    verify_tls = True

    if settings is not None:
        adapter_id = spec.adapter
        if adapter_id == "llm_gateway":
            endpoint = endpoint or settings.llm_gateway_base_url or None
            path = path or settings.llm_gateway_path
            timeout = settings.llm_gateway_timeout_seconds or timeout
            verify_tls = settings.llm_gateway_verify_tls
            if settings.llm_gateway_model and "deployment" not in cfg:
                cfg["deployment"] = settings.llm_gateway_model
        elif adapter_id == "docling":
            endpoint = endpoint or settings.docling_base_url or None
            path = path or settings.docling_parse_path
            timeout = settings.docling_timeout_seconds or timeout
            verify_tls = settings.docling_verify_tls

    return AdapterConfig(
        adapter=spec.adapter,
        endpoint=endpoint,
        secret=secret_value,
        config=cfg,
        timeout_seconds=timeout,
        max_retries=spec.max_retries,
        path=str(path) if path else None,
        method=method,
        headers=headers,
        verify_tls=verify_tls,
        correlation_id=correlation_id,
    )


def build_llm_adapter(
    binding: CapabilityBinding,
    secrets: SecretsProvider,
    settings: Settings,
    *,
    correlation_id: str = "",
) -> LLMAdapter:
    cfg = build_adapter_config(binding, secrets, settings, correlation_id=correlation_id)
    if settings.llm_backend == "gateway":
        from eap.adapters.llm_gateway import CrisilLLMGatewayAdapter

        return CrisilLLMGatewayAdapter(cfg)
    from eap.adapters.llm_gateway import FakeLLMAdapter

    return FakeLLMAdapter(cfg)


def build_api_adapter(
    binding: CapabilityBinding,
    secrets: SecretsProvider,
    settings: Settings,
    *,
    correlation_id: str = "",
) -> APIAdapter:
    cfg = build_adapter_config(binding, secrets, settings, correlation_id=correlation_id)
    adapter_id = binding.spec.adapter
    if adapter_id == "docling":
        if settings.docling_backend == "gateway":
            from eap.adapters.docling import DoclingGatewayAdapter

            return DoclingGatewayAdapter(cfg)
        from eap.adapters.docling import FakeDoclingAdapter

        return FakeDoclingAdapter(cfg)
    if settings.api_backend == "real":
        from eap.adapters.enterprise_api import EnterpriseAPIAdapter

        return EnterpriseAPIAdapter(cfg)
    from eap.adapters.enterprise_api import FakeEnterpriseAPIAdapter

    return FakeEnterpriseAPIAdapter(cfg)


def build_vector_adapter(
    binding: CapabilityBinding, secrets: SecretsProvider, settings: Settings
) -> VectorStoreAdapter:
    cfg = build_adapter_config(binding, secrets, settings)
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
