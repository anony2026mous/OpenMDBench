"""Retained Artist lifecycle and headless renderer tests."""

import subprocess
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pytest
from matplotlib.patches import Patch

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from openmdbench.core.entities import Domain, Lifecycle, Side
from openmdbench.visualization import MatplotlibRenderer
from openmdbench.visualization.schema import (
    DetectionSets,
    ScoreSets,
    SideScore,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)


def _entity(index: int, *, x_offset: float = 0.0) -> VisualizationEntity:
    return VisualizationEntity(
        id=f"usv-{index}",
        side=Side.BLUE,
        type="usv",
        domain=Domain.SURFACE,
        position=(float(index) + x_offset, float(index % 10), 0.0),
        velocity=(1.0, 0.0, 0.0),
        heading=90.0,
        health=1.0,
        energy=0.8,
        sensor_mode="search",
        comm_status="connected",
        status=Lifecycle.ACTIVE,
        visual_profile="usv_generic",
    )


def _frame(count: int, *, x_offset: float = 0.0) -> VisualizationFrame:
    return VisualizationFrame(
        timestamp=int(x_offset),
        entities=tuple(_entity(index, x_offset=x_offset) for index in range(count)),
        detections=DetectionSets(),
        scores=ScoreSets(blue=SideScore(total=0.6), red=SideScore(total=0.4)),
    )


def test_static_map_and_entity_artists_are_reused_headlessly(tmp_path: Path) -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(0.0, 100.0)
    renderer = MatplotlibRenderer(axes, static_polygons=(((0.0, 0.0), (1.0, 0.0)),))
    renderer.update(_frame(2))
    identities = {key: id(value) for key, value in renderer.entity_artists.items()}
    static_identity = id(renderer.static_map)
    renderer.update(_frame(2, x_offset=1.0))
    assert {key: id(value) for key, value in renderer.entity_artists.items()} == identities
    assert id(renderer.static_map) == static_identity
    output = tmp_path / "renderer.png"
    figure.savefig(output)
    plt.close(figure)
    assert output.stat().st_size > 0


def test_open_coastline_is_not_implicitly_closed_or_filled() -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(0.0, 10.0)
    axes.set_ylim(0.0, 10.0)
    coastline = ((1.0, 1.0), (5.0, 4.0), (9.0, 2.0))
    renderer = MatplotlibRenderer(axes, static_lines=(coastline,))

    segments = renderer.static_coastline.get_segments()
    assert len(segments) == 1
    assert segments[0].tolist() == [list(point) for point in coastline]
    assert len(renderer.static_map.get_paths()) == 0
    plt.close(figure)


def test_entity_label_energy_signal_and_dashed_sensor_range_update() -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(-100.0, 100.0)
    axes.set_ylim(-100.0, 100.0)
    renderer = MatplotlibRenderer(axes)
    frame = _frame(1).model_copy(
        update={
            "events": (
                VisualizationEvent(
                    event_type="sensor_range",
                    entity_id="usv-0",
                    data={"center": (0.0, 0.0), "radius_m": 50.0, "side": "blue"},
                ),
            )
        }
    )
    renderer.update(frame)
    label_identity = id(renderer.label_artists["usv-0"])
    energy_identity = tuple(id(item) for item in renderer.energy_artists["usv-0"])
    assert renderer.label_artists["usv-0"].get_text() == "usv-0  E80 H100"
    overlay = renderer.overlay_artists[0]
    assert isinstance(overlay, Patch)
    assert overlay.get_linestyle() == "--"

    low_energy = frame.entities[0].model_copy(update={"energy": 0.2})
    renderer.update(frame.model_copy(update={"entities": (low_energy,)}))
    assert id(renderer.label_artists["usv-0"]) == label_identity
    assert tuple(id(item) for item in renderer.energy_artists["usv-0"]) == energy_identity
    assert renderer.label_artists["usv-0"].get_text() == "usv-0  E20 H100"
    background, foreground = renderer.energy_artists["usv-0"]
    assert np.asarray(background.get_path().vertices).shape == (20, 2)
    assert np.asarray(foreground.get_path().vertices).shape == (5, 2)
    plt.close(figure)


def test_combat_communication_and_terminal_state_are_visually_explicit() -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(-10.0, 110.0)
    axes.set_ylim(-10.0, 110.0)
    renderer = MatplotlibRenderer(axes)
    renderer.update(_frame(1))
    destroyed = _entity(0).model_copy(update={"health": 0.0, "status": Lifecycle.DESTROYED})
    frame = _frame(1).model_copy(
        update={
            "entities": (destroyed,),
            "events": (
                VisualizationEvent(
                    event_type="weapon_fired",
                    data={"start": (0.0, 0.0, 0.0), "end": (100.0, 100.0, 0.0), "hit": True},
                ),
                VisualizationEvent(
                    event_type="communication_route",
                    data={
                        "points": ((0.0, 0.0, 0.0), (50.0, 20.0, 0.0), (100.0, 0.0, 0.0)),
                        "status": "delivered",
                    },
                ),
                VisualizationEvent(
                    event_type="entity_killed",
                    message="red-uav [missile] destroyed usv-0",
                    data={
                        "attacker_id": "red-uav",
                        "weapon_id": "missile",
                        "target_id": "usv-0",
                        "tick": 0,
                    },
                ),
                VisualizationEvent(
                    event_type="collision_impact",
                    data={"position": (25.0, 25.0, 100.0)},
                ),
            ),
        }
    )
    renderer.update(frame)
    assert not renderer.entity_artists["usv-0"].get_visible()
    assert not renderer.trajectory_artists["usv-0"].get_visible()
    assert "red-uav [missile] destroyed usv-0" in renderer.kill_text.get_text()
    assert len(renderer._transient_effects) == 3
    combat_artists = renderer._transient_effects[0][1]
    communication_artists = renderer._transient_effects[1][1]
    assert combat_artists[0].get_color() == "#D73027"
    assert combat_artists[1].get_marker() == "*"
    assert communication_artists[0].get_color() == "#1A9850"
    assert renderer._transient_effects[2][1][0].get_marker() == "X"
    renderer.update(frame.model_copy(update={"timestamp": 20, "events": ()}))
    assert renderer._transient_effects == []
    plt.close(figure)


def test_wave_identity_spawn_countdown_and_maneuver_are_explicit() -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(-10.0, 110.0)
    axes.set_ylim(-10.0, 110.0)
    renderer = MatplotlibRenderer(axes)
    frame = _frame(1).model_copy(
        update={
            "events": (
                VisualizationEvent(
                    event_type="wave_status",
                    data={
                        "entity_waves": {"usv-0": "wave-2"},
                        "waves": (
                            {
                                "wave_id": "wave-2",
                                "planned": 5,
                                "spawned": 1,
                                "active": 1,
                                "destroyed": 0,
                                "breached": 0,
                            },
                        ),
                        "next_wave": {"wave_id": "wave-3", "ticks_remaining": 600},
                    },
                ),
                VisualizationEvent(
                    event_type="wave_spawn",
                    data={"position": (0.0, 0.0, 0.0), "wave_id": "wave-2"},
                ),
                VisualizationEvent(
                    event_type="maneuver_vector",
                    entity_id="usv-0",
                    data={"start": (0.0, 0.0, 0.0), "end": (50.0, 20.0, 0.0)},
                ),
            )
        }
    )
    renderer.update(frame)
    assert "WAVE-2: 1/5 spawned" in renderer.wave_text.get_text()
    assert "NEXT WAVE-3 IN 600 ticks" in renderer.wave_text.get_text()
    assert "WAVE-2" in renderer.label_artists["usv-0"].get_text()
    assert renderer.entity_artists["usv-0"].get_facecolor()[:3] == pytest.approx(
        matplotlib.colors.to_rgb("#009E73")
    )
    assert len(renderer._transient_effects) == 1
    assert renderer._transient_effects[0][1][0].get_markersize() == 24
    assert renderer.maneuver_artists["usv-0"].get_visible()
    maneuver_identity = id(renderer.maneuver_artists["usv-0"])
    renderer.update(frame.model_copy(update={"timestamp": 1}))
    assert id(renderer.maneuver_artists["usv-0"]) == maneuver_identity
    plt.close(figure)


def test_air_entity_label_shows_altitude_and_vertical_trend() -> None:
    figure, axes = plt.subplots()
    renderer = MatplotlibRenderer(axes)
    climbing = _entity(0).model_copy(
        update={
            "domain": Domain.AIR,
            "position": (0.0, 0.0, 120.0),
            "velocity": (1.0, 0.0, 20.0),
            "visual_profile": "uav_generic",
        }
    )
    renderer.update(_frame(1).model_copy(update={"entities": (climbing,)}))
    assert "A120m^" in renderer.label_artists["usv-0"].get_text()

    descending = climbing.model_copy(update={"velocity": (1.0, 0.0, -20.0)})
    renderer.update(_frame(1, x_offset=1.0).model_copy(update={"entities": (descending,)}))
    assert "A120mv" in renderer.label_artists["usv-0"].get_text()
    plt.close(figure)


def test_one_thousand_entities_update_without_artist_rebuild() -> None:
    figure, axes = plt.subplots()
    axes.set_xlim(0.0, 1_100.0)
    renderer = MatplotlibRenderer(axes)
    renderer.update(_frame(1_000))
    identities = tuple(id(renderer.entity_artists[f"usv-{index}"]) for index in range(1_000))
    renderer.update(_frame(1_000, x_offset=1.0))
    updated = tuple(id(renderer.entity_artists[f"usv-{index}"]) for index in range(1_000))
    assert updated == identities
    assert len(renderer.entity_artists) == len(renderer.trajectory_artists) == 1_000
    plt.close(figure)


def test_dynamic_entity_churn_is_bounded_and_close_releases_owned_artists() -> None:
    figure, axes = plt.subplots()
    renderer = MatplotlibRenderer(axes, max_retained_entities=8)
    for index in range(40):
        entity = _entity(index).model_copy(update={"id": f"dynamic-{index}"})
        renderer.update(_frame(0, x_offset=float(index)).model_copy(update={"entities": (entity,)}))
        assert len(renderer.entity_artists) <= 8
    renderer.close()
    assert not renderer.entity_artists
    assert not renderer.trajectory_artists
    assert not renderer.label_artists
    assert not renderer.energy_artists
    plt.close(figure)


def test_renderer_import_does_not_load_taichi() -> None:
    command = [
        sys.executable,
        "-c",
        "import sys; import openmdbench.visualization.renderer; assert 'taichi' not in sys.modules",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
