"""Simulation-free retained Matplotlib renderer for rich V2 frames."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.visualization.lifecycle_v2 import is_displayable_lifecycle_v2
from openmdbench.visualization.profiles import display_dimensions, transform_profile


@dataclass(frozen=True, slots=True)
class LivePresentationStatusV2:
    """Configured pacing and display metadata, separate from authority frames."""

    target_speed: float
    rendered_fps: float
    render_fps_cap: float
    skipped_ticks: int


def interpolate_frame_v2(
    previous: VisualizationFrameV2, current: VisualizationFrameV2, fraction: float
) -> VisualizationFrameV2:
    """Build a presentation-only sub-frame while preserving authoritative records."""

    if not 0.0 < fraction <= 1.0:
        raise ValueError("interpolation fraction must be in (0, 1]")
    if fraction == 1.0 or previous.scenario_id != current.scenario_id:
        return current
    prior = {str(item["entity_id"]): item for item in previous.entities}
    entities: list[dict[str, Any]] = []
    positions: dict[str, tuple[float, float, float]] = {}
    for source in current.entities:
        entity = dict(source)
        entity_id = str(entity["entity_id"])
        before = prior.get(entity_id)
        if before is not None:
            start = tuple(float(value) for value in before["position_m"])
            end = tuple(float(value) for value in entity["position_m"])
            entity["position_m"] = (
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
                start[2] + (end[2] - start[2]) * fraction,
            )
        position = entity["position_m"]
        positions[entity_id] = (
            float(position[0]),
            float(position[1]),
            float(position[2]),
        )
        entities.append(entity)

    def relocate(items: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        relocated: list[dict[str, Any]] = []
        for source in items:
            item = dict(source)
            entity_id = str(item.get("entity_id", ""))
            if entity_id in positions:
                item["center_m"] = positions[entity_id][:2]
            relocated.append(item)
        return tuple(relocated)

    return current.model_copy(
        update={
            "entities": tuple(entities),
            "sensor_coverage": relocate(current.sensor_coverage),
            "weapon_coverage": relocate(current.weapon_coverage),
            "sim_time_s": previous.sim_time_s
            + (current.sim_time_s - previous.sim_time_s) * fraction,
            "events": (),
        }
    )


class MatplotlibRendererV2:
    """Render immutable frames only; no Session, World, Catalog, or RNG imports."""

    def __init__(self, figure: Any, axes: Any, *, trajectory_points: int = 500) -> None:
        if trajectory_points < 1:
            raise ValueError("trajectory_points must be positive")
        self.figure = figure
        self.axes = axes
        self.trajectory_points = trajectory_points
        self._configured_hash: str | None = None
        self._trajectories: dict[str, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=trajectory_points)
        )
        self._trajectory_artists: dict[str, Any] = {}
        self._entity_artists: dict[str, Any] = {}
        self._labels: dict[str, Any] = {}
        self._status_badges: dict[str, dict[str, Any]] = {}
        self._overlays: list[Any] = []
        self._background: Any | None = None
        self._event_text = axes.text(1.01, 0.98, "", transform=axes.transAxes, va="top")
        self._mission_text = axes.text(1.01, 0.50, "", transform=axes.transAxes, va="top")

    @staticmethod
    def _presentation_hash(frame: VisualizationFrameV2) -> str:
        payload = {
            "map": frame.map_identity,
            "bounds": frame.world_bounds_m,
            "polygons": frame.static_polygons,
            "lines": frame.static_lines,
            "zones": frame.zones,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _configure(self, frame: VisualizationFrameV2) -> None:
        from matplotlib.collections import LineCollection, PolyCollection
        from matplotlib.patches import Polygon

        identity = self._presentation_hash(frame)
        if identity == self._configured_hash:
            return
        self.axes.clear()
        self._configured_hash = identity
        self._trajectories.clear()
        self._trajectory_artists.clear()
        self._entity_artists.clear()
        self._labels.clear()
        self._status_badges.clear()
        self._overlays.clear()
        self._background = None
        self._event_text = self.axes.text(
            1.01, 0.98, "", transform=self.axes.transAxes, va="top", fontsize=8
        )
        self._mission_text = self.axes.text(
            1.01, 0.50, "", transform=self.axes.transAxes, va="top", fontsize=9
        )
        self.axes.add_collection(
            PolyCollection(frame.static_polygons, facecolors="#DDD7C7", edgecolors="#756F63")
        )
        self.axes.add_collection(
            LineCollection(frame.static_lines, colors="#6F777D", linewidths=0.55, alpha=0.8)
        )
        for zone in frame.zones:
            points = zone.get("coordinates_m", ())
            if zone.get("geometry_type") == "polygon" and len(points) >= 3:
                color = "#7B3294" if "objective" in zone.get("tags", ()) else "#008837"
                patch = Polygon(points, closed=True, fill=False, edgecolor=color, linestyle="--")
                self.axes.add_patch(patch)
                center_x = sum(item[0] for item in points) / len(points)
                center_y = sum(item[1] for item in points) / len(points)
                self.axes.text(center_x, center_y, str(zone.get("id")), fontsize=8, color=color)
        if frame.world_bounds_m is not None:
            self.axes.set_xlim(frame.world_bounds_m[0], frame.world_bounds_m[2])
            self.axes.set_ylim(frame.world_bounds_m[1], frame.world_bounds_m[3])
        self.axes.set_aspect("equal", adjustable="box")
        self.axes.set_xlabel("Local East / m")
        self.axes.set_ylabel("Local North / m")
        self.axes.grid(alpha=0.18)

    def _meters_per_pixel(self) -> float:
        width = max(float(self.axes.bbox.width), 1.0)
        x_min, x_max = self.axes.get_xlim()
        return max(abs(float(x_max) - float(x_min)) / width, 1e-9)

    def update(
        self,
        frame: VisualizationFrameV2,
        *,
        presentation_status: LivePresentationStatusV2 | None = None,
    ) -> None:
        from matplotlib.patches import Circle

        self._configure(frame)
        for overlay in self._overlays:
            overlay.remove()
        self._overlays.clear()
        displayed_entities = tuple(
            item
            for item in frame.entities
            if is_displayable_lifecycle_v2(item.get("lifecycle_state"))
        )
        factions = sorted({str(item.get("faction_id")) for item in displayed_entities})
        palette = {
            faction: color
            for faction, color in zip(
                factions, ("#D73027", "#2878B5", "#009E73", "#CC79A7"), strict=False
            )
        }
        active_ids: set[str] = set()
        for entity in displayed_entities:
            entity_id = str(entity["entity_id"])
            active_ids.add(entity_id)
            x, y = entity["position_m"][:2]
            color = palette[str(entity.get("faction_id"))]
            self._trajectories[entity_id].append((float(x), float(y)))
            trajectory = self._trajectory_artists.get(entity_id)
            if trajectory is None:
                (trajectory,) = self.axes.plot([], [], color=color, linewidth=1.0, alpha=0.55)
                self._trajectory_artists[entity_id] = trajectory
            trajectory.set_visible(True)
            points = tuple(self._trajectories[entity_id])
            trajectory.set_data([item[0] for item in points], [item[1] for item in points])
            length, width = display_dimensions(
                float(entity.get("visual_length_m", 10.0)),
                float(entity.get("visual_width_m", 10.0)),
                meters_per_pixel=self._meters_per_pixel(),
                minimum_pixels=3.5,
            )
            path = transform_profile(
                str(entity.get("visual_profile", "uav_generic")),
                position=(float(x), float(y)),
                heading_deg=float(entity.get("heading_deg", 0.0)),
                length_m=length,
                width_m=width,
            )
            entity_artist = self._entity_artists.get(entity_id)
            if entity_artist is None:
                from matplotlib.patches import PathPatch

                entity_artist = PathPatch(
                    path, facecolor=color, edgecolor="#222222", linewidth=0.8, zorder=4
                )
                self.axes.add_patch(entity_artist)
                self._entity_artists[entity_id] = entity_artist
            else:
                entity_artist.set_path(path)
                entity_artist.set_facecolor(color)
                entity_artist.set_visible(True)
            self._update_status_badge(entity, position=(float(x), float(y)), color=color)
        for entity_id, artist in self._trajectory_artists.items():
            if entity_id not in active_ids:
                artist.set_visible(False)
                if entity_id in self._entity_artists:
                    self._entity_artists[entity_id].set_visible(False)
                if entity_id in self._labels:
                    self._labels[entity_id].set_visible(False)
                if entity_id in self._status_badges:
                    self._status_badges[entity_id]["annotation"].set_visible(False)
        self._update_relationship_overlays(frame)
        for coverage, color, linestyle in (
            (frame.sensor_coverage, "#56B4E9", ":"),
            (frame.weapon_coverage, "#E69F00", "--"),
        ):
            for item in coverage:
                radius = float(item.get("radius_m", item.get("max_range_m", 0.0)))
                if radius <= 0.0:
                    continue
                circle = Circle(
                    tuple(item["center_m"]),
                    radius,
                    fill=False,
                    edgecolor=color,
                    linestyle=linestyle,
                    alpha=0.25,
                )
                self.axes.add_patch(circle)
                self._overlays.append(circle)
        terminal = frame.mission.get("terminal_result")
        title = (
            f"{frame.scenario_id} · {frame.view} · tick {frame.tick} · t={frame.sim_time_s:.1f}s"
        )
        if presentation_status is not None:
            title += (
                f" · simulation {presentation_status.target_speed:g}x"
                f" · display {presentation_status.rendered_fps:.1f}/"
                f"{presentation_status.render_fps_cap:g} FPS"
                f" · skipped ticks {presentation_status.skipped_ticks}"
            )
        self.axes.set_title(title)
        score = frame.scores_by_faction.get("scenario", {})
        environment = frame.environment.get("declared", {})
        waves = frame.mission.get("waves", ())
        wave_text = "\n".join(
            f"{item['wave_id']}: {item['active']}/{item['planned']} active" for item in waves
        )
        faction_text = "\n".join(
            f"{faction}: {'BLUE' if color == '#2878B5' else 'RED' if color == '#D73027' else color}"
            for faction, color in palette.items()
        )
        self._mission_text.set_text(
            "MISSION\n"
            f"states: {', '.join(frame.mission.get('states', ())) or '-'}\n"
            f"remaining: {frame.mission.get('remaining_ticks', '-')} ticks\n"
            f"terminal: {terminal or '-'}\n"
            f"next wave: {frame.mission.get('next_wave', '-')}\n{wave_text}\n\n"
            "SCORE\n"
            + "\n".join(f"{key}: {value}" for key, value in sorted(score.items()))
            + "\n\nENVIRONMENT\n"
            + "\n".join(f"{key}: {value}" for key, value in sorted(environment.items()))
            + "\n\nLEGEND\n"
            + faction_text
            + "\n"
            + "E endurance · C communications\n"
            + "S sensor · H health\n"
            + "TRACK authoritative contact"
        )
        self._event_text.set_text(
            "EVENTS\n"
            + "\n".join(
                str(item.get("event_type", item.get("event_id", "event")))
                for item in frame.events[-12:]
            )
        )
        dynamic_artists: list[Any] = [
            *self._trajectory_artists.values(),
            *self._entity_artists.values(),
            *self._labels.values(),
            *(badge["annotation"] for badge in self._status_badges.values()),
            *self._overlays,
            self._event_text,
            self._mission_text,
            self.axes.title,
        ]
        canvas = self.figure.canvas
        supports_blit = bool(getattr(canvas, "supports_blit", False)) and all(
            hasattr(canvas, name) for name in ("copy_from_bbox", "restore_region", "blit")
        )
        if not supports_blit:
            for artist in dynamic_artists:
                artist.set_animated(False)
            canvas.draw()
            return
        for artist in dynamic_artists:
            artist.set_animated(True)
        if self._background is None:
            canvas.draw()
            self._background = canvas.copy_from_bbox(self.figure.bbox)
        canvas.restore_region(self._background)
        for artist in dynamic_artists:
            if artist.get_visible():
                self.figure.draw_artist(artist)
        canvas.blit(self.figure.bbox)

    @staticmethod
    def _entity_label(entity: dict[str, Any]) -> str:
        return f"{entity['entity_id']}  H{round(float(entity.get('health', 0.0)) * 100):d}%"

    def _update_status_badge(
        self, entity: dict[str, Any], *, position: tuple[float, float], color: str
    ) -> None:
        entity_id = str(entity["entity_id"])
        badge = self._status_badges.get(entity_id)
        if badge is None:
            badge = self._create_status_badge(position=position, color=color)
            self._status_badges[entity_id] = badge
        annotation = badge["annotation"]
        annotation.xy = position
        annotation.set_visible(True)
        badge["name_area"].set_text(self._entity_label(entity))

        energy = entity.get("endurance_fraction")
        if isinstance(energy, (int, float)):
            fraction = min(1.0, max(0.0, float(energy)))
            badge["battery_fill"].set_width(12.0 * fraction)
            badge["battery_text"].set_text(f"{fraction:.0%}")
            badge["battery_fill"].set_facecolor(
                "#2CA02C" if fraction > 0.5 else "#E6A700" if fraction > 0.2 else "#D73027"
            )
        else:
            badge["battery_fill"].set_width(0.0)
            badge["battery_text"].set_text("?")

        communication = str(entity.get("communication_status", "unavailable"))
        quality = float(entity.get("communication_quality", 0.0))
        levels = (
            min(4, max(0, math.ceil(quality * 4.0)))
            if communication == "online"
            else 1
            if communication == "offline"
            else 0
        )
        signal_color = (
            "#1A9850"
            if communication == "online"
            else "#D73027"
            if communication == "offline"
            else "#999999"
        )
        for index, bar in enumerate(badge["signal_bars"], start=1):
            color = signal_color if index <= levels else "#D5D5D5"
            bar.set_facecolor(color)
            bar.set_edgecolor(signal_color if index <= levels else "#999999")

        sensor_status = str(entity.get("sensor_status", "unavailable"))
        sensor_online = sensor_status == "online"
        sensor_color = (
            "#1A9850" if sensor_online else "#D73027" if sensor_status == "offline" else "#999999"
        )
        badge["sensor_ring"].set_edgecolor(sensor_color)
        badge["sensor_arc"].set_color(sensor_color)
        badge["sensor_text"].set_color(sensor_color)
        badge["sensor_text"].set_text("+" if sensor_online else "−")

    def _create_status_badge(self, *, position: tuple[float, float], color: str) -> dict[str, Any]:
        from matplotlib.offsetbox import AnnotationBbox, DrawingArea, HPacker, TextArea
        from matplotlib.patches import Arc, Circle, Rectangle
        from matplotlib.text import Text

        area = DrawingArea(36.5, 8, 0, 0)
        battery_shell = Rectangle(
            (0, 1.5), 14, 5.5, facecolor="white", edgecolor="#555555", linewidth=0.45
        )
        battery_terminal = Rectangle((14, 3), 1, 2.5, facecolor="#555555", edgecolor="#555555")
        battery_fill = Rectangle((1, 2.5), 12, 3.5, facecolor="#2CA02C", edgecolor="none")
        battery_text = Text(7, 4.25, "", ha="center", va="center", fontsize=3, color="#111111")
        for artist in (battery_shell, battery_terminal, battery_fill, battery_text):
            area.add_artist(artist)

        signal_bars = []
        for index, height in enumerate((4, 7, 10, 13)):
            bar = Rectangle(
                (17.5 + index * 2, 1.5),
                1.5,
                height * 0.4,
                facecolor="#D5D5D5",
                edgecolor="#999999",
                linewidth=0.3,
            )
            signal_bars.append(bar)
            area.add_artist(bar)

        sensor_ring = Circle(
            (31, 4.25), 2.75, facecolor="white", edgecolor="#999999", linewidth=0.45
        )
        sensor_arc = Arc((31, 4.25), 4, 4, theta1=25, theta2=155, color="#777777", linewidth=0.35)
        sensor_text = Text(31, 4.25, "", ha="center", va="center", fontsize=4, fontweight="bold")
        for sensor_artist in (sensor_ring, sensor_arc, sensor_text):
            area.add_artist(sensor_artist)

        name_area = TextArea("", textprops={"fontsize": 6, "color": color})
        packed = HPacker(children=[name_area, area], align="center", pad=0, sep=3)
        annotation = AnnotationBbox(
            packed,
            position,
            xybox=(4, 4),
            xycoords="data",
            boxcoords="offset points",
            box_alignment=(0.0, 0.0),
            frameon=False,
            zorder=9,
        )
        self.axes.add_artist(annotation)
        return {
            "annotation": annotation,
            "name_area": name_area,
            "battery_fill": battery_fill,
            "battery_text": battery_text,
            "signal_bars": tuple(signal_bars),
            "sensor_ring": sensor_ring,
            "sensor_arc": sensor_arc,
            "sensor_text": sensor_text,
        }

    def _update_relationship_overlays(self, frame: VisualizationFrameV2) -> None:
        for link in frame.communication_links:
            start = link.get("start_m")
            end = link.get("end_m")
            if not isinstance(start, (list, tuple)) or not isinstance(end, (list, tuple)):
                continue
            status = str(link.get("status", "queued"))
            color = "#1A9850" if status in {"delivered", "applied"} else "#00A6D6"
            (artist,) = self.axes.plot(
                (start[0], end[0]),
                (start[1], end[1]),
                color=color,
                linestyle=":",
                linewidth=1.2,
                alpha=0.65,
                zorder=3,
            )
            self._overlays.append(artist)
        best_targeting: dict[str, dict[str, Any]] = {}
        for link in frame.targeting_links:
            target_id = str(link.get("target_entity_id", ""))
            current = best_targeting.get(target_id)
            if current is None or float(link.get("confidence", 0.0)) > float(
                current.get("confidence", 0.0)
            ):
                best_targeting[target_id] = link
        for link in best_targeting.values():
            start = link.get("start_m")
            end = link.get("end_m")
            if not isinstance(start, (list, tuple)) or not isinstance(end, (list, tuple)):
                continue
            confidence = float(link.get("confidence", 0.0))
            (track,) = self.axes.plot(
                (start[0], end[0]),
                (start[1], end[1]),
                color="#D55E00" if link.get("fresh") else "#777777",
                linestyle="--",
                linewidth=0.7 + confidence,
                alpha=min(0.75, 0.15 + confidence * 0.45),
                zorder=2.8,
            )
            self._overlays.append(track)
            label = self.axes.annotate(
                f"TRACK {float(link.get('confidence', 0.0)):.0%}",
                (
                    (float(start[0]) + float(end[0])) / 2.0,
                    (float(start[1]) + float(end[1])) / 2.0,
                ),
                fontsize=6,
                color="#D55E00",
                alpha=0.8,
                zorder=6,
            )
            self._overlays.append(label)
        for event in frame.events:
            if event.get("event_type") != "weapon_fired":
                continue
            start = event.get("start_m")
            end = event.get("end_m")
            if not isinstance(start, (list, tuple)) or not isinstance(end, (list, tuple)):
                continue
            hit = bool(event.get("hit"))
            color = "#D73027" if hit else "#555555"
            (shot,) = self.axes.plot(
                (start[0], end[0]),
                (start[1], end[1]),
                color=color,
                linestyle="-" if hit else "--",
                linewidth=2.2,
                alpha=0.9,
                zorder=7,
            )
            (impact,) = self.axes.plot(
                (end[0],),
                (end[1],),
                marker="*" if hit else "x",
                markersize=14 if hit else 9,
                color=color,
                linestyle="none",
                zorder=8,
            )
            self._overlays.extend((shot, impact))

    def close(self) -> None:
        self._trajectories.clear()
        self._trajectory_artists.clear()
        self._entity_artists.clear()
        self._labels.clear()
        self._status_badges.clear()
        self._overlays.clear()
        self._background = None


__all__ = ["LivePresentationStatusV2", "MatplotlibRendererV2", "interpolate_frame_v2"]
