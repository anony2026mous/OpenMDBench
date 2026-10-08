"""Order independence and side isolation for sensor fusion."""

from openmdbench.core.entities import Domain, Side
from openmdbench.core.world import ContactTrack
from openmdbench.systems.sensors import fuse_tracks


def _track(side: Side, sensor: str, x: float, uncertainty: float) -> ContactTrack:
    return ContactTrack(
        contact_id="contact-1",
        owner_side=side,
        estimated_domain=Domain.SURFACE,
        position=(x, 0.0, 0.0),
        velocity=(1.0, 0.0, 0.0),
        uncertainty_m=uncertainty,
        confidence=0.7,
        first_detected_tick=1,
        detected_by=(sensor,),
    )


def test_fusion_is_input_order_independent_and_improves_track() -> None:
    radar = _track(Side.BLUE, "radar", 10.0, 20.0)
    eo = _track(Side.BLUE, "eo", 12.0, 30.0)
    forward = fuse_tracks((radar, eo))[0]
    reverse = fuse_tracks((eo, radar))[0]
    assert forward == reverse
    assert forward.uncertainty_m < radar.uncertainty_m
    assert forward.detected_by == ("eo", "radar")
    assert forward.confidence > radar.confidence


def test_same_contact_label_from_different_sides_is_not_fused() -> None:
    blue = _track(Side.BLUE, "blue-radar", 10.0, 20.0)
    red = _track(Side.RED, "red-radar", 100.0, 20.0)
    fused = fuse_tracks((red, blue))
    assert len(fused) == 2
    assert {track.owner_side for track in fused} == {Side.BLUE, Side.RED}
