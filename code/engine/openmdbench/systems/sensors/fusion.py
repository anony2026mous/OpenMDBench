"""Order-independent side-scoped contact fusion."""

from __future__ import annotations

from collections import defaultdict

from openmdbench.core.entities import Side
from openmdbench.core.world import ContactTrack


def fuse_tracks(tracks: tuple[ContactTrack, ...]) -> tuple[ContactTrack, ...]:
    groups: dict[tuple[Side, str], list[ContactTrack]] = defaultdict(list)
    for track in tracks:
        groups[(track.owner_side, track.contact_id)].append(track)

    fused: list[ContactTrack] = []
    for key in sorted(groups, key=lambda item: (item[0].value, item[1])):
        measurements = groups[key]
        reference = min(
            measurements,
            key=lambda track: (
                track.first_detected_tick,
                track.detected_by,
                track.position,
            ),
        )
        weights = [1.0 / max(track.uncertainty_m**2, 1e-9) for track in measurements]
        weight_sum = sum(weights)
        position = tuple(
            sum(
                weight * track.position[axis]
                for weight, track in zip(weights, measurements, strict=True)
            )
            / weight_sum
            for axis in range(3)
        )
        velocity = tuple(
            sum(
                weight * track.velocity[axis]
                for weight, track in zip(weights, measurements, strict=True)
            )
            / weight_sum
            for axis in range(3)
        )
        confidence = min(
            1.0,
            max(track.confidence for track in measurements) + 0.1 * (len(measurements) - 1),
        )
        fused.append(
            ContactTrack(
                contact_id=key[1],
                owner_side=key[0],
                estimated_domain=reference.estimated_domain,
                position=position,  # type: ignore[arg-type]
                velocity=velocity,  # type: ignore[arg-type]
                uncertainty_m=(1.0 / weight_sum) ** 0.5,
                confidence=confidence,
                first_detected_tick=min(track.first_detected_tick for track in measurements),
                detected_by=tuple(
                    sorted({sensor for track in measurements for sensor in track.detected_by})
                ),
                inferred_type=reference.inferred_type,
                message_sent_tick=reference.message_sent_tick,
                message_source=reference.message_source,
                last_update_tick=max(
                    (
                        track.last_update_tick
                        for track in measurements
                        if track.last_update_tick is not None
                    ),
                    default=None,
                ),
            )
        )
    return tuple(fused)
