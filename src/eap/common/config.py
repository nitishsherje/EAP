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


@dataclass(frozen=True)
class Settings:
    """Environment-agnostic platform settings (no secrets)."""

    environment: str = _env("EAP_ENV", "dev")

    # Backend selection: "memory"/"fake" run the walking skeleton with no
    # external infra; real values plug in existing CRISIL capabilities.
    metadata_backend: str = _env("EAP_METADATA_BACKEND", "memory")  # memory | postgres
    artifact_backend: str = _env("EAP_ARTIFACT_BACKEND", "memory")  # memory | s3
    llm_backend: str = _env("EAP_LLM_BACKEND", "fake")  # fake | gateway
    docling_backend: str = _env("EAP_DOCLING_BACKEND", "fake")  # fake | gateway
    api_backend: str = _env("EAP_API_BACKEND", "fake")  # fake | real (enterprise APIs)
    vector_backend: str = _env("EAP_VECTOR_BACKEND", "memory")  # memory | milvus

    # Cross-cutting toggles.
    otel_enabled: bool = _flag("EAP_OTEL_ENABLED", False)
    auth_enabled: bool = _flag("EAP_AUTH_ENABLED", False)

    @staticmethod
    def load() -> Settings:
        return Settings()
