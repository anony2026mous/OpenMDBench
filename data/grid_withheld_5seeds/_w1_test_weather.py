"""Verify the weather ladder (⑤) against the shipped environment resources.

The requirement is that the last three scenarios carry weather and that weather
is a real difficulty factor.  "The resource is declared in the YAML" is not
evidence that it does anything, so this test drives the engine's own pure
modifier pipeline with the **actual catalog content**:

    environment.rain-fog  ->  visibility 0.65 / sea_state 4 /
                              sensor_range_multiplier 0.7 /
                              sensor_detection_probability_multiplier 0.8

and asserts the tick-gated effect that the IE scenarios rely on
(IE-06 fog at 600, IE-07 at 400, IE-08 at 300).

It also pins down a dead field: ``visibility_scale`` is declared by both
environment resources but is consumed by nothing -- the same class of defect as
``health_scale`` on the damage models and ``reference_depth_m`` in the older
scorecard.  The test asserts it produces no modifier, so the fact stays visible.

Pure function: no session, no engine world, no LLM.  Runs in milliseconds.

Usage:
    python _w1_test_weather.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))

from openmdbench.world.capability_modifier_v2 import (  # noqa: E402
    modifiers_from_environment_content_v2,
    resolve_capability_v2,
)

CATALOGS = (ROOT / "catalog" / "v2" / "ie_set.yaml",
            ROOT / "catalog" / "v2" / "md_ad_006.yaml")

# The IE scenarios' declared fog onsets.
FOG_ONSET = {
    "ie_06_decoy_mixed": 600,
    "ie_07_cross_domain": 400,
    "ie_08_island_strike": 300,
}


def environment_content(ref_id: str) -> dict:
    """Read an environment resource from whichever shipped catalog defines it.

    Catalog resources carry ``id`` and ``version`` as separate fields; an exact
    reference is ``id@version``.
    """
    for catalog in CATALOGS:
        if not catalog.is_file():
            continue
        payload = yaml.safe_load(catalog.read_text(encoding="utf-8"))
        for resource in payload.get("resources") or ():
            exact = f"{resource['id']}@{resource['version']}"
            if exact == ref_id:
                return dict(resource.get("content") or {})
    raise AssertionError(f"{ref_id} not found in any shipped catalog")


def scenario_weather_events(package: str) -> list[tuple[str, int]]:
    path = ROOT / "scenarios" / "formal" / package / "scenario.yaml"
    scenario = yaml.safe_load(path.read_text(encoding="utf-8"))["scenario"]
    out = []
    for event in scenario.get("events") or ():
        if event.get("event_type") != "weather_change":
            continue
        out.append((str(event["payload"]["environment_ref"]),
                    int(event["trigger"]["tick"])))
    return out


def test_rain_fog_degrades_sensors_only_after_its_tick():
    content = environment_content("environment.rain-fog@2.0.0")
    onset = 600
    modifiers = modifiers_from_environment_content_v2(
        environment_ref="environment.rain-fog@2.0.0",
        content=content,
        source_event_id="event.weather-fog",
        active_from_tick=onset,
    )
    before = resolve_capability_v2(capability="sensor.range", base_value=15000.0,
                                   tick=onset - 1, modifiers=modifiers)
    after = resolve_capability_v2(capability="sensor.range", base_value=15000.0,
                                  tick=onset, modifiers=modifiers)
    assert before.value == 15000.0, before.value
    assert abs(after.value - 10500.0) < 1e-6, after.value      # 15000 x 0.7

    prob_before = resolve_capability_v2(capability="sensor.probability",
                                        base_value=0.9, tick=onset - 1,
                                        modifiers=modifiers)
    prob_after = resolve_capability_v2(capability="sensor.probability",
                                       base_value=0.9, tick=onset,
                                       modifiers=modifiers)
    assert abs(prob_before.value - 0.9) < 1e-9
    assert abs(prob_after.value - 0.72) < 1e-9                 # 0.9 x 0.8
    assert "environment.rain-fog@2.0.0:sensor_range_multiplier" in after.applied_modifier_ids


def test_clear_weather_changes_nothing():
    content = environment_content("environment.clear@2.0.0")
    modifiers = modifiers_from_environment_content_v2(
        environment_ref="environment.clear@2.0.0",
        content=content,
        source_event_id="event.weather-initial",
        active_from_tick=0,
    )
    resolved = resolve_capability_v2(capability="sensor.range", base_value=15000.0,
                                     tick=5000, modifiers=modifiers)
    assert resolved.value == 15000.0
    assert resolved.applied_modifier_ids == () or all(
        abs(m.value - 1.0) < 1e-9 for m in modifiers if m.capability == "sensor.range")


def test_visibility_scale_is_a_dead_field():
    """`visibility_scale` 被两个环境资源声明，但引擎里没有任何读取点。

    与 `damage.*` 的 `health_scale`、旧记分卡的 `reference_depth_m` 同类。
    本测试断言它**不产生任何 modifier**；一旦将来内核开始读它，这条会失败，
    提醒我们把气象参数的口径更新到文档与场景说明里。
    """
    for ref_id in ("environment.rain-fog@2.0.0", "environment.clear@2.0.0"):
        content = environment_content(ref_id)
        assert "visibility_scale" in content, ref_id
        modifiers = modifiers_from_environment_content_v2(
            environment_ref=ref_id, content=content,
            source_event_id=None, active_from_tick=0)
        assert not any("visibility" in m.capability for m in modifiers), ref_id
        assert not any("visibility" in m.modifier_id for m in modifiers), ref_id


def test_first_five_scenarios_are_clear_and_last_three_are_fogged():
    """⑤ 的分档：IE-01..05 全程晴好，最后三个最难场景加入 rain-fog。"""
    for index in range(1, 6):
        packages = list((ROOT / "scenarios" / "formal").glob(f"ie_0{index}_*"))
        assert packages, index
        events = scenario_weather_events(packages[0].name)
        refs = [ref for ref, _tick in events]
        assert refs == ["environment.clear@2.0.0"], (index, refs)

    for package, onset in FOG_ONSET.items():
        events = scenario_weather_events(package)
        refs = {ref: tick for ref, tick in events}
        assert "environment.rain-fog@2.0.0" in refs, (package, refs)
        assert refs["environment.rain-fog@2.0.0"] == onset, (package, refs)
        # 必须先晴后雾：初始 clear 在 tick 0
        assert refs.get("environment.clear@2.0.0") == 0, (package, refs)


def main() -> int:
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    failures = 0
    for name, function in tests:
        try:
            function()
            print(f"  PASS {name}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"  ERROR {name}: {type(error).__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
