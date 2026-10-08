from pathlib import Path

import matplotlib
import pytest
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.visualization import VisualizationEvent, export_png, frame_from_world
from openmdbench.visualization.live_match import run_live_md_ad_002

matplotlib.use("Agg")


def test_easy_referee_frame_renders_weihai_and_denial_zone_with_agg(
    tmp_path: Path,
) -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=0)
    env.reset(seed=0)
    assert env.world is not None and env.geo_frame is not None
    protected = (float(env._protected_point[0]), float(env._protected_point[1]))
    frame = frame_from_world(
        env.world,
        view="referee",
        geo_frame=env.geo_frame,
        events=(
            VisualizationEvent(
                event_type="protection_zone",
                data={"center": protected, "radius_m": 8_000.0},
            ),
        ),
    )
    assert {entity.visual_profile for entity in frame.entities} >= {
        "uav_generic",
        "usv_generic",
        "shore_radar_generic",
    }
    layers = env.geo_frame.visualization_layers
    output = export_png(
        frame,
        tmp_path / "easy.png",
        world_bounds=layers.bounds(),
        static_polygons=layers.land_polygons,
        static_lines=layers.coastline_lines,
    )
    assert output.stat().st_size > 10_000


def test_medium_weather_frame_renders_with_same_dto(tmp_path: Path) -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=1)
    env.reset(seed=1)
    assert env.world is not None and env.geo_frame is not None
    env._apply_ad2_difficulty_events(600)
    frame = frame_from_world(env.world, view="referee", geo_frame=env.geo_frame)
    assert frame.environment.weather == "cloudy"
    layers = env.geo_frame.visualization_layers
    output = export_png(
        frame,
        tmp_path / "medium.png",
        world_bounds=layers.bounds(),
        static_polygons=layers.land_polygons,
        static_lines=layers.coastline_lines,
    )
    assert output.stat().st_size > 10_000


def test_hard_relay_status_reaches_visualization_dto() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=2)
    env.reset(seed=2)
    assert env.world is not None and env.geo_frame is not None
    env._apply_ad2_difficulty_events(900)
    env._route_ad2_tracks((), 900)
    frame = frame_from_world(env.world, view="referee", geo_frame=env.geo_frame)
    uav = next(entity for entity in frame.entities if entity.id == "red-interceptor-uav-1")
    assert uav.comm_status == "relayed"
    assert frame.environment.weather in {"light_rain", "fog"}
    assert frame.environment.sea_state == 4


@pytest.mark.parametrize(
    "scenario_id",
    ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"),
)
def test_each_md_ad_002_scenario_runs_through_shared_live_renderer(
    scenario_id: str,
) -> None:
    result = run_live_md_ad_002(
        scenario_id=scenario_id,  # type: ignore[arg-type]
        seed=3,
        speed=1_000_000.0,
        max_ticks=2,
        block_on_finish=False,
    )
    assert result.ticks == 2
    assert result.outcome == "in_progress"
