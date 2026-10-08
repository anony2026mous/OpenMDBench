"""Single interpretation of benchmark weather degradation values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Weather(StrEnum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    HIGH_SEA_STATE = "high_sea_state"


class SensorKind(StrEnum):
    EO_IR = "eo_ir"
    RADAR = "radar"
    SONAR = "sonar"


@dataclass(frozen=True, slots=True)
class WeatherEffect:
    eo_ir: float
    radar: float
    sonar: float
    speed: float


WEATHER_EFFECTS = {
    Weather.CLEAR: WeatherEffect(0.0, 0.0, 0.0, 0.0),
    Weather.CLOUDY: WeatherEffect(0.20, 0.05, 0.0, 0.0),
    Weather.LIGHT_RAIN: WeatherEffect(0.40, 0.15, 0.10, 0.05),
    Weather.HEAVY_RAIN: WeatherEffect(0.70, 0.30, 0.20, 0.10),
    Weather.FOG: WeatherEffect(0.80, 0.20, 0.0, 0.05),
    Weather.HIGH_SEA_STATE: WeatherEffect(0.30, 0.10, 0.30, 0.20),
}


def effective_range(base_range_m: float, sensor: SensorKind, weather: Weather) -> float:
    """Apply every sensor degradation as a reduction in effective range."""
    if base_range_m < 0.0:
        raise ValueError("base sensor range cannot be negative")
    effect = WEATHER_EFFECTS[weather]
    degradation = {
        SensorKind.EO_IR: effect.eo_ir,
        SensorKind.RADAR: effect.radar,
        SensorKind.SONAR: effect.sonar,
    }[sensor]
    return base_range_m * (1.0 - degradation)


def effective_speed(base_speed_mps: float, weather: Weather) -> float:
    if base_speed_mps < 0.0:
        raise ValueError("base speed cannot be negative")
    return base_speed_mps * (1.0 - WEATHER_EFFECTS[weather].speed)


@dataclass(frozen=True, slots=True)
class WeatherChange:
    tick: int
    weather: Weather


class WeatherTimeline:
    def __init__(self, initial: Weather, changes: tuple[WeatherChange, ...] = ()) -> None:
        if any(change.tick < 0 for change in changes):
            raise ValueError("weather change tick cannot be negative")
        if tuple(sorted(changes, key=lambda change: change.tick)) != changes:
            raise ValueError("weather changes must be sorted by tick")
        if len({change.tick for change in changes}) != len(changes):
            raise ValueError("only one weather change is allowed per tick")
        self.initial = initial
        self.changes = changes
        self._next_change = 0
        self.current = initial

    def advance(self, tick: int) -> tuple[dict[str, str | int], ...]:
        events: list[dict[str, str | int]] = []
        while self._next_change < len(self.changes):
            change = self.changes[self._next_change]
            if change.tick > tick:
                break
            previous = self.current
            self.current = change.weather
            events.append(
                {
                    "event_type": "weather_changed",
                    "from": previous.value,
                    "timestamp": change.tick,
                    "to": self.current.value,
                }
            )
            self._next_change += 1
        return tuple(events)
