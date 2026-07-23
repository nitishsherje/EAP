# §18 — Persistence

## Logical stores

| Store | Interface | Default impl | Real backend | Owns |
| --- | --- | --- | --- | --- |
| Metadata | `MetadataRepository` | `InMemoryMetadataRepository` | `PostgresMetadataRepository` **STUB** | resources, aliases, run records |
| Artifacts | `ArtifactStore` | `InMemoryArtifactStore` | `S3ArtifactStore` **STUB** | ResolvedDefinition JSON blobs |
| State | `StateStore` | `InMemoryStateStore` | `PostgresStateStore` **STUB** | checkpoints |

Factories: `persistence/__init__.py` `build_metadata_repository`, `build_artifact_store`, `build_state_store`.

## Redis

Listed under optional `adapters` extra in `pyproject.toml`. **No Redis client or cache usage exists in `src/eap/`.** Status: PLANNED / NOT IMPLEMENTED.

## Models

`persistence/models.py`: `ResourceRecord`, `RunRecord`, `Checkpoint`, `LifecycleStatus`, `RunStatus`.

## Suggested Postgres schema

Documented as comments in `persistence/postgres.py` (resources, aliases, runs, checkpoints) — not applied migrations in-repo.
