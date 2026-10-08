"""Thin REST transport for AgentGatewayV2."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.schemas.interface_v2 import ActionBatchV2
from openmdbench.sessions.gateway_v2 import AgentGatewayV2
from openmdbench.sessions.lifecycle_v2 import SessionCheckpointV2


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


class CreateSessionRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1)
    seed: int = Field(ge=0)


class RestoreSessionRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checkpoint: SessionCheckpointV2


class ControlRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = Field(min_length=1)


class SubmitRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch: ActionBatchV2
    authority_token: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    expected_tick: int = Field(ge=0)


class StepRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str = Field(min_length=1)
    expected_tick: int = Field(ge=0)


def create_gateway_app_v2(gateway: AgentGatewayV2) -> FastAPI:
    app = FastAPI()

    def translate(function: Any) -> Any:
        try:
            return function()
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (TypeError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/v2/sessions")
    async def sessions() -> dict[str, Any]:
        return {"session_ids": gateway.session_ids}

    @app.post("/v2/sessions", status_code=201)
    async def create(request: CreateSessionRequestV2) -> dict[str, Any]:
        session_id = translate(
            lambda: gateway.create(session_id=request.session_id, seed=request.seed)
        )
        return {"session_id": session_id}

    @app.post("/v2/sessions/restore", status_code=201)
    async def restore(request: RestoreSessionRequestV2) -> dict[str, Any]:
        session_id = translate(lambda: gateway.restore(request.checkpoint))
        return {"session_id": session_id}

    @app.post("/v2/sessions/{session_id}/control")
    async def control(session_id: str, request: ControlRequestV2) -> dict[str, Any]:
        state = translate(lambda: gateway.control(session_id, request.operation))
        return {"session_id": session_id, "state": state.value}

    @app.get("/v2/sessions/{session_id}/observation")
    async def observation(session_id: str, faction_id: str) -> Any:
        value = translate(lambda: gateway.observation(session_id, faction_id=faction_id))
        return value.model_dump(mode="json")

    @app.post("/v2/sessions/{session_id}/actions")
    async def actions(session_id: str, request: SubmitRequestV2) -> Any:
        value = translate(
            lambda: gateway.submit(
                session_id,
                batch=request.batch,
                authority_token=request.authority_token,
                operation_id=request.operation_id,
                expected_tick=request.expected_tick,
            )
        )
        return value.model_dump(mode="json")

    @app.post("/v2/sessions/{session_id}/step")
    async def step(session_id: str, request: StepRequestV2) -> Any:
        value = translate(
            lambda: gateway.step(
                session_id,
                operation_id=request.operation_id,
                expected_tick=request.expected_tick,
            )
        )
        return value.model_dump(mode="json")

    @app.get("/v2/sessions/{session_id}/checkpoint")
    async def checkpoint(session_id: str) -> Any:
        value = translate(lambda: gateway.checkpoint(session_id))
        return value.model_dump(mode="json")

    @app.get("/v2/sessions/{session_id}/commands/{child_id}")
    async def command_status(session_id: str, child_id: str) -> dict[str, str]:
        return {
            "session_id": session_id,
            "child_id": child_id,
            "status": translate(lambda: gateway.command_status(session_id, child_id)),
        }

    @app.get("/v2/sessions/{session_id}/events")
    async def events(session_id: str) -> dict[str, Any]:
        return {"events": _json_value(translate(lambda: gateway.events(session_id)))}

    @app.get("/v2/sessions/{session_id}/result")
    async def result(session_id: str) -> Any:
        return _json_value(translate(lambda: gateway.result(session_id)))

    @app.get("/v2/sessions/{session_id}/visualization")
    async def visualization(session_id: str, faction_id: str) -> Any:
        value = translate(lambda: gateway.visualization(session_id, faction_id=faction_id))
        return value.model_dump(mode="json")

    @app.get("/v2/sessions/{session_id}/replay")
    async def replay(session_id: str, faction_id: str) -> Any:
        return _json_value(
            translate(lambda: gateway.replay_artifact(session_id, faction_id=faction_id))
        )

    @app.delete("/v2/sessions/{session_id}", status_code=204)
    async def close(session_id: str) -> None:
        translate(lambda: gateway.close(session_id))

    return app


__all__ = [
    "CreateSessionRequestV2",
    "RestoreSessionRequestV2",
    "create_gateway_app_v2",
]
