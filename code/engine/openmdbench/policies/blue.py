"""Blue cooperative interception baseline using only public contacts."""

from __future__ import annotations

import math

from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.schemas.observation import DetectedContact, FriendlyAsset, Observation


class BlueInterceptionAgent:
    def __init__(
        self,
        protected_point: tuple[float, float, float],
        *,
        patrol_offset_m: float = 3_000.0,
        prediction_seconds: float = 5.0,
        contact_max_age_ticks: int = 10,
        max_altitude_m: float = 3_000.0,
        intercept_standoff_m: float = 1_000.0,
    ) -> None:
        self.protected_point = protected_point
        self.patrol_offset_m = patrol_offset_m
        self.prediction_seconds = prediction_seconds
        self.contact_max_age_ticks = contact_max_age_ticks
        self.max_altitude_m = max_altitude_m
        self.intercept_standoff_m = intercept_standoff_m

    def reset(self, observation: Observation, seed: int) -> None:
        del observation, seed

    def _contact_valid(self, observation: Observation, contact: DetectedContact) -> bool:
        message_tick = contact.message_sent_time
        return (
            contact.confidence >= 0.7
            and message_tick is not None
            and observation.timestamp - message_tick <= self.contact_max_age_ticks
        )

    def _uav_action(
        self,
        asset: FriendlyAsset,
        target: tuple[float, float, float],
        contact: DetectedContact,
        *,
        role: str,
    ) -> PlatformAction:
        distance = math.dist(asset.position, contact.position)
        engage = distance <= 8_000.0 and asset.weapon_count > 0
        if distance <= self.intercept_standoff_m:
            return PlatformAction(
                entity_id=asset.id,
                navigation="hold_position",
                engage_contact_id=contact.id if engage else None,
                weapon_id="uav_interceptor_missile" if engage else None,
            )
        return PlatformAction(
            entity_id=asset.id,
            navigation="move_to",
            target=target,
            speed_mps=40.0,
            engage_contact_id=contact.id if engage else None,
            weapon_id="uav_interceptor_missile" if engage else None,
        )

    def act(self, observation: Observation) -> ActionBatch:
        assets = {asset.id: asset for asset in observation.situational_data.friendly_assets}
        valid_contacts = sorted(
            (
                contact
                for contact in observation.situational_data.detected_contacts
                if self._contact_valid(observation, contact)
            ),
            key=lambda contact: (-contact.confidence, contact.id),
        )
        actions: list[PlatformAction] = []
        radar = assets.get("blue-radar-1")
        if radar is not None:
            actions.append(PlatformAction(entity_id=radar.id, navigation="active_search"))
        usv = assets.get("blue-usv-1")
        if usv is not None:
            actions.append(
                PlatformAction(
                    entity_id=usv.id,
                    navigation="guard",
                    target=self.protected_point,
                    speed_mps=4.0,
                )
            )
        uav1 = assets.get("blue-uav-1")
        uav2 = assets.get("blue-uav-2")
        roles: dict[str, str] = {}
        if not valid_contacts:
            for index, asset in enumerate(item for item in (uav1, uav2) if item is not None):
                target = (
                    self.protected_point[0] + (index * 2 - 1) * self.patrol_offset_m,
                    self.protected_point[1] + self.patrol_offset_m,
                    1_200.0,
                )
                actions.append(
                    PlatformAction(
                        entity_id=asset.id,
                        navigation="patrol",
                        target=target,
                        speed_mps=40.0,
                    )
                )
                roles[asset.id] = "patrol"
        else:
            contact = valid_contacts[0]
            predicted_values = tuple(
                contact.position[axis] + contact.velocity[axis] * self.prediction_seconds
                for axis in range(3)
            )
            predicted = (
                predicted_values[0],
                predicted_values[1],
                max(0.0, min(self.max_altitude_m, predicted_values[2])),
            )
            primary, flank = uav1, uav2
            if primary is None or primary.weapon_count == 0:
                primary, flank = uav2, uav1
            if primary is not None:
                actions.append(self._uav_action(primary, predicted, contact, role="primary"))
                roles[primary.id] = "primary_interceptor"
            if flank is not None:
                flank_target = (predicted[0], predicted[1] + 2_000.0, predicted[2])
                actions.append(self._uav_action(flank, flank_target, contact, role="flank"))
                roles[flank.id] = "flank_interceptor"
            if radar is not None and math.dist(radar.position, contact.position) <= 2_000.0:
                actions.append(
                    PlatformAction(
                        entity_id=radar.id,
                        navigation="active_search",
                        engage_contact_id=contact.id,
                        weapon_id="shore_ciws",
                    )
                )
        return ActionBatch(
            timestamp=observation.timestamp,
            actions=tuple(
                sorted(actions, key=lambda action: (action.entity_id, action.navigation))
            ),
            high_level_intent={
                "roles": roles,
                "contact_id": valid_contacts[0].id if valid_contacts else None,
                "confidence": valid_contacts[0].confidence if valid_contacts else 0.0,
            },
        )
