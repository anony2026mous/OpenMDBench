"""View switching, detail, event, weather, mission, and score panels."""

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from openmdbench.core.entities import Domain, Lifecycle, Side
from openmdbench.visualization import MatplotlibRenderer, VisualizationDashboard
from openmdbench.visualization.dashboard import frame_for_view
from openmdbench.visualization.schema import (
    DetectionSets,
    EnvironmentPanel,
    MissionPanel,
    ScoreSets,
    SideScore,
    VisualizationDetection,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)


def _entity(entity_id: str, side: Side) -> VisualizationEntity:
    return VisualizationEntity(
        id=entity_id,
        side=side,
        type="usv",
        domain=Domain.SURFACE,
        position=(0.0, 0.0, 0.0),
        velocity=(0.0, 0.0, 0.0),
        heading=0.0,
        health=1.0,
        energy=1.0,
        sensor_mode="search",
        comm_status="connected",
        status=Lifecycle.ACTIVE,
        visual_profile="usv_generic",
    )


def _authority_frame() -> VisualizationFrame:
    contact = VisualizationDetection(
        id="red-contact",
        estimated_domain=Domain.SURFACE,
        position=(5.0, 5.0, 0.0),
        position_uncertainty=10.0,
        confidence=0.8,
    )
    return VisualizationFrame(
        timestamp=4,
        entities=(
            _entity("blue", Side.BLUE),
            _entity("red", Side.RED),
            _entity("neutral", Side.NEUTRAL),
        ),
        detections=DetectionSets(blue=(contact,)),
        events=(VisualizationEvent(event_type="weather_change", message="storm"),),
        scores=ScoreSets(blue=SideScore(total=0.37), red=SideScore(total=0.61)),
        environment=EnvironmentPanel(weather="storm", sea_state=5),
        mission=MissionPanel(status="running", objective="track target", time_remaining=80),
    )


def test_view_switch_hides_truth_and_entity_detail() -> None:
    figure, axes = plt.subplots()
    dashboard = VisualizationDashboard(MatplotlibRenderer(axes), view="referee")
    dashboard.update(_authority_frame())
    assert dashboard.entity_detail("red") is not None
    dashboard.set_view("blue")
    assert dashboard.entity_detail("red") is None
    assert dashboard.entity_detail("blue") is not None
    assert not dashboard.renderer.entity_artists["red"].get_visible()
    dashboard.set_view("public")
    assert dashboard.entity_detail("blue") is None
    assert dashboard.entity_detail("neutral") is not None
    plt.close(figure)


def test_panels_use_authoritative_frame_values() -> None:
    figure, axes = plt.subplots()
    dashboard = VisualizationDashboard(MatplotlibRenderer(axes), view="blue")
    frame = _authority_frame()
    dashboard.update(frame)
    assert dashboard.events == [(4, frame.events[0])]
    assert dashboard.scores[0].blue == 0.37
    assert dashboard.scores[0].red == 0.61
    assert "storm" in dashboard.renderer.task_text.get_text()
    assert "track target" in dashboard.renderer.task_text.get_text()
    plt.close(figure)


def test_view_specific_effects_do_not_leak_authority_or_red_routes() -> None:
    frame = _authority_frame().model_copy(
        update={
            "events": (
                VisualizationEvent(
                    event_type="weapon_fired",
                    data={"visible_to": ("referee",), "end": (1.0, 2.0, 3.0)},
                ),
                VisualizationEvent(
                    event_type="communication_route",
                    data={"visible_to": ("referee", "red"), "route": ("a", "b")},
                ),
            )
        }
    )
    assert len(frame_for_view(frame, "referee").events) == 2
    assert [event.event_type for event in frame_for_view(frame, "red").events] == [
        "communication_route"
    ]
    assert frame_for_view(frame, "blue").events == ()
    assert frame_for_view(frame, "public").events == ()
