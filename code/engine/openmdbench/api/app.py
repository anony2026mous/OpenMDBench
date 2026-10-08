"""FastAPI routes for local and remote benchmark sessions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.responses import Response

from openmdbench.api.models import ActionRequest, CreateSessionRequest, RestoreRequest
from openmdbench.api.sessions import Session, SessionStore
from openmdbench.domains.surface.actions import validate_kinematic_actions
from openmdbench.scenarios.loader import installed_scenarios
from openmdbench.schemas.platform import platform_json_schema


def _summary(session: Session) -> dict[str, object]:
    return {
        "session_id": session.session_id,
        "scenario_id": session.scenario_id,
        "seed": session.seed,
        "status": session.status,
        "timestamp": session.observation["timestamp"],
        **(session.env.config_metadata or {}),
    }


def create_app(store: SessionStore | None = None, *, max_body_bytes: int = 1_048_576) -> FastAPI:
    if max_body_bytes <= 0:
        raise ValueError("max_body_bytes must be positive")
    sessions = store or SessionStore()
    api = FastAPI(title="OpenMDBench API", version="1.0.0")

    def platform_openapi() -> dict[str, object]:
        if api.openapi_schema is not None:
            return api.openapi_schema
        document = get_openapi(title=api.title, version=api.version, routes=api.routes)
        components = document.setdefault("components", {}).setdefault("schemas", {})
        components.update(platform_json_schema().get("$defs", {}))
        api.openapi_schema = document
        return document

    api.openapi = platform_openapi  # type: ignore[method-assign]

    def error_response(
        request: Request, status_code: int, code: str, message: str, details: object = None
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=status_code,
            content={
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            },
        )

    @api.middleware("http")
    async def request_identity(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        content_length = request.headers.get("content-length")
        try:
            declared_size = int(content_length) if content_length is not None else None
        except ValueError:
            return error_response(request, 400, "invalid_content_length", "invalid Content-Length")
        if declared_size is not None and (declared_size < 0 or declared_size > max_body_bytes):
            return error_response(
                request, 413, "payload_too_large", "request body exceeds configured limit"
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_body_bytes:
                return error_response(
                    request, 413, "payload_too_large", "request body exceeds configured limit"
                )
        # Starlette reuses this bounded cache when the route parses the request body.
        request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @api.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code_by_status = {
            404: "not_found",
            409: "conflict",
            422: "invalid_action",
            429: "rate_limited",
        }
        return error_response(
            request,
            exc.status_code,
            code_by_status.get(exc.status_code, "http_error"),
            str(exc.detail),
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            request, 422, "validation_error", "request validation failed", exc.errors()
        )

    def find(session_id: str) -> Session:
        try:
            return sessions.get(session_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error

    @api.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @api.get("/health/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @api.get("/v1/scenarios")
    async def scenarios() -> list[dict[str, str]]:
        return [
            {
                "scenario_id": scenario.scenario_id,
                "category": scenario.category,
                "schema_version": scenario.schema_version,
            }
            for scenario in installed_scenarios()
        ]

    @api.get("/v1/schemas/platform/1.0")
    async def platform_schema() -> dict[str, object]:
        """Return the frozen RF-01 schema bundle used by SDK generators."""
        return platform_json_schema()

    @api.post("/v1/sessions", status_code=status.HTTP_201_CREATED)
    async def create(request: CreateSessionRequest) -> dict[str, object]:
        try:
            return _summary(sessions.create(request.scenario_id, request.seed))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.get("/v1/sessions/{session_id}")
    async def session_status(session_id: str) -> dict[str, object]:
        return _summary(find(session_id))

    @api.delete("/v1/sessions/{session_id}")
    async def close(session_id: str) -> dict[str, object]:
        return {**_summary(sessions.delete(find(session_id).session_id)), "status": "closed"}

    @api.get("/v1/sessions/{session_id}/observation")
    async def observation(session_id: str) -> dict[str, object]:
        session = find(session_id)
        sessions.record(
            session, "observation_read", {"timestamp": session.observation["timestamp"]}
        )
        if session.env._ad2_adjudicator is not None:
            return session.env.red_observation().model_dump(mode="json")
        if session.env.world is not None:
            return session.env.public_observation("blue").model_dump(mode="json")
        return dict(session.observation)

    @api.post("/v1/sessions/{session_id}/actions")
    async def actions(
        session_id: str,
        request: ActionRequest,
        idempotency_key: str = Header(min_length=1, max_length=128, alias="Idempotency-Key"),
    ) -> dict[str, object]:
        session = find(session_id)
        fingerprint = (
            request.timestamp,
            request.model_dump(mode="json", exclude_none=True),
        )
        cached = session.idempotency.get(idempotency_key)
        if cached is not None:
            if cached[0] != fingerprint:
                sessions.record(session, "action_rejected", {"reason": "idempotency_conflict"})
                raise HTTPException(status_code=409, detail="idempotency key payload conflict")
            return cached[1]
        if session.status != "running":
            sessions.record(session, "action_rejected", {"reason": "terminal"})
            raise HTTPException(status_code=409, detail="session is terminal")
        if request.timestamp != session.observation["timestamp"]:
            sessions.record(session, "action_rejected", {"reason": "timestamp_conflict"})
            raise HTTPException(status_code=409, detail="timestamp conflict")
        try:
            if request.action_batch is not None:
                if session.env._ad2_adjudicator is None:
                    raise ValueError("action_batch is only supported by MD-AD-002")
                sessions.check_rate_limit(session)
                result = sessions.step_action_batch(session, request.action_batch)
                session.idempotency[idempotency_key] = (fingerprint, result)
                return result
            if request.action is None:
                raise ValueError("missing action")
            if session.env._ad2_adjudicator is not None:
                raise ValueError("MD-AD-002 requires canonical action_batch")
            if session.env.world is None:
                validate_kinematic_actions(np.asarray(request.action, dtype=np.float32))
            else:
                speed, heading = request.action
                if not 0.0 <= speed <= 80.0 or not 0.0 <= heading < 360.0:
                    raise ValueError(
                        "formal runtime speed/heading is outside the public action range"
                    )
            sessions.check_rate_limit(session)
            result = sessions.step(session, request.action)
            session.idempotency[idempotency_key] = (fingerprint, result)
            return result
        except RuntimeError as error:
            sessions.record(session, "action_rejected", {"reason": "rate_limited"})
            raise HTTPException(status_code=429, detail=str(error)) from error
        except ValueError as error:
            sessions.record(session, "action_rejected", {"reason": "invalid_action"})
            raise HTTPException(status_code=422, detail=str(error)) from error

    @api.get("/v1/sessions/{session_id}/results")
    async def results(session_id: str) -> dict[str, object]:
        session = find(session_id)
        mission_result: dict[str, object] = {}
        if session.env._adjudicator is not None:
            adjudication = session.env._adjudicator.result
            mission_result = {
                "outcome": adjudication.outcome.value,
                "reason": adjudication.reason,
                "breach_latched": adjudication.breach_latched,
            }
        elif session.env._ad2_adjudicator is not None:
            ad2_adjudication = session.env._ad2_adjudicator.result
            mission_result = {
                "outcome": ad2_adjudication.outcome.value,
                "reason": ad2_adjudication.reason,
                "breach_count": ad2_adjudication.breach_count,
            }
        return {**_summary(session), "total_reward": session.total_reward, **mission_result}

    @api.post("/v1/sessions/{session_id}/checkpoints")
    async def checkpoint(session_id: str) -> dict[str, object]:
        session = find(session_id)
        result = session.checkpoint()
        sessions.record(
            session, "checkpoint_created", {"timestamp": session.observation["timestamp"]}
        )
        return result

    @api.post("/v1/sessions/{session_id}/restore", status_code=status.HTTP_201_CREATED)
    async def restore(session_id: str, request: RestoreRequest) -> dict[str, object]:
        find(session_id)
        try:
            return _summary(sessions.restore(request.checkpoint))
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return api


app = create_app(SessionStore(audit_dir="var/audit", replay_dir="var/replays"))
