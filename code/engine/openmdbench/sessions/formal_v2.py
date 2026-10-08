"""Create native V2 sessions for installed formal data-only scenario packages."""

from __future__ import annotations

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.gateway_v2 import AgentGatewayV2
from openmdbench.sessions.lifecycle_v2 import (
    RunnerModeV2,
    SessionCheckpointV2,
    SessionLifecycleV2,
)
from openmdbench.world.factory_v2 import WorldFactoryV2


def create_formal_session_v2(
    public_id: str,
    *,
    session_id: str,
    seed: int = 0,
    runner_mode: RunnerModeV2 = RunnerModeV2.LOCKSTEP,
) -> SessionLifecycleV2:
    resolved, catalog = compile_formal_scenario_v2(public_id)
    return SessionLifecycleV2.create(
        session_id=session_id,
        seed=seed,
        resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=runner_mode,
        physics_dt_seconds=float(resolved.world.tick_seconds or 1.0),
        decision_interval_ticks=1,
    )


def create_formal_gateway_v2(public_id: str) -> AgentGatewayV2:
    """Bind one transport-independent gateway to an installed formal scenario package."""

    resolved, catalog = compile_formal_scenario_v2(public_id)

    def create(session_id: str, seed: int) -> SessionLifecycleV2:
        return SessionLifecycleV2.create(
            session_id=session_id,
            seed=seed,
            resolved=resolved,
            expected_resolved_hash=resolved.resolved_hash,
            catalog_hash=resolved.catalog_hash,
            model_registry_hash=resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
            runner_mode=RunnerModeV2.LOCKSTEP,
            physics_dt_seconds=float(resolved.world.tick_seconds or 1.0),
            decision_interval_ticks=1,
        )

    def restore(checkpoint: SessionCheckpointV2) -> SessionLifecycleV2:
        typed = SessionCheckpointV2.model_validate(checkpoint)
        factory = WorldFactoryV2(model_registry=catalog.model_registry)
        return SessionLifecycleV2.restore(
            checkpoint=typed,
            expected_checkpoint_hash=typed.checkpoint_hash,
            resolved=resolved,
            expected_resolved_hash=resolved.resolved_hash,
            model_registry=catalog.model_registry,
            expected_model_registry_hash=resolved.model_registry_hash,
            world_factory=factory,
        )

    def visualization(session: SessionLifecycleV2, faction_id: str) -> object:
        from openmdbench.visualization.formal_v2 import build_formal_frame_v2

        return build_formal_frame_v2(session, catalog, view="faction", faction_id=faction_id)

    return AgentGatewayV2(
        session_factory=create,
        restore_factory=restore,
        visualization_factory=visualization,
    )


__all__ = ["create_formal_gateway_v2", "create_formal_session_v2"]
