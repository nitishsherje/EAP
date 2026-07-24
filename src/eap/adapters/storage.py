"""Object storage adapter - transport to S3 / approved object storage.

``InMemoryObjectStorage`` powers local/dev. The S3 implementation is a stub wired
via boto3 (``adapters`` extra); credentials come from instance role / secrets.
"""

from __future__ import annotations

from eap.adapters.base import AdapterConfig, ObjectStorageAdapter


class InMemoryObjectStorage(ObjectStorageAdapter):
    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config
        self._blobs: dict[str, bytes] = {}

    def get_object(self, key: str) -> bytes | None:
        return self._blobs.get(key)

    def put_object(self, key: str, data: bytes) -> None:
        self._blobs[key] = data


class S3ObjectStorage(ObjectStorageAdapter):
    def __init__(self, config: AdapterConfig) -> None:  # pragma: no cover - stub
        self._config = config

    def get_object(self, key: str) -> bytes | None:  # pragma: no cover - stub
        raise NotImplementedError("Wire boto3 S3 client here.")

    def put_object(self, key: str, data: bytes) -> None:  # pragma: no cover - stub
        raise NotImplementedError("Wire boto3 S3 client here.")
