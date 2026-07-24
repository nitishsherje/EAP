"""FastAPI surface for EAP (Layer 6).

Thin HTTP layer over the composition root: authentication, request validation
against the spec contract, and the register / resolve / run endpoints. All heavy
lifting is delegated to the control plane and runtime.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from eap.api_gateway.assembly import EapApplication, build_app_with_examples
from eap.common.errors import EapError
from eap.security import Principal
from eap.specifications.loader import parse_resource

app = FastAPI(title="Core EAP", version="1.0.0")
_eap: EapApplication = build_app_with_examples()


def get_app() -> EapApplication:
    return _eap


def get_principal(
    authorization: str | None = Header(default=None),
    application: EapApplication = Depends(get_app),
) -> Principal:
    token = authorization.split(" ", 1)[-1] if authorization else None
    return application.authenticate(token)


class RegisterRequest(BaseModel):
    resource: dict[str, Any]
    publish: bool = False


class ResolveRequest(BaseModel):
    ref: str
    environment: str | None = None


class RunRequest(BaseModel):
    ref: str
    query: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    environment: str | None = None


class FeedbackRequest(BaseModel):
    run_id: str
    rating: int
    comment: str = ""


def _handle(exc: EapError) -> HTTPException:
    status = {
        "security.unauthenticated": 401,
        "security.unauthorized": 403,
        "governance.policy_denied": 403,
        "registry.not_found": 404,
        "registry.already_exists": 409,
    }.get(exc.code.value, 400)
    return HTTPException(status_code=status, detail=exc.to_dict())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/v1/catalog")
def catalog(application: EapApplication = Depends(get_app)) -> list[dict]:
    return [entry.__dict__ for entry in application.control_plane.catalog.list()]


@app.post("/v1/specs")
def register_spec(
    body: RegisterRequest,
    application: EapApplication = Depends(get_app),
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        resource = parse_resource(body.resource)
        application.register(resource, principal, publish=body.publish)
    except EapError as exc:
        raise _handle(exc) from exc
    return {"registered": resource.key, "published": body.publish}


@app.post("/v1/resolve")
def resolve(
    body: ResolveRequest,
    application: EapApplication = Depends(get_app),
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        rd = application.resolve(body.ref, body.environment, principal)
    except EapError as exc:
        raise _handle(exc) from exc
    return {
        "target": rd.target,
        "environment": rd.environment,
        "content_hash": rd.content_hash,
        "effective_policy": rd.effective_policy.model_dump(),
        "bindings": list(rd.bundle.bindings),
    }


@app.post("/v1/agents/run")
def run_agent(
    body: RunRequest,
    application: EapApplication = Depends(get_app),
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        result = application.run_agent(
            body.ref, query=body.query, inputs=body.inputs, principal=principal, environment=body.environment
        )
    except EapError as exc:
        raise _handle(exc) from exc
    return {
        "run_id": result.run_id,
        "status": result.status,
        "content": result.content,
        "output": result.output,
        "citations": result.citations,
        "tokens": {"prompt": result.prompt_tokens, "completion": result.completion_tokens},
        "used_fallback": result.used_fallback,
        "error": result.error,
    }


@app.post("/v1/feedback")
def submit_feedback(
    body: FeedbackRequest,
    application: EapApplication = Depends(get_app),
    principal: Principal = Depends(get_principal),
) -> dict:
    fb = application.record_feedback(body.run_id, body.rating, body.comment, principal.subject)
    return {"id": fb.id, "run_id": fb.run_id, "rating": fb.rating}


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str, application: EapApplication = Depends(get_app)) -> dict:
    run = application.metadata_repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "registry.not_found", "message": "run not found"})
    return run.model_dump()
