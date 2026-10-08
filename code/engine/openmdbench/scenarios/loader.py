"""Safe YAML loading and public-only briefing rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from openmdbench.scenarios.md_ad_002_config import MDAD002_CONFIG_PATHS, load_md_ad_002_config
from openmdbench.scenarios.schema import Scenario

SCENARIO_ROOT = Path(__file__).parent


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open(encoding="utf-8") as scenario_file:
        raw: Any = yaml.safe_load(scenario_file)
    if not isinstance(raw, dict):
        raise ValueError("scenario YAML root must be an object")
    return Scenario.model_validate(raw)


def load_scenario_id(scenario_id: str) -> Scenario:
    """Resolve an installed scenario by its public identifier."""
    if scenario_id == "MD-AD-002":
        raise ValueError(
            "MD-AD-002 is deprecated; use MD-AD-002-EASY, MD-AD-002-MEDIUM, or MD-AD-002-HARD"
        )
    if scenario_id in MDAD002_CONFIG_PATHS:
        config = load_md_ad_002_config(scenario_id).config
        template = load_scenario(SCENARIO_ROOT / "area_denial/MD-AD-002.yaml")
        return template.model_copy(
            update={
                "scenario_id": scenario_id,
                "difficulty": config.difficulty,
                "public": template.public.model_copy(
                    update={"name": f"海空协同多波次拒止（{config.difficulty.upper()}）"}
                ),
            }
        )
    matches = tuple(SCENARIO_ROOT.glob(f"*/{scenario_id}.yaml"))
    if len(matches) != 1:
        raise ValueError(f"unknown or ambiguous scenario_id: {scenario_id}")
    return load_scenario(matches[0])


def installed_scenarios() -> tuple[Scenario, ...]:
    """Return public scenarios, replacing the retired AD-002 placeholder by its variants."""
    regular = tuple(
        load_scenario(path)
        for path in SCENARIO_ROOT.glob("*/*.yaml")
        if path.name != "MD-AD-002.yaml"
    )
    variants = tuple(load_scenario_id(scenario_id) for scenario_id in MDAD002_CONFIG_PATHS)
    return tuple(sorted((*regular, *variants), key=lambda item: item.scenario_id))


def render_briefing(scenario: Scenario) -> str:
    """Render only explicitly public fields; referee data is structurally unreachable."""
    public = scenario.public
    primary = "\n".join(f"- {objective}" for objective in public.primary_objectives)
    secondary = "\n".join(f"- {objective}" for objective in public.secondary_objectives) or "- None"
    return (
        f"【任务名称】{scenario.scenario_id} - {public.name}\n\n"
        f"【任务背景】\n{public.background}\n\n"
        f"【任务目标】\n主要目标：\n{primary}\n次要目标：\n{secondary}\n\n"
        f"【情报评估】\n天气预测：{public.weather_forecast}\n\n"
        f"【约束条件】\n时间限制：{scenario.time_limit_ticks} tick\n"
        f"交战规则：{', '.join(scenario.roe)}"
    )
