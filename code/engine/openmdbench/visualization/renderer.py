"""Headless-safe Matplotlib renderer consuming only VisualizationFrame DTOs."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from collections.abc import Sequence

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PatchCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path
from matplotlib.text import Annotation

from openmdbench.visualization.profiles import (
    Theme,
    display_dimensions,
    style_for_entity,
    transform_profile,
)
from openmdbench.visualization.schema import VisualizationEntity, VisualizationFrame

_DEFAULT_DIMENSIONS = {
    "uav_generic": (12.0, 18.0),
    "usv_generic": (20.0, 6.0),
    "shore_radar_generic": (12.0, 12.0),
    "auv_generic": (8.0, 1.2),
    "civilian_vessel": (50.0, 12.0),
}

_WAVE_COLORS = {
    "wave-1": "#0072B2",
    "wave-2": "#009E73",
    "wave-3": "#CC79A7",
}

_HIDDEN_TERMINAL_STATES = {
    "crashed",
    "destroyed",
    "impacted",
    "out_of_bounds",
    "removed",
}


def _energy_signal_path(
    position: tuple[float, float], *, meters_per_pixel: float, levels: int
) -> Path:
    """Build a four-bar phone-signal shape next to an entity."""
    if levels <= 0:
        return Path(np.empty((0, 2), dtype=np.float64))
    vertices: list[tuple[float, float]] = []
    codes: list[int] = []
    bar_width = 2.0 * meters_per_pixel
    gap = 1.0 * meters_per_pixel
    base_x = position[0] - 6.0 * meters_per_pixel
    base_y = position[1] + 7.0 * meters_per_pixel
    for index in range(max(0, min(levels, 4))):
        left = base_x + index * (bar_width + gap)
        right = left + bar_width
        top = base_y + (3.0 + 2.0 * index) * meters_per_pixel
        vertices.extend(
            (
                (left, base_y),
                (right, base_y),
                (right, top),
                (left, top),
                (left, base_y),
            )
        )
        codes.extend(
            (
                int(Path.MOVETO),
                int(Path.LINETO),
                int(Path.LINETO),
                int(Path.LINETO),
                int(Path.CLOSEPOLY),
            )
        )
    return Path(vertices, codes)


class MatplotlibRenderer:
    """Retained-mode renderer: stable IDs retain their Artists across frames."""

    def __init__(
        self,
        axes: Axes,
        *,
        static_polygons: Sequence[Sequence[tuple[float, float]]] = (),
        static_lines: Sequence[Sequence[tuple[float, float]]] = (),
        theme: Theme = "standard",
        trajectory_points: int = 500,
        max_retained_entities: int = 4096,
    ) -> None:
        if trajectory_points <= 0 or max_retained_entities <= 0:
            raise ValueError("trajectory and retained-entity limits must be positive")
        self.axes = axes
        self.theme = theme
        self.trajectory_points = trajectory_points
        self.max_retained_entities = max_retained_entities
        self.entity_artists: dict[str, PathPatch] = {}
        self.trajectory_artists: dict[str, Line2D] = {}
        self.label_artists: dict[str, Annotation] = {}
        self.energy_artists: dict[str, tuple[PathPatch, PathPatch]] = {}
        self.status_artists: dict[str, Annotation] = {}
        self.maneuver_artists: dict[str, Line2D] = {}
        self._trajectories: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self._transient_effects: list[tuple[int, tuple[Line2D, ...]]] = []
        self._seen_transient_events: dict[str, int] = {}
        self._seen_kill_events: deque[str] = deque(maxlen=256)
        self.kill_feed: list[str] = []
        x_limits = axes.get_xlim()
        y_limits = axes.get_ylim()

        def valid_polygon(polygon: Sequence[tuple[float, float]]) -> bool:
            if len(polygon) < 3:
                return False
            x_values = [point[0] for point in polygon]
            y_values = [point[1] for point in polygon]
            intersects_view = not (
                max(x_values) < x_limits[0]
                or min(x_values) > x_limits[1]
                or max(y_values) < y_limits[0]
                or min(y_values) > y_limits[1]
            )
            twice_area = abs(
                sum(
                    x_values[index - 1] * y_values[index] - x_values[index] * y_values[index - 1]
                    for index in range(len(polygon))
                )
            )
            return intersects_view and twice_area > 1e-6

        def valid_line(line: Sequence[tuple[float, float]]) -> bool:
            if len(line) < 2:
                return False
            x_values = [point[0] for point in line]
            y_values = [point[1] for point in line]
            return not (
                max(x_values) < x_limits[0]
                or min(x_values) > x_limits[1]
                or max(y_values) < y_limits[0]
                or min(y_values) > y_limits[1]
            )

        valid_static_polygons = tuple(
            polygon for polygon in static_polygons if valid_polygon(polygon)
        )
        self.static_map = PolyCollection(
            valid_static_polygons,
            facecolors="none",
            edgecolors="#777777",
            label="Land / island boundary",
            zorder=0,
        )
        axes.add_collection(self.static_map)
        self.static_coastline = LineCollection(
            tuple(line for line in static_lines if valid_line(line)),
            colors="#777777",
            linewidths=1.0,
            label="Coastline",
            zorder=0.5,
        )
        axes.add_collection(self.static_coastline)
        self.contact_artists = {
            "blue": axes.scatter([], [], marker="o", facecolors="none", edgecolors="#0072B2"),
            "red": axes.scatter([], [], marker="o", facecolors="none", edgecolors="#D55E00"),
        }
        self.sensor_layer = PatchCollection([], match_original=True, zorder=1)
        self.protection_layer = PatchCollection(
            [], facecolors="none", edgecolors="#9467BD", linestyles="dashed", zorder=1
        )
        self.communication_layer = LineCollection([], colors="#666666", linestyles="dotted")
        self.overlay_artists: list[Artist] = []
        self._entity_waves: dict[str, str] = {}
        axes.add_collection(self.sensor_layer)
        axes.add_collection(self.protection_layer)
        axes.add_collection(self.communication_layer)
        self.task_text = axes.text(0.01, 0.99, "", transform=axes.transAxes, va="top")
        self.score_text = axes.text(0.99, 0.99, "", transform=axes.transAxes, ha="right", va="top")
        self.wave_text = axes.text(
            0.01,
            0.01,
            "",
            transform=axes.transAxes,
            va="bottom",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "#777777"},
        )
        self.kill_text = axes.text(
            0.99,
            0.86,
            "",
            transform=axes.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#B2182B",
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#B2182B"},
        )

    def _remove_absent_entity(self, entity_id: str) -> None:
        for mapping in (
            self.entity_artists,
            self.trajectory_artists,
            self.label_artists,
            self.status_artists,
            self.maneuver_artists,
        ):
            artist = mapping.pop(entity_id, None)
            if artist is not None:
                artist.remove()
        for artist in self.energy_artists.pop(entity_id, ()):
            artist.remove()
        self._trajectories.pop(entity_id, None)
        self._entity_waves.pop(entity_id, None)

    def close(self) -> None:
        for entity_id in tuple(self.entity_artists):
            self._remove_absent_entity(entity_id)
        for _expires, artists in self._transient_effects:
            for artist in artists:
                artist.remove()
        self._transient_effects.clear()
        self._seen_transient_events.clear()
        self._seen_kill_events.clear()
        self.kill_feed.clear()

    def _meters_per_pixel(self) -> float:
        width = max(float(self.axes.bbox.width), 1.0)
        x_min, x_max = self.axes.get_xlim()
        return max(abs(x_max - x_min) / width, 1e-9)

    def _update_entity(self, entity: VisualizationEntity) -> None:
        length, width = _DEFAULT_DIMENSIONS[entity.visual_profile]
        length, width = display_dimensions(length, width, meters_per_pixel=self._meters_per_pixel())
        path = transform_profile(
            entity.visual_profile,
            position=entity.position[:2],
            heading_deg=entity.heading,
            length_m=length,
            width_m=width,
        )
        style = style_for_entity(entity.side, entity.status, theme=self.theme)
        artist = self.entity_artists.get(entity.id)
        if artist is None:
            artist = PathPatch(path, zorder=3)
            self.entity_artists[entity.id] = artist
            self.axes.add_patch(artist)
        else:
            artist.set_path(path)
        artist.set_visible(True)
        wave_id = self._entity_waves.get(entity.id)
        entity_color = (
            _WAVE_COLORS.get(wave_id, style.facecolor) if wave_id is not None else style.facecolor
        )
        artist.set_facecolor(entity_color)
        artist.set_edgecolor(style.edgecolor)
        artist.set_alpha(style.alpha)
        artist.set_linestyle(style.linestyle)

        points = self._trajectories[entity.id]
        points.append(entity.position[:2])
        del points[: -self.trajectory_points]
        trajectory = self.trajectory_artists.get(entity.id)
        if trajectory is None:
            (trajectory,) = self.axes.plot([], [], color=entity_color, alpha=0.55, zorder=2)
            self.trajectory_artists[entity.id] = trajectory
        trajectory.set_color(entity_color)
        coordinates = np.asarray(points, dtype=np.float64)
        trajectory.set_data(coordinates[:, 0], coordinates[:, 1])
        trajectory.set_visible(True)

        label = self.label_artists.get(entity.id)
        wave_label = f" {wave_id.upper()}" if wave_id else ""
        vertical_label = ""
        if entity.domain.value == "air":
            trend = "^" if entity.velocity[2] > 0.1 else "v" if entity.velocity[2] < -0.1 else "-"
            vertical_label = f" A{round(entity.position[2]):d}m{trend}"
        label_text = (
            f"{entity.id}{wave_label}{vertical_label}  E{round(entity.energy * 100):d} "
            f"H{round(entity.health * 100):d}"
        )
        if label is None:
            label = self.axes.annotate(
                label_text,
                xy=entity.position[:2],
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=7,
                color="#222222",
                zorder=6,
            )
            self.label_artists[entity.id] = label
        else:
            label.xy = entity.position[:2]
            label.set_text(label_text)
            label.set_visible(True)

        status = self.status_artists.get(entity.id)
        status_text = {
            "degraded": "! DEGRADED",
            "offline": "X OFFLINE",
            "crashed": "X CRASHED",
            "drifting": "! DRIFTING",
            "destroyed": "X DESTROYED",
            "impacted": "X IMPACTED",
            "out_of_bounds": "X OUT OF BOUNDS",
            "removed": "X REMOVED",
        }.get(entity.status.value, "")
        if not status_text and entity.comm_status == "offline":
            status_text = "COMMS OFFLINE"
        elif not status_text and entity.comm_status == "relayed":
            status_text = "RELAY"
        if status is None:
            status = self.axes.annotate(
                status_text,
                xy=entity.position[:2],
                xytext=(8, -14),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold",
                color="#B2182B",
                zorder=8,
            )
            self.status_artists[entity.id] = status
        else:
            status.xy = entity.position[:2]
            status.set_text(status_text)
        status.set_color("#2166AC" if status_text == "RELAY" else "#B2182B")
        status.set_visible(bool(status_text))

        meters_per_pixel = self._meters_per_pixel()
        energy = self.energy_artists.get(entity.id)
        background_path = _energy_signal_path(
            entity.position[:2], meters_per_pixel=meters_per_pixel, levels=4
        )
        filled_levels = min(4, max(0, int(np.ceil(entity.energy * 4.0))))
        foreground_path = _energy_signal_path(
            entity.position[:2], meters_per_pixel=meters_per_pixel, levels=filled_levels
        )
        if energy is None:
            background = PathPatch(
                background_path,
                facecolor="#D0D0D0",
                edgecolor="#666666",
                linewidth=0.5,
                zorder=5,
            )
            foreground = PathPatch(
                foreground_path,
                facecolor="#2CA02C",
                edgecolor="#1B6E1B",
                linewidth=0.5,
                zorder=5.1,
            )
            self.axes.add_patch(background)
            self.axes.add_patch(foreground)
            self.energy_artists[entity.id] = (background, foreground)
        else:
            background, foreground = energy
            background.set_path(background_path)
            foreground.set_path(foreground_path)
            background.set_visible(True)
            foreground.set_visible(True)

    def _update_transient_effects(self, frame: VisualizationFrame) -> None:
        self._seen_transient_events = {
            key: timestamp
            for key, timestamp in self._seen_transient_events.items()
            if timestamp >= frame.timestamp - 20
        }
        retained: list[tuple[int, tuple[Line2D, ...]]] = []
        for expires_tick, artists in self._transient_effects:
            if expires_tick < frame.timestamp:
                for artist in artists:
                    artist.remove()
            else:
                retained.append((expires_tick, artists))
        self._transient_effects = retained

        for index, event in enumerate(frame.events):
            if event.event_type not in {
                "weapon_fired",
                "communication_route",
                "wave_spawn",
                "collision_impact",
            }:
                continue
            key = f"{frame.timestamp}:{index}:{event.event_type}:" + json.dumps(
                event.data, sort_keys=True, default=str
            )
            if key in self._seen_transient_events:
                continue
            self._seen_transient_events[key] = frame.timestamp
            if event.event_type == "weapon_fired":
                start = event.data.get("start")
                end = event.data.get("end")
                if not (
                    isinstance(start, (list, tuple))
                    and isinstance(end, (list, tuple))
                    and len(start) >= 2
                    and len(end) >= 2
                ):
                    continue
                hit = bool(event.data.get("hit"))
                color = "#D73027" if hit else "#666666"
                (track,) = self.axes.plot(
                    (float(start[0]), float(end[0])),
                    (float(start[1]), float(end[1])),
                    color=color,
                    linestyle="-" if hit else "--",
                    linewidth=2.0,
                    alpha=0.9,
                    zorder=7,
                )
                (impact,) = self.axes.plot(
                    (float(end[0]),),
                    (float(end[1]),),
                    marker="*" if hit else "x",
                    markersize=14 if hit else 9,
                    color=color,
                    linestyle="none",
                    zorder=8,
                )
                self._transient_effects.append((frame.timestamp + 8, (track, impact)))
            elif event.event_type == "communication_route":
                points = event.data.get("points")
                if not isinstance(points, (list, tuple)) or len(points) < 2:
                    continue
                status = str(event.data.get("status", "queued"))
                color = {
                    "queued": "#00A6D6",
                    "delivered": "#1A9850",
                    "dropped": "#D73027",
                    "expired": "#D73027",
                    "blocked": "#D73027",
                }.get(status, "#666666")
                (route,) = self.axes.plot(
                    [float(point[0]) for point in points],
                    [float(point[1]) for point in points],
                    color=color,
                    linestyle=":" if status == "queued" else "--",
                    marker="o",
                    markersize=3,
                    linewidth=1.6,
                    alpha=0.8,
                    zorder=4,
                )
                self._transient_effects.append((frame.timestamp + 4, (route,)))
            elif event.event_type == "wave_spawn":
                position = event.data.get("position")
                wave_id = str(event.data.get("wave_id", ""))
                if not isinstance(position, (list, tuple)) or len(position) < 2:
                    continue
                (spawn,) = self.axes.plot(
                    (float(position[0]),),
                    (float(position[1]),),
                    marker="o",
                    markersize=24,
                    markerfacecolor="none",
                    markeredgecolor=_WAVE_COLORS.get(wave_id, "#F0E442"),
                    markeredgewidth=3.0,
                    linestyle="none",
                    zorder=9,
                )
                self._transient_effects.append((frame.timestamp + 12, (spawn,)))
            else:
                position = event.data.get("position")
                if not isinstance(position, (list, tuple)) or len(position) < 2:
                    continue
                (impact,) = self.axes.plot(
                    (float(position[0]),),
                    (float(position[1]),),
                    marker="X",
                    markersize=20,
                    markerfacecolor="#E69F00",
                    markeredgecolor="#8C2D04",
                    markeredgewidth=2.0,
                    linestyle="none",
                    zorder=10,
                )
                self._transient_effects.append((frame.timestamp + 12, (impact,)))

    def update(self, frame: VisualizationFrame) -> None:
        """Update retained Artists without clearing axes or rebuilding the static map."""
        for event in frame.events:
            if event.event_type != "entity_killed":
                continue
            key = json.dumps(event.data, sort_keys=True, default=str)
            if key in self._seen_kill_events:
                continue
            self._seen_kill_events.append(key)
            self.kill_feed.append(event.message or "entity destroyed")
            del self.kill_feed[:-8]
        self.kill_text.set_text(
            "KILL FEED\n" + "\n".join(reversed(self.kill_feed)) if self.kill_feed else ""
        )
        wave_status = next(
            (event for event in frame.events if event.event_type == "wave_status"), None
        )
        if wave_status is not None:
            memberships = wave_status.data.get("entity_waves", {})
            if isinstance(memberships, dict):
                self._entity_waves = {
                    str(entity_id): str(wave_id) for entity_id, wave_id in memberships.items()
                }
            waves = wave_status.data.get("waves", ())
            lines = ["BLUE WAVES"]
            if isinstance(waves, (list, tuple)):
                for wave in waves:
                    if not isinstance(wave, dict):
                        continue
                    lines.append(
                        f"{str(wave.get('wave_id', '?')).upper()}: "
                        f"{wave.get('spawned', 0)}/{wave.get('planned', 0)} spawned | "
                        f"{wave.get('active', 0)} active | {wave.get('destroyed', 0)} destroyed | "
                        f"{wave.get('breached', 0)} breached"
                    )
            next_wave = wave_status.data.get("next_wave")
            if isinstance(next_wave, dict):
                lines.append(
                    f"NEXT {str(next_wave.get('wave_id', '?')).upper()} IN "
                    f"{next_wave.get('ticks_remaining', 0)} ticks"
                )
            else:
                lines.append("ALL WAVES DEPLOYED")
            self.wave_text.set_text("\n".join(lines))
        renderable_entities = tuple(
            entity
            for entity in frame.entities
            if entity.status.value not in _HIDDEN_TERMINAL_STATES
        )
        visible_ids = {entity.id for entity in renderable_entities}
        for entity_id, artist in self.entity_artists.items():
            if entity_id not in visible_ids:
                artist.set_visible(False)
                self.trajectory_artists[entity_id].set_visible(False)
                self.label_artists[entity_id].set_visible(False)
                self.status_artists[entity_id].set_visible(False)
                for energy_artist in self.energy_artists[entity_id]:
                    energy_artist.set_visible(False)
        for entity in renderable_entities:
            self._update_entity(entity)
        retention_limit = max(self.max_retained_entities, len(visible_ids))
        removable_ids = tuple(
            entity_id for entity_id in self.entity_artists if entity_id not in visible_ids
        )
        for entity_id in removable_ids[: max(0, len(self.entity_artists) - retention_limit)]:
            self._remove_absent_entity(entity_id)
        self._update_transient_effects(frame)
        for existing_maneuver in self.maneuver_artists.values():
            existing_maneuver.set_visible(False)
        for event in frame.events:
            if event.event_type != "maneuver_vector" or event.entity_id is None:
                continue
            start = event.data.get("start")
            end = event.data.get("end")
            if not (
                isinstance(start, (list, tuple))
                and isinstance(end, (list, tuple))
                and len(start) >= 2
                and len(end) >= 2
            ):
                continue
            maneuver = self.maneuver_artists.get(event.entity_id)
            if maneuver is None:
                (maneuver,) = self.axes.plot(
                    [],
                    [],
                    color="#E69F00",
                    linestyle="-.",
                    marker=">",
                    markevery=[1],
                    linewidth=1.2,
                    alpha=0.75,
                    zorder=3,
                )
                self.maneuver_artists[event.entity_id] = maneuver
            maneuver.set_data(
                (float(start[0]), float(end[0])),
                (float(start[1]), float(end[1])),
            )
            maneuver.set_visible(True)

        for overlay_artist in self.overlay_artists:
            overlay_artist.remove()
        self.overlay_artists.clear()
        for event in frame.events:
            if event.event_type not in {"sensor_range", "protection_zone"}:
                continue
            center = event.data.get("center")
            radius = event.data.get("radius_m")
            if (
                not isinstance(center, (list, tuple))
                or len(center) != 2
                or not isinstance(radius, (int, float))
            ):
                continue
            x_limits = self.axes.get_xlim()
            y_limits = self.axes.get_ylim()
            safe_display_radius = min(
                float(radius),
                2.0
                * max(
                    abs(float(x_limits[1] - x_limits[0])),
                    abs(float(y_limits[1] - y_limits[0])),
                ),
            )
            patch = Circle((float(center[0]), float(center[1])), safe_display_radius)
            if event.event_type == "sensor_range":
                side = event.data.get("side")
                edgecolor = {"blue": "#0072B2", "red": "#D55E00"}.get(
                    side if isinstance(side, str) else "", "#17BECF"
                )
                patch.set(
                    facecolor="none",
                    edgecolor=edgecolor,
                    linestyle="--",
                    linewidth=1.0,
                    alpha=0.35,
                    zorder=1,
                )
            else:
                patch.set(
                    facecolor="none",
                    edgecolor="#9467BD",
                    linestyle="dashed",
                    zorder=1,
                )
            self.axes.add_patch(patch)
            self.overlay_artists.append(patch)

        for side, detections in (
            ("blue", frame.detections.blue),
            ("red", frame.detections.red),
        ):
            offsets = np.asarray([item.position[:2] for item in detections], dtype=np.float64)
            self.contact_artists[side].set_offsets(
                offsets.reshape((-1, 2)) if offsets.size else np.empty((0, 2))
            )
        self.task_text.set_text(
            "\n".join(
                filter(
                    None,
                    (
                        f"Mission: {frame.mission.status} {frame.mission.objective}".strip(),
                        f"Weather: {frame.environment.weather}",
                        *tuple(
                            event.message or event.event_type
                            for event in frame.events
                            if event.event_type
                            not in {
                                "maneuver_vector",
                                "protection_zone",
                                "sensor_range",
                                "wave_status",
                            }
                        )[-5:],
                    ),
                )
            )
        )
        self.score_text.set_text(
            f"BLUE {frame.scores.blue.total:.3f}\nRED {frame.scores.red.total:.3f}"
        )
