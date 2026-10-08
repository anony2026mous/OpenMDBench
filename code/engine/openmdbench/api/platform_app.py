"""RF-09 REST vertical slice over :class:`AgentGateway` only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.sessions.gateway import AgentGateway
from openmdbench.sessions.session import ObservationSnapshot

T = TypeVar("T")


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateRequest(_Request):
    scenario_id: str
    seed: int = Field(default=0, ge=0)


class StepRequest(_Request):
    action: tuple[float, float] | None = None


class ControlRequest(_Request):
    operation: Literal["start", "pause", "resume", "cancel"]


def _snapshot(snapshot: ObservationSnapshot) -> dict[str, object]:
    return {
        "session_id": snapshot.session_id,
        "scenario_id": snapshot.scenario_id,
        "scenario_hash": snapshot.scenario_hash,
        "tick": snapshot.tick,
        "state": snapshot.state.value,
        "observation": snapshot.observation,
        "reward": snapshot.reward,
        "terminated": snapshot.terminated,
        "truncated": snapshot.truncated,
    }


def create_platform_app(gateway: AgentGateway | None = None) -> FastAPI:
    authority = gateway or AgentGateway()
    app = FastAPI(title="OpenMDBench Platform API", version="2.0.0")

    def guarded(call: Callable[[], T]) -> T:
        try:
            return call()
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.post("/v2/sessions", status_code=201)
    async def create(request: CreateRequest) -> dict[str, object]:
        session = guarded(lambda: authority.create(request.scenario_id, seed=request.seed))
        return _snapshot(session.snapshot())

    @app.get("/v2/sessions/{session_id}")
    async def status(session_id: str) -> dict[str, object]:
        return _snapshot(guarded(lambda: authority.snapshot(session_id)))

    @app.get("/v2/sessions/{session_id}/observation")
    async def observation(session_id: str) -> dict[str, object]:
        return _snapshot(guarded(lambda: authority.snapshot(session_id)))

    @app.post("/v2/sessions/{session_id}/step")
    async def step(session_id: str, request: StepRequest) -> dict[str, object]:
        return _snapshot(guarded(lambda: authority.step(session_id, request.action)))

    @app.post("/v2/sessions/{session_id}/control")
    async def control(session_id: str, request: ControlRequest) -> dict[str, object]:
        return _snapshot(guarded(lambda: authority.control(session_id, request.operation)))

    @app.get("/v2/sessions/{session_id}/frames/{view}")
    async def frame(session_id: str, view: Literal["referee", "blue", "red", "public"]) -> object:
        return guarded(lambda: authority.frame(session_id, view)).model_dump(mode="json")

    @app.delete("/v2/sessions/{session_id}", status_code=204)
    async def close(session_id: str) -> None:
        guarded(lambda: authority.close(session_id))

    return app
