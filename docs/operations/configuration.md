# §17 — Configuration & Environment Binding

## Portable specs + env-specific bindings

The same Agent/Skill/Capability/Knowledge YAML can run in DEV/UAT/PROD by registering **different CapabilityBinding documents** per `spec.environment` and resolving with that environment name.

```text
resolve(ref, environment="dev"|"uat"|"prod")
  → Resolver selects bindings where binding.spec.environment == environment
```

Missing bindings → `ResolutionError`.

## Settings (environment variables)

From `eap.common.config.Settings`:

| Env var | Default | Meaning |
| --- | --- | --- |
| `EAP_ENV` | `dev` | Default resolve environment |
| `EAP_METADATA_BACKEND` | `memory` | `memory` \| `postgres` |
| `EAP_ARTIFACT_BACKEND` | `memory` | `memory` \| `s3` |
| `EAP_LLM_BACKEND` | `fake` | `fake` \| `gateway` |
| `EAP_DOCLING_BACKEND` | `fake` | `fake` \| `gateway` |
| `EAP_API_BACKEND` | `fake` | `fake` \| `real` |
| `EAP_VECTOR_BACKEND` | `memory` | `memory` \| `milvus` |
| `EAP_OTEL_ENABLED` | false | Enable OTel tracer if installed |
| `EAP_AUTH_ENABLED` | false | Passed as governance `enforce_policies` |

## Secrets

| Mechanism | Status |
| --- | --- |
| Binding `auth.secret_ref` | IMPLEMENTED in models |
| `EnvSecretsProvider` | IMPLEMENTED — reads `EAP_SECRET_<NAME>` (dashes → underscores, uppercased) |
| Secret values in YAML | Forbidden by design; not present in examples |

Example: `secret_ref: docling-oauth` → env `EAP_SECRET_DOCLING_OAUTH`.

## Endpoint resolution

Adapters receive `AdapterConfig(endpoint=binding.spec.endpoint, secret=secrets.get_secret(...), …)` from factory helpers in `adapters/__init__.py`.

## Example overlay intent

| Env | Bindings | Settings |
| --- | --- | --- |
| DEV | `bindings.dev.yaml` endpoints to `*.dev.crisil.internal` | often fakes for laptop |
| PROD | Separate binding docs (not fully checked in beyond K8s overlay config) | real backends via env |

K8s ConfigMap patches: `deploy/kubernetes/overlays/dev/config-patch.yaml`, prod resource patches.
