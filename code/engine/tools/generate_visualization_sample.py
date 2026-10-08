"""Generate the committed M6 four-domain replay fixture deterministically."""

from pathlib import Path

from openmdbench.core.entities import Domain, Lifecycle, Side
from openmdbench.core.rng import configuration_hash
from openmdbench.replay import ReplayWriter
from openmdbench.scenarios.loader import load_scenario_id
from openmdbench.visualization.schema import (
    DetectionSets,
    EnvironmentPanel,
    MissionPanel,
    ReplayMetadata,
    ScoreSets,
    SideScore,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)


def main() -> None:
    scenario = load_scenario_id("MD-REC-001")
    target = Path("samples/example.replay.jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    metadata = ReplayMetadata(
        match_id="example-four-domain",
        scenario_id=scenario.scenario_id,
        seed=7,
        tick_seconds=1.0,
        coordinate_system="local_enu",
        engine_version="0.1.0",
        config_hash=configuration_hash(scenario.model_dump(mode="json")),
    )
    definitions = (
        ("blue-uav", Side.BLUE, "uav", Domain.AIR, "uav_generic", (40_000.0, 80_000.0, 500.0)),
        ("blue-usv", Side.BLUE, "usv", Domain.SURFACE, "usv_generic", (60_000.0, 60_000.0, 0.0)),
        (
            "red-radar",
            Side.RED,
            "shore_radar",
            Domain.SHORE,
            "shore_radar_generic",
            (150_000.0, 150_000.0, 0.0),
        ),
        (
            "red-auv",
            Side.RED,
            "auv",
            Domain.UNDERWATER,
            "auv_generic",
            (130_000.0, 70_000.0, -80.0),
        ),
        (
            "neutral-ship",
            Side.NEUTRAL,
            "civilian",
            Domain.SURFACE,
            "civilian_vessel",
            (100_000.0, 100_000.0, 0.0),
        ),
    )
    entities = tuple(
        VisualizationEntity(
            id=entity_id,
            side=side,
            type=entity_type,
            domain=domain,
            position=position,
            velocity=(0.0, 0.0, 0.0),
            heading=float(index * 45),
            health=1.0,
            energy=0.9,
            sensor_mode="search",
            comm_status="connected",
            status=Lifecycle.ACTIVE,
            visual_profile=profile,
        )
        for index, (entity_id, side, entity_type, domain, profile, position) in enumerate(
            definitions
        )
    )
    frame = VisualizationFrame(
        timestamp=0,
        entities=entities,
        detections=DetectionSets(),
        events=(VisualizationEvent(event_type="mission_started", message="Patrol started"),),
        scores=ScoreSets(blue=SideScore(total=0.0), red=SideScore(total=0.0)),
        environment=EnvironmentPanel(weather="clear", sea_state=2, visibility_km=20.0),
        mission=MissionPanel(status="running", objective="four-domain patrol", time_remaining=1200),
    )
    with ReplayWriter(target, metadata) as writer:
        writer.write_frame(frame)


if __name__ == "__main__":
    main()
