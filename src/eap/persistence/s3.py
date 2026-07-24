"""S3 / object-storage artifact store (stub).

Wiring point for approved CRISIL S3 object storage. In-memory store covers MVP1;
implement against boto3 (``adapters`` extra) when artifacts must be durable.
Credentials come from instance role / SecretsProvider, never from source.
"""

from __future__ import annotations

from eap.persistence.base import ArtifactStore

_NOT_IMPLEMENTED = (
    "S3 artifact store is not yet implemented. Set EAP_ARTIFACT_BACKEND=memory for "
    "local/dev, or implement S3ArtifactStore against boto3."
)


class S3ArtifactStore(ArtifactStore):
    def __init__(self, bucket: str, prefix: str = "eap/") -> None:  # pragma: no cover - stub
        raise NotImplementedError(_NOT_IMPLEMENTED)
