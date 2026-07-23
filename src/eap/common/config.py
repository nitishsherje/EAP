"""Runtime configuration for the composition root.

Configuration selects *which* backends to wire (fakes vs. real CRISIL
capabilities). It never contains secrets or credentials - those are resolved at
bind time via the SecretsProvider. Values come from environment variables so the
same image runs unchanged across dev/qa/prod.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _flag(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _first_env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.environ.get(key)
        if value is not None and value.strip() != "":
            return value
    return default


@dataclass(frozen=True)
class Settings:
    """Environment-agnostic platform settings (secrets resolved via SecretsProvider)."""

    environment: str = _env("EAP_ENV", _env("APP_ENV", "dev"))

    # Backend selection: "memory"/"fake" run the walking skeleton with no
    # external infra; real values plug in existing CRISIL capabilities.
    metadata_backend: str = _env("EAP_METADATA_BACKEND", "memory")  # memory | postgres
    artifact_backend: str = _env("EAP_ARTIFACT_BACKEND", "memory")  # memory | s3
    llm_backend: str = _env("EAP_LLM_BACKEND", "fake")  # fake | gateway
    docling_backend: str = _env("EAP_DOCLING_BACKEND", "fake")  # fake | gateway
    api_backend: str = _env("EAP_API_BACKEND", "fake")  # fake | real (enterprise APIs)
    vector_backend: str = _env("EAP_VECTOR_BACKEND", "memory")  # memory | milvus

    # Enterprise gateway endpoints (bindings may still override per-environment).
    llm_gateway_base_url: str = _first_env("LLM_GATEWAY_BASE_URL", "EAP_LLM_GATEWAY_BASE_URL")
    llm_gateway_path: str = _first_env(
        "LLM_GATEWAY_PATH", "EAP_LLM_GATEWAY_PATH", default="/v1/chat/completions"
    )
    llm_gateway_model: str = _first_env("LLM_GATEWAY_MODEL", "EAP_LLM_GATEWAY_MODEL")
    llm_gateway_timeout_seconds: float = float(
        _first_env("LLM_GATEWAY_TIMEOUT_SECONDS", "EAP_LLM_GATEWAY_TIMEOUT_SECONDS", default="60")
    )
    llm_gateway_verify_tls: bool = _flag("LLM_GATEWAY_VERIFY_TLS", True)

    docling_base_url: str = _first_env("DOCLING_BASE_URL", "EAP_DOCLING_BASE_URL")
    docling_parse_path: str = _first_env(
        "DOCLING_PARSE_PATH", "EAP_DOCLING_PARSE_PATH", default="/v1/parse"
    )
    docling_timeout_seconds: float = float(
        _first_env("DOCLING_TIMEOUT_SECONDS", "EAP_DOCLING_TIMEOUT_SECONDS", default="30")
    )
    docling_verify_tls: bool = _flag("DOCLING_VERIFY_TLS", True)

    # Cross-cutting toggles.
    otel_enabled: bool = _flag("EAP_OTEL_ENABLED", False)
    auth_enabled: bool = _flag("EAP_AUTH_ENABLED", False)

    @staticmethod
    def load() -> Settings:
        return Settings()
