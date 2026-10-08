"""Weather table, unified degradation, and event-timeline tests."""

import pytest
from openmdbench.systems.weather import (
    WEATHER_EFFECTS,
    SensorKind,
    Weather,
    WeatherTimeline,
    effective_range,
    effective_speed,
)
from openmdbench.systems.weather.model import WeatherChange


@pytest.mark.parametrize(
    ("weather", "expected"),
    [
        (Weather.CLEAR, (0.0, 0.0, 0.0, 0.0)),
        (Weather.CLOUDY, (0.20, 0.05, 0.0, 0.0)),
        (Weather.LIGHT_RAIN, (0.40, 0.15, 0.10, 0.05)),
        (Weather.HEAVY_RAIN, (0.70, 0.30, 0.20, 0.10)),
        (Weather.FOG, (0.80, 0.20, 0.0, 0.05)),
        (Weather.HIGH_SEA_STATE, (0.30, 0.10, 0.30, 0.20)),
    ],
)
def test_normative_weather_table(weather: Weather, expected: tuple[float, ...]) -> None:
    effect = WEATHER_EFFECTS[weather]
    assert (effect.eo_ir, effect.radar, effect.sonar, effect.speed) == expected


def test_degradation_consistently_reduces_effective_range_and_speed() -> None:
    assert effective_range(15_000.0, SensorKind.EO_IR, Weather.FOG) == pytest.approx(3_000.0)
    assert effective_range(20_000.0, SensorKind.RADAR, Weather.HEAVY_RAIN) == 14_000.0
    assert effective_speed(10.0, Weather.HIGH_SEA_STATE) == 8.0


def test_dynamic_weather_emits_replayable_public_event() -> None:
    timeline = WeatherTimeline(
        Weather.CLEAR,
        (WeatherChange(10, Weather.CLOUDY), WeatherChange(20, Weather.HEAVY_RAIN)),
    )
    assert timeline.advance(9) == ()
    events = timeline.advance(20)
    assert [event["to"] for event in events] == ["cloudy", "heavy_rain"]
    assert timeline.current is Weather.HEAVY_RAIN
