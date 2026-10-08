"""Unit tests for the multi-dimensional strategy scorecard.

Run:
    python _w1_test_strategy_metrics.py     # standalone
    pytest _w1_test_strategy_metrics.py     # if pytest is available
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from strategy_metrics import (  # noqa: E402
    MetricsConfig,
    ROLE_FACILITY,
    ROLE_UAV,
    ROLE_USV,
    UnitState,
    classify_role,
    compute_scorecard,
    format_scorecard_line,
)

DEFENDER = "coalition.defender"
ATTACKER = "coalition.intruder"

FACILITIES = [
    {"id": "facility.command", "position_m": (0.0, 0.0, 0.0), "weight": 2.0},
    {"id": "facility.comms", "position_m": (0.0, 1000.0, 0.0), "weight": 1.0},
]


def unit(entity_id, faction, role, domain, lifecycle, health, position, tags=()):
    return UnitState(
        entity_id=entity_id, faction=faction, role=role, domain=domain,
        tags=tuple(tags), lifecycle=lifecycle, health=health,
        position_m=tuple(float(v) for v in position),
    )


def base_units():
    return {
        # defender: one surviving UAV, one lost UAV, one surviving USV
        "def.uav-1": unit("def.uav-1", DEFENDER, ROLE_UAV, "air", "active", 1.0, (0, 0, 800)),
        "def.uav-2": unit("def.uav-2", DEFENDER, ROLE_UAV, "air", "destroyed", 0.0, (5000, 0, 800)),
        "def.usv-1": unit("def.usv-1", DEFENDER, ROLE_USV, "surface", "active", 1.0, (2000, -500, 0)),
        # attacker: raider killed deep at 15 km, raider killed close at 2 km, raider alive at 1 km
        "atk.uav-deep": unit("atk.uav-deep", ATTACKER, ROLE_UAV, "air", "destroyed", 0.0,
                             (15000, 0, 100), ["target.facility.command", "wave-1"]),
        "atk.uav-close": unit("atk.uav-close", ATTACKER, ROLE_UAV, "air", "disabled", 0.4,
                              (2000, 0, 100), ["target.facility.comms"]),
        "atk.uav-leaker": unit("atk.uav-leaker", ATTACKER, ROLE_UAV, "air", "active", 1.0,
                               (1000, 0, 100), ["target.facility.command"]),
        "atk.boat-1": unit("atk.boat-1", ATTACKER, ROLE_USV, "surface", "destroyed", 0.0,
                           (6000, -2500, 0), ["strike-pier"]),
        "facility.command": unit("facility.command", DEFENDER, ROLE_FACILITY, "land",
                                 "disabled", 0.4, (0, 0, 0)),
        "facility.comms": unit("facility.comms", DEFENDER, ROLE_FACILITY, "land",
                               "active", 1.0, (0, 1000, 0)),
    }


LOSSES = [
    {"tick": 100, "entity_id": "atk.uav-deep", "faction": ATTACKER, "role": ROLE_UAV,
     "lifecycle": "destroyed", "previous_lifecycle": "active",
     "position_m": (15000.0, 0.0, 100.0)},
    {"tick": 300, "entity_id": "atk.uav-close", "faction": ATTACKER, "role": ROLE_UAV,
     "lifecycle": "disabled", "previous_lifecycle": "active",
     "position_m": (2000.0, 0.0, 100.0)},
    {"tick": 400, "entity_id": "def.uav-2", "faction": DEFENDER, "role": ROLE_UAV,
     "lifecycle": "destroyed", "previous_lifecycle": "active",
     "position_m": (5000.0, 0.0, 800.0)},
    {"tick": 500, "entity_id": "atk.boat-1", "faction": ATTACKER, "role": ROLE_USV,
     "lifecycle": "destroyed", "previous_lifecycle": "active",
     "position_m": (6000.0, -2500.0, 0.0)},
    {"tick": 600, "entity_id": "facility.command", "faction": DEFENDER,
     "role": ROLE_FACILITY, "lifecycle": "disabled", "previous_lifecycle": "active",
     "position_m": (0.0, 0.0, 0.0)},
]

FIRES = [
    {"tick": 90, "side_faction": DEFENDER, "shooter": "def.uav-1",
     "weapon": "weapon.air-interceptor-munition@2.0.0", "target": "atk.uav-deep",
     "target_role": ROLE_UAV},
    {"tick": 95, "side_faction": DEFENDER, "shooter": "def.uav-1",
     "weapon": "weapon.air-interceptor-munition@2.0.0", "target": "atk.uav-deep",
     "target_role": ROLE_UAV},
    {"tick": 290, "side_faction": DEFENDER, "shooter": "def.uav-1",
     "weapon": "weapon.air-interceptor-munition@2.0.0", "target": "atk.uav-close",
     "target_role": ROLE_UAV},
    {"tick": 400, "side_faction": ATTACKER, "shooter": "atk.uav-deep",
     "weapon": "weapon.loitering-munition@2.0.0", "target": "def.uav-2",
     "target_role": ROLE_UAV},
    {"tick": 600, "side_faction": ATTACKER, "shooter": "atk.uav-close",
     "weapon": "weapon.loitering-munition@2.0.0", "target": "facility.command",
     "target_role": ROLE_FACILITY},
]


def card(**overrides):
    arguments = dict(
        units=base_units(), losses=LOSSES, fires=FIRES, facilities=FACILITIES,
        defender_faction=DEFENDER, attacker_faction=ATTACKER,
        terminal_result={"outcome": "defender_success", "rule_id": "rule.defence-success",
                         "tick": 1799, "latched": True},
        aborted=None, ticks_run=1800, max_ticks=1800, config=MetricsConfig(),
    )
    arguments.update(overrides)
    return compute_scorecard(**arguments)


def test_classify_role():
    assert classify_role("air", ["intruder", "uav"]) == ROLE_UAV
    assert classify_role("surface", ["defence", "usv"]) == ROLE_USV
    assert classify_role("land", ["facility", "fixed"]) == ROLE_FACILITY
    assert classify_role("surface", ["facility", "pier"]) == ROLE_FACILITY  # tag wins


def test_force_accounting():
    result = card()
    assert result["force"][ATTACKER][ROLE_UAV]["total"] == 3
    assert result["force"][ATTACKER][ROLE_UAV]["lost"] == 2
    assert result["force"][ATTACKER][ROLE_UAV]["surviving"] == 1
    assert result["force"][ATTACKER][ROLE_USV]["lost"] == 1
    assert result["force"][DEFENDER][ROLE_UAV]["lost"] == 1


def test_weighted_facility_survival_uses_weights():
    result = card()
    # command weight 2 at health 0.4, comms weight 1 at health 1.0
    expected = (2.0 * 0.4 + 1.0 * 1.0) / 3.0
    assert abs(result["facilities"]["weighted_survival"] - round(expected, 4)) < 1e-6
    assert result["facilities"]["out_of_action"] == 1
    assert result["facilities"]["destroyed"] == 0


def test_interception_depth_uses_kill_position():
    result = card()
    depths = result["air_layer"]["interception_depth_m"]["per_entity"]
    # kill at (15000,0,100) vs facility.command at origin
    assert abs(depths["atk.uav-deep"] - 15000.0) < 1.0
    # kill at (2000,0,100) vs facility.comms at (0,1000,0)
    expected_close = ((2000.0 ** 2) + (1000.0 ** 2) + (100.0 ** 2)) ** 0.5
    assert abs(depths["atk.uav-close"] - expected_close) < 1.0
    assert result["air_layer"]["raiders_intercepted"] == 2
    mean = result["air_layer"]["interception_depth_m"]["mean"]
    assert abs(mean - (15000.0 + expected_close) / 2) < 1.0
    assert result["air_layer"]["interception_rate"] == round(2 / 3, 4)


def test_leak_and_release_rates():
    result = card()
    # geometric: atk.uav-leaker ends 1 km from facility.command, atk.uav-close ends
    # ~2.2 km from facility.comms -> both inside the 8 km strike radius
    assert result["air_layer"]["leakers"] == 2
    assert result["air_layer"]["leak_rate"] == round(2 / 3, 4)
    # substantive: only atk.uav-close actually released a weapon on its objective
    # (see FIRES: shooter atk.uav-close -> target facility.command, which is NOT its
    # assigned target), so no raider released on *its own* assigned objective.
    assert result["air_layer"]["released_on_target"] == 0
    assert result["air_layer"]["release_rate"] == 0.0
    assert result["layers"]["leak"] == 1.0


def test_release_on_assigned_target_is_penetration():
    fires = list(FIRES) + [
        {"tick": 610, "side_faction": ATTACKER, "shooter": "atk.uav-close",
         "weapon": "weapon.loitering-munition@2.0.0", "target": "facility.comms",
         "target_role": ROLE_FACILITY},
    ]
    result = card(fires=fires)
    assert result["air_layer"]["released_on_target"] == 1
    assert result["air_layer"]["release_rate"] == round(1 / 3, 4)
    assert result["layers"]["leak"] < 1.0


def test_terminal_consistency_guard():
    # Declaring a defender win while every protected facility is destroyed is
    # contradictory and must be penalised.
    all_dead = base_units()
    for facility_id, position in (("facility.command", (0, 0, 0)),
                                  ("facility.comms", (0, 1000, 0))):
        all_dead[facility_id] = unit(facility_id, DEFENDER, ROLE_FACILITY, "land",
                                     "destroyed", 0.0, position)

    consistent_attacker = card(
        units=all_dead,
        terminal_result={"outcome": "intruder_success", "rule_id": "rule.facilities-lost",
                         "tick": 1500, "latched": True})
    assert consistent_attacker["terminal"]["consistent_with_evidence"] is True

    contradictory = card(
        units=all_dead,
        terminal_result={"outcome": "defender_success", "rule_id": "rule.defence-success",
                         "tick": 1799, "latched": True})
    assert contradictory["terminal"]["consistent_with_evidence"] is False
    assert contradictory["layers"]["terminal"] < 1.0

    # An attacker win with no destroyed facility is equally contradictory.
    intact = base_units()
    intact["facility.command"] = unit("facility.command", DEFENDER, ROLE_FACILITY,
                                      "land", "active", 1.0, (0, 0, 0))
    bogus_attacker_win = card(
        units=intact,
        terminal_result={"outcome": "intruder_success", "rule_id": "rule.facilities-lost",
                         "tick": 1500, "latched": True})
    assert bogus_attacker_win["terminal"]["consistent_with_evidence"] is False


def test_abort_scores_zero_terminal():
    result = card(aborted="exception: boom")
    assert result["terminal"]["state"] == "aborted"
    assert result["layers"]["terminal"] == 0.0


def test_overall_score_is_weighted_sum_of_layers():
    result = card()
    weights = result["layer_weights"]
    total = sum(weights.values())
    expected = sum(result["layers"][name] * weights[name] for name in weights) / total
    assert abs(result["defender_score"] - round(expected, 4)) < 1e-6
    assert abs(result["attacker_score"] + result["defender_score"] - 1.0) < 1e-6
    for name, value in result["layers"].items():
        assert 0.0 <= value <= 1.0, name


def test_better_defence_scores_higher():
    """Deeper interception + intact facilities must beat shallow + damaged."""

    deep_units = base_units()
    deep_units["atk.uav-close"] = unit("atk.uav-close", ATTACKER, ROLE_UAV, "air",
                                       "destroyed", 0.0, (14000, 1000, 100),
                                       ["target.facility.comms"])
    deep_units["atk.uav-leaker"] = unit("atk.uav-leaker", ATTACKER, ROLE_UAV, "air",
                                        "destroyed", 0.0, (17000, 0, 100),
                                        ["target.facility.command"])
    deep_units["facility.command"] = unit("facility.command", DEFENDER, ROLE_FACILITY,
                                          "land", "active", 1.0, (0, 0, 0))
    deep_losses = [
        dict(LOSSES[1], lifecycle="destroyed", position_m=(14000.0, 1000.0, 100.0)),
        {"tick": 320, "entity_id": "atk.uav-leaker", "faction": ATTACKER,
         "role": ROLE_UAV, "lifecycle": "destroyed", "previous_lifecycle": "active",
         "position_m": (17000.0, 0.0, 100.0)},
        LOSSES[2], LOSSES[3],
    ]
    good = card(units=deep_units, losses=deep_losses)
    # The poor case also lets a raider actually release on its objective.
    poor_fires = list(FIRES) + [
        {"tick": 620, "side_faction": ATTACKER, "shooter": "atk.uav-leaker",
         "weapon": "weapon.loitering-munition@2.0.0", "target": "facility.command",
         "target_role": ROLE_FACILITY},
    ]
    poor = card(fires=poor_fires)
    assert good["defender_score"] > poor["defender_score"]
    assert good["layers"]["depth"] > poor["layers"]["depth"]
    assert good["layers"]["leak"] > poor["layers"]["leak"]
    assert good["layers"]["facilities"] > poor["layers"]["facilities"]


def test_unresolved_raider_is_reported_not_silently_zero():
    units = base_units()
    units["atk.uav-notag"] = unit("atk.uav-notag", ATTACKER, ROLE_UAV, "air", "active",
                                  1.0, (30000, 0, 100), ["intruder"])
    result = card(units=units)
    assert result["air_layer"]["unresolved_assignments"] == 1
    assert result["air_layer"]["raiders_total"] == 4


def test_unstructured_terminal_blob_is_parsed_not_substring_matched():
    """The engine's frozen receipt blob must not be classified by substring.

    The blob also contains the ranking map ('coalition.intruder': 2), so a naive
    ``"intruder" in blob`` check reports an attacker win for a defender hold.
    """

    blob = ("TerminalMissionResultV2(rule_id='rule.defence-success', "
            "outcome='defender_success', priority=50, tick=1799, latched=True, "
            "trigger_evidence=mappingproxy({'event_id': 'event.defence-success'}), "
            "ranking=mappingproxy({'coalition.defender': 1, 'coalition.intruder': 2}))")
    result = card(terminal_result={"result": blob})
    assert result["terminal"]["state"] == "defender_success"
    assert result["terminal"]["unstructured_receipt"] is True
    assert result["terminal"]["rule_id"] == "rule.defence-success"
    assert result["terminal"]["tick"] == 1799
    assert result["terminal"]["latched"] is True
    assert result["layers"]["terminal"] == 1.0


def test_mapping_terminal_receipt_is_structured():
    result = card()
    assert result["terminal"]["unstructured_receipt"] is False
    assert result["terminal"]["state"] == "defender_success"


def test_terminal_state_never_uses_ranking_text():
    from strategy_metrics import classify_terminal_state

    assert classify_terminal_state("defender_success") == "defender_success"
    assert classify_terminal_state("intruder_success") == "attacker_success"
    # unknown labels must not be guessed from the word "intruder" alone when it is
    # only present as a field name is not possible here -> explicit mapping wins
    assert classify_terminal_state("timeout") == "defender_success"
    assert classify_terminal_state(None) == "undecided"


def test_rescore_offline_matches_inline_scoring():
    import copy

    from strategy_metrics import rescore_report_terminal

    blob = ("TerminalMissionResultV2(rule_id='rule.defence-success', "
            "outcome='defender_success', priority=50, tick=1799, latched=True, "
            "ranking=mappingproxy({'coalition.defender': 1, 'coalition.intruder': 2}))")
    good = card(terminal_result={"result": blob})
    # simulate a pre-fix report whose embedded terminal layer was misclassified
    embedded = copy.deepcopy(good)
    embedded["layers"]["terminal"] = 0.0
    embedded["defender_score"] = 0.0
    embedded["attacker_score"] = 1.0
    report = {"terminal_result": {"result": blob}, "aborted": None,
              "strategy_scorecard": embedded}

    rescored = rescore_report_terminal(report)
    assert rescored["strategy_scorecard"]["layers"]["terminal"] == good["layers"]["terminal"]
    assert rescored["strategy_scorecard"]["terminal"]["rescored_offline"] is True
    weights = rescored["strategy_scorecard"]["layer_weights"]
    total = sum(weights.values())
    expected = sum(rescored["strategy_scorecard"]["layers"][k] * weights[k]
                   for k in weights) / total
    assert abs(rescored["strategy_scorecard"]["defender_score"] - round(expected, 4)) < 1e-6
    assert abs(rescored["strategy_scorecard"]["defender_score"]
               - good["defender_score"]) < 1e-6


def test_depth_layer_is_robust_to_mean_masking():
    """A mean-based depth layer lets a few long kills hide point-blank defence."""

    from strategy_metrics import MetricsConfig, depth_layer_score

    cfg = MetricsConfig()
    # 12 raiders, all stopped deep
    deep_score, deep_info = depth_layer_score(
        [9000.0, 10000.0, 11000.0] * 4, cfg, raiders_total=12)
    # 12 raiders, only 3 stopped deep and the rest got through
    masked_score, masked_info = depth_layer_score(
        [200.0, 300.0, 30000.0], cfg, raiders_total=12)

    assert deep_info["median_m"] > 9000.0
    assert masked_info["median_m"] < 1000.0
    assert deep_info["legacy_deep_rate"] == 1.0
    assert masked_info["legacy_deep_rate"] == round(1 / 12, 4)
    # 连续口径把纵深按 reference_depth_m 归一化，量级比旧的二值口径小，
    # 但"多数拦得远"相对"少数拦得极远、其余漏防"仍应有数倍差距
    assert deep_score > masked_score * 3
    assert 0.0 <= masked_score <= 1.0 and 0.0 <= deep_score <= 1.0


def test_depth_layer_does_not_reward_disengaging():
    """The layer must measure coverage × depth, never "fly away and score".

    ``depth`` is defined over all raiders, so failing to engage scores zero; among
    defences that stop the same number, stopping them farther out scores higher.
    """

    from strategy_metrics import MetricsConfig, depth_layer_score

    cfg = MetricsConfig()
    # engaged nobody
    none_score, _ = depth_layer_score([], cfg, raiders_total=12)
    # stopped 4 at point-blank
    near_score, _ = depth_layer_score([150.0] * 4, cfg, raiders_total=12)
    # stopped the same 4 far out
    far_score, _ = depth_layer_score([19000.0] * 4, cfg, raiders_total=12)
    # stopped 7 far out
    more_score, _ = depth_layer_score([19000.0] * 7, cfg, raiders_total=12)

    assert none_score == 0.0
    # 贴脸拦截在新连续口径下不再是严格 0，而是"几乎不值分"
    assert near_score < 0.01
    assert far_score > near_score
    assert more_score > far_score
    # 4 架在 19 km 被拦：每个 min(1, 19000/20000)=0.95，分母是全部 12 个来袭者
    assert abs(far_score - 4 * 0.95 / 12) < 1e-6
    assert abs(more_score - 7 * 0.95 / 12) < 1e-6
    # 旧口径同时保留，便于与历史结果对照
    assert _legacy_deep_rate(depths=[19000.0] * 4, total=12) == round(4 / 12, 4)


def _legacy_deep_rate(*, depths: list[float], total: int) -> float:
    from strategy_metrics import MetricsConfig, depth_layer_score

    _score, info = depth_layer_score(depths, MetricsConfig(), raiders_total=total)
    return info["legacy_deep_rate"]


def test_depth_layer_empty_is_zero():
    from strategy_metrics import MetricsConfig, depth_layer_score

    score, info = depth_layer_score([], MetricsConfig(), raiders_total=0)
    assert score == 0.0
    assert info["intercepted"] == 0
    assert info["median_m"] is None


def test_format_line_renders():
    line = format_scorecard_line(card(), "rule")
    assert line.startswith("rule")
    assert "overall=" in line


def _weighted_average(result):
    weights = result["layer_weights"]
    applicable = result["layer_applicability"]
    denominator = sum(weights[name] for name in weights if applicable[name])
    numerator = sum(result["layers"][name] * weights[name]
                    for name in weights if applicable[name])
    return numerator / denominator, denominator


def _without_air_raiders():
    """纯水面突袭（IE-03 形态）：来袭方只有自爆船，没有无人机。"""
    units = {key: value for key, value in base_units().items()
             if not (value.faction == ATTACKER and value.role == ROLE_UAV)}
    dropped = ("atk.uav-deep", "atk.uav-close")
    return card(
        units=units,
        losses=[row for row in LOSSES if row["entity_id"] not in dropped],
        fires=[row for row in FIRES
               if row["shooter"] not in dropped and row["target"] not in dropped],
    )


def _without_surface_threat():
    """纯空中来袭（IE-01/IE-02 形态）：来袭方没有水面平台。"""
    return card(
        units={key: value for key, value in base_units().items()
               if key != "atk.boat-1"},
        losses=[row for row in LOSSES if row["entity_id"] != "atk.boat-1"],
    )


def test_missing_air_raiders_does_not_zero_the_depth_layer():
    """IE-03 回归：没有空中来袭者时，纵深/漏防两层必须退出加权，而不是记 0。

    第 11 轮实测 IE-03 的 `layer_depth` 恒为 0.0、`layer_leak` 恒为 1.0，纯粹
    因为该场景没有无人机 —— 等于凭空扣掉 0.30 权重，把最容易的场景压到与
    更难场景同分（0.8000）。N/A 既不能自动计零，也不能自动计满分。
    """
    result = _without_air_raiders()
    assert result["layer_applicability"]["depth"] is False
    assert result["layer_applicability"]["leak"] is False
    assert result["layer_applicability"]["surface"] is True
    # 层分数本身仍然照实报出（便于诊断），只是不再参与加权
    assert result["layers"]["depth"] == 0.0
    expected, denominator = _weighted_average(result)
    assert abs(denominator - 0.70) < 1e-9, denominator
    assert abs(result["defender_score"] - round(expected, 4)) < 1e-6
    assert result["defender_score"] > result["legacy_defender_score_all_layers"]


def test_missing_surface_threat_does_not_gift_the_surface_layer():
    """没有水面来袭者时水面层 N/A，不能白送 0.10 权重。"""
    result = _without_surface_threat()
    assert result["layer_applicability"]["surface"] is False
    assert result["layer_applicability"]["depth"] is True
    assert result["layers"]["surface"] == 1.0  # 照实报出，但不计权重
    expected, denominator = _weighted_average(result)
    assert abs(denominator - 0.90) < 1e-9, denominator
    assert abs(result["defender_score"] - round(expected, 4)) < 1e-6


def test_legacy_score_kept_for_old_reports():
    """旧口径（全 7 层恒定分母）必须保留，历史结果才可对照。"""
    result = _without_air_raiders()
    weights = result["layer_weights"]
    total = sum(weights.values())
    legacy = sum(result["layers"][name] * weights[name] for name in weights) / total
    assert abs(result["legacy_defender_score_all_layers"] - round(legacy, 4)) < 1e-6
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_format_line_marks_na_layers():
    line = format_scorecard_line(_without_air_raiders(), "rule")
    assert "depth= n/a" in line, line
    assert "leak= n/a" in line, line
    assert "surf=" in line and "surf= n/a" not in line, line


def test_collisions_are_not_credited_as_kills():
    """IE-03 回归：非战斗损失（碰撞/搁浅/自爆）不能算成对方击杀。

    实测 IE-03 我方只开火 2 发，却有 4 艘自爆船落损（其余是碰撞），旧口径记
    "4 个击杀" → 弹药效率 2.0（层饱和）、交换比放大 2 倍。归因后只认
    `source_kind == "weapon"` 且来源为对方且非自伤的那些损失。
    """
    losses = []
    for index, cause in enumerate(("weapon", "weapon", "collision", "environment")):
        losses.append({
            "tick": 100 + index, "entity_id": f"atk.boat-{index}", "faction": ATTACKER,
            "role": ROLE_USV, "lifecycle": "destroyed", "previous_lifecycle": "active",
            "position_m": (6000.0, 0.0, 0.0),
            "damage_source_kind": cause,
            "killer_entity_id": "def.usv-1" if cause == "weapon" else None,
            "killer_faction": DEFENDER if cause == "weapon" else None,
            "self_inflicted": False,
        })
    result = card(losses=losses, fires=FIRES)
    fire = result["fire"]
    assert fire["kill_attribution"] == "damage_intent"
    assert fire["defender_kills"] == 2, fire["defender_kills"]
    assert fire["defender_kills_all_causes"] == 4
    assert fire["non_combat_losses"] == 2
    # 弹药效率按真实击杀算，而不是按落损数
    assert abs(fire["defender_ammo_efficiency"]
               - round(2 / len([f for f in FIRES
                                if f["side_faction"] == DEFENDER]), 4)) < 1e-6


def test_self_inflicted_damage_is_not_a_kill_for_either_side():
    """自爆战斗部由来袭方自己引爆，不能算成防守方的击杀。"""
    losses = [{
        "tick": 300, "entity_id": "atk.boat-9", "faction": ATTACKER,
        "role": ROLE_USV, "lifecycle": "destroyed", "previous_lifecycle": "active",
        "position_m": (700.0, -1000.0, 0.0),
        "damage_source_kind": "weapon",
        "killer_entity_id": "atk.boat-9",
        "killer_faction": ATTACKER,
        "self_inflicted": True,
    }]
    result = card(losses=losses, fires=FIRES)
    assert result["fire"]["defender_kills"] == 0
    assert result["fire"]["non_combat_losses"] == 1


def test_unattributed_losses_fall_back_to_legacy_counting():
    """老报告没有归因字段时必须回退旧口径，否则历史结果无法复算对照。"""
    result = card()  # LOSSES fixture carries no damage_source_kind
    assert result["fire"]["kill_attribution"] == "legacy_all_causes"
    assert result["fire"]["defender_kills"] == sum(
        1 for row in LOSSES if row["faction"] == ATTACKER)
    assert result["fire"]["attacker_kills"] == sum(
        1 for row in LOSSES if row["faction"] == DEFENDER)
    assert result["fire"]["non_combat_losses"] == 0


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
    print()
    print(format_scorecard_line(card(), "fixture"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
