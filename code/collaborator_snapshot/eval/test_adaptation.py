"""W1 适配层自测：GOAI 协议纯单测 + LLM planner stub + V2 引擎 60-tick 冒烟。

运行（Linux 原生、仓库根目录）：
    PYTHONPATH=$PWD MPLCONFIGDIR=/tmp/openmdbench-mpl .venv/bin/python \
      ../eval_w1/test_adaptation.py

也可被 pytest 收集（所有 test_* 函数）。引擎冒烟需要 MMG 子进程，
必须在 Linux 原生文件系统上运行，且入口有 __main__ 保护。
"""

from __future__ import annotations

import traceback
from types import SimpleNamespace

from goai_protocol import GOAIBroker, GoalCommand, StatusReport
from rule_planner import RulePlannerConfigV2, RulePlannerV2
from llm_planner import LLMPlannerV2


# ---------------------------------------------------------------------------
# 纯协议 / 规划层测试
# ---------------------------------------------------------------------------

def _own(eid, x, y, z, energy=1.0):
    return {"entity_id": eid, "lifecycle_state": "active",
            "position_m": (float(x), float(y), float(z)),
            "velocity_mps": (0.0, 0.0, 0.0),
            "heading_deg": 0.0, "health": 1.0, "energy": energy}


def _contact(cid, x, y, conf=0.9, age=1, observer="defender.picket-001"):
    return {"contact_id": cid, "observer_entity_id": observer,
            "estimated_position_m": (float(x), float(y), 100.0),
            "confidence": conf, "age_ticks": age}


OWN = [
    _own("defender.interceptor-001", 8000.0, 0.0, 800.0),
    _own("defender.interceptor-002", 8000.0, 2000.0, 800.0),
    _own("defender.interceptor-003", 8000.0, -2000.0, 800.0),
    _own("defender.picket-001", 12334.0, 4995.0, 0.0),
    _own("defender.picket-002", 17620.0, -1110.0, 0.0),
    _own("defender.shore-ew", -1057.0, 222.0, 0.0),
]
CONTACTS = [
    _contact("intruder.wave-1-001", 9000.0, 500.0),
    _contact("intruder.wave-1-002", 20000.0, -500.0),
]
ROLES = {
    "defender.interceptor-001": frozenset({"defence", "interceptor"}),
    "defender.interceptor-002": frozenset({"defence", "interceptor"}),
    "defender.interceptor-003": frozenset({"defence", "interceptor"}),
    "defender.picket-001": frozenset({"defence", "picket"}),
    "defender.picket-002": frozenset({"defence", "picket"}),
    "defender.shore-ew": frozenset({"defence", "fixed", "early-warning"}),
}


def _fake_observation(own, contacts):
    return SimpleNamespace(
        own_entities=tuple(own),
        contacts_by_faction={"coalition.defender": tuple(contacts)},
        observer_faction_id="coalition.defender",
    )


def test_broker_accept_and_reject():
    broker = GOAIBroker()
    good = GoalCommand(task_id="patrol_001", goal_type="patrol",
                       parameters={"unit_id": "u1", "position": [1.0, 2.0]})
    result = broker.submit_goals([good], step=0)
    assert result["accepted"] == ["patrol_001"], result
    bad = GoalCommand(task_id="bad_001", goal_type="explode",
                      parameters={"unit_id": "u1"})
    result2 = broker.submit_goals([bad], step=1)
    assert result2["rejected"], result2


def test_broker_supersede_and_negotiation():
    broker = GOAIBroker()
    broker.submit_goals([GoalCommand(task_id="patrol_001", goal_type="patrol",
                                     parameters={"unit_id": "u1",
                                                 "position": [1.0, 2.0]})],
                       step=0)
    broker.submit_goals([GoalCommand(task_id="patrol_002", goal_type="patrol",
                                     parameters={"unit_id": "u1",
                                                 "position": [3.0, 4.0]})],
                       step=1)
    assert broker.active["patrol_001"].status == "superseded"
    broker.post_report(StatusReport(task_id="patrol_002", status="infeasible",
                                    progress=0.0))
    result = broker.submit_goals(
        [GoalCommand(task_id="patrol_003", goal_type="patrol",
                     parameters={"unit_id": "u1", "position": [3.0, 4.0]})],
        step=2,
    )
    assert result["rejected"], "同签名不可行目标重发应被拒绝"
    result2 = broker.submit_goals(
        [GoalCommand(task_id="patrol_004", goal_type="patrol",
                     parameters={"unit_id": "u1", "position": [5.0, 6.0]})],
        step=3,
    )
    assert result2["accepted"], "修改参数后应允许重发"


def test_rule_planner_goals():
    planner = RulePlannerV2(RulePlannerConfigV2())
    commands = planner.plan(_fake_observation(OWN, CONTACTS), tick=5,
                            unit_roles=ROLES)
    by_unit = {c.unit_id: c for c in commands}
    assert "defender.shore-ew" not in by_unit  # fixed 单位不分配
    intercepts = [c for c in commands if c.goal_type == "intercept"]
    assert len(intercepts) == 2
    targets = {c.parameters["target_id"] for c in intercepts}
    assert targets == {"intruder.wave-1-001", "intruder.wave-1-002"}
    patrol = [c for c in commands if c.goal_type == "patrol"]
    # 2 个接触被 2 架拦截机瓜分，剩余 1 架拦截机进入巡逻
    assert any(c.unit_id.startswith("defender.interceptor") for c in patrol)
    assert any(c.unit_id.startswith("defender.picket") for c in patrol)


def test_rule_planner_low_energy_return():
    own = [dict(OWN[0], energy=0.1), *OWN[1:]]
    planner = RulePlannerV2(RulePlannerConfigV2())
    commands = planner.plan(_fake_observation(own, CONTACTS), tick=5,
                            unit_roles=ROLES)
    returns = [c for c in commands if c.goal_type == "return"]
    assert any(c.unit_id == "defender.interceptor-001" for c in returns)


def test_rule_planner_policy_driven_weapon_units():
    """场景泛化：weapon_policies 提供时按 selector 标签判定武装，不再硬编码 interceptor。"""
    roles = {
        "defender.gunship-001": frozenset({"defence", "gunship"}),
        "defender.interceptor-001": frozenset({"defence", "interceptor"}),
        "defender.picket-001": frozenset({"defence", "picket"}),
    }
    own = [
        _own("defender.gunship-001", 8000.0, 0.0, 800.0),
        _own("defender.interceptor-001", 8000.0, 2000.0, 800.0),
        _own("defender.picket-001", 12334.0, 4995.0, 0.0),
    ]
    cfg = RulePlannerConfigV2(
        weapon_policies=(SimpleNamespace(selector_tags=("gunship",)),),
        patrol_anchors_weapon=(),  # 空锚点 → 按保护目标合成环形锚点
        patrol_anchors_sensor=(),
    )
    planner = RulePlannerV2(cfg)
    commands = planner.plan(
        _fake_observation(own, [
            _contact("sensor.contact.defender.picket-001.intruder.wave-1-001",
                     9000.0, 500.0),
        ]), tick=5, unit_roles=roles)
    by_unit = {c.unit_id: c for c in commands}
    intercepts = [c for c in commands if c.goal_type == "intercept"]
    assert [c.unit_id for c in intercepts] == ["defender.gunship-001"], \
        "有策略标签的单位才拿 intercept"
    assert "defender.interceptor-001" not in {
        c.unit_id for c in intercepts}, "无策略标签不视为武装"
    # 未分配单位拿到合成巡逻锚点（相对 objective 的环形点，不崩溃即可）
    patrol = [c for c in commands if c.goal_type == "patrol"]
    assert patrol, "空锚点配置应回退到合成环形锚点"
    for c in patrol:
        pos = c.parameters["position"]
        assert len(pos) == 3 and isinstance(pos[0], float)
    # weapon_policies 为空时回退 weapon_tags（默认 interceptor），行为不变
    default = RulePlannerV2(RulePlannerConfigV2())
    cmds = default.plan(_fake_observation(OWN, CONTACTS), tick=5,
                        unit_roles=ROLES)
    assert any(c.goal_type == "intercept" for c in cmds)


class _StubLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.prompts = []

    def chat(self, system_prompt, user_message, max_tokens=None,
             temperature=0.1):
        self.calls += 1
        self.prompts.append((system_prompt, user_message))
        return self.responses.pop(0) if self.responses else ""


def test_llm_planner_parses_and_falls_back():
    json_resp = (
        '{"goal_commands":[{"task_id":"intercept_001","goal_type":"intercept",'
        '"parameters":{"unit_id":"defender.interceptor-001",'
        '"target_id":"intruder.wave-1-001"},"priority":0.9}],'
        '"reasoning":"engage nearest"}'
    )
    stub = _StubLLM([json_resp, "抱歉，我无法输出 JSON。", "garbage {{{"])
    planner = LLMPlannerV2(RulePlannerConfigV2(), llm=stub)
    commands = planner.plan(_fake_observation(OWN, CONTACTS), tick=5,
                            unit_roles=ROLES)
    assert len(commands) == 1 and commands[0].goal_type == "intercept"
    # D1：已有可用目标集时，解析失败沿用上一轮（旧目标继续执行），不回退规则
    commands2 = planner.plan(_fake_observation(OWN, CONTACTS), tick=6,
                             unit_roles=ROLES)
    assert commands2, "解析失败应有可用目标（沿用上一轮）"
    assert commands2[0].goal_type == "intercept"
    stats = planner.get_stats()
    assert stats["stale_plan_reuse"] >= 1
    assert stats["parse_failures"] >= 1
    # 无历史目标（新一局第一步就失败）才回退到规则规划器
    fresh = LLMPlannerV2(RulePlannerConfigV2(), llm=_StubLLM(["garbage {{{"]))
    fresh_commands = fresh.plan(_fake_observation(OWN, CONTACTS), tick=0,
                                unit_roles=ROLES)
    assert fresh_commands and fresh.get_stats()["fallback_count"] == 1
    assert fresh_commands[0].goal_type in ("intercept", "patrol")


def test_llm_planner_resolves_abbreviated_contact_ids():
    from llm_planner import LLMPlannerV2

    # 千问把完整 contact_id 简写为实体后缀（三方法复现 Hybrid 0 开火的根因回归）
    obs = _fake_observation(OWN, [
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                 9000.0, 500.0, observer="defender.interceptor-001"),
        _contact("sensor.contact.defender.picket-001.intruder.wave-1-002",
                 20000.0, -500.0, observer="defender.picket-001"),
    ])
    planner = LLMPlannerV2(RulePlannerConfigV2())
    plan = {"goal_commands": [
        {"task_id": "intercept_001", "goal_type": "intercept",
         "parameters": {"unit_id": "defender.interceptor-001",
                        "target_id": "intruder.wave-1-001"}, "priority": 0.9},
        {"task_id": "track_001", "goal_type": "track",
         "parameters": {"unit_id": "defender.picket-001",
                        "target_id": "intruder.wave-1-002"}, "priority": 0.7},
        {"task_id": "intercept_002", "goal_type": "intercept",
         "parameters": {"unit_id": "defender.interceptor-002",
                        "target_id": "intruder.wave-1-999"}, "priority": 0.8},
    ]}
    commands = planner._validate_commands(plan, obs, ROLES)
    assert len(commands) == 2, "后缀匹配应保留两条有效命令"
    by_type = {c.goal_type: c for c in commands}
    assert by_type["intercept"].parameters["target_id"].startswith("sensor.contact.")
    assert by_type["track"].parameters["target_id"].startswith("sensor.contact.")
    # 歧义后缀：优先命令单位自己观测的接触；都不持有 → 置信度最高者
    ambiguous = _fake_observation(OWN, [
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                 1000.0, 0.0, conf=0.6, observer="defender.interceptor-001"),
        _contact("sensor.contact.defender.picket-001.intruder.wave-1-001",
                 2000.0, 0.0, conf=0.9, observer="defender.picket-001"),
    ])
    contacts_by_id = {
        c["contact_id"]: c
        for c in ambiguous.contacts_by_faction["coalition.defender"]
    }
    assert LLMPlannerV2._resolve_contact_id(
        "intruder.wave-1-001", contacts_by_id,
        "defender.interceptor-001",
    ) == "sensor.contact.defender.interceptor-001.intruder.wave-1-001"
    assert LLMPlannerV2._resolve_contact_id(
        "intruder.wave-1-001", contacts_by_id,
        "defender.interceptor-002",
    ) == "sensor.contact.defender.picket-001.intruder.wave-1-001"
    # 完全不存在 → None
    assert LLMPlannerV2._resolve_contact_id(
        "intruder.wave-9-999", contacts_by_id, "defender.interceptor-001") is None


def test_llm_planner_remaps_intercept_to_armed_observer():
    obs = _fake_observation(OWN, [
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                 9000.0, 500.0, observer="defender.interceptor-001"),
    ])
    planner = LLMPlannerV2(RulePlannerConfigV2())
    commands = planner._validate_commands({"goal_commands": [{
        "task_id": "intercept_001", "goal_type": "intercept",
        "parameters": {"unit_id": "defender.picket-001",
                        "target_id": "intruder.wave-1-001"},
    }]}, obs, ROLES)
    assert len(commands) == 1
    assert commands[0].unit_id == "defender.interceptor-001"


def test_llm_planner_scenario_prompt_context():
    """场景泛化：prompt_context 注入保护区/射程，armed_tags 数据驱动武装判定。"""
    # 默认口径 = AD-002：system prompt 含保护区 (0,0) 与武器射程
    default = LLMPlannerV2(RulePlannerConfigV2())
    assert "(0,0)" in default._system_prompt
    assert "500-8000" in default._system_prompt
    assert default._armed_unit({"interceptor"}) is True
    assert default._armed_unit({"picket"}) is False

    # 自定义口径：system prompt + 图模板都吃 objective/weapon_range，
    # 武装标签改为数据驱动（如 gunship），不再硬编码 "interceptor"
    custom = LLMPlannerV2(
        RulePlannerConfigV2(),
        prompt_context={
            "objective": "(1200,-800)",
            "weapon_range": "1500-9000",
            "force_desc": "gunship wing, range {weapon_range} m",
        },
        armed_tags=("gunship",),
    )
    assert "(1200,-800)" in custom._system_prompt
    assert "1500-9000" in custom._system_prompt
    assert custom._prompt_context["force_desc"] == "gunship wing, range 1500-9000 m"
    assert custom._armed_unit({"gunship"}) is True
    assert custom._armed_unit({"interceptor"}) is False, \
        "自定义 armed_tags 后不再按 'interceptor' 判定"

    # 图模板 format 成功且含注入口径（回归：曾因缺 objective/weapon_range 键抛 KeyError）
    from llm_planner import PLANNER_USER_TEMPLATE_GRAPH

    rendered = PLANNER_USER_TEMPLATE_GRAPH.format(
        tick=7, graph="<graph>", history="<history>",
        objective=custom._prompt_context["objective"],
        weapon_range=custom._prompt_context["weapon_range"],
        shore="(none)",
    )
    assert "(1200,-800)" in rendered and "1500-9000" in rendered
    assert "(none)" in rendered  # 无近防场景的岸基段占位


def test_contact_entity_suffix():
    from v2_executor import contact_entity_suffix

    contact = {"contact_id": "sensor.contact.defender.picket-001.intruder.wave-1-004",
               "observer_entity_id": "defender.picket-001"}
    assert contact_entity_suffix(contact) == "intruder.wave-1-004"
    weird = {"contact_id": "x.y", "observer_entity_id": "other"}
    assert contact_entity_suffix(weird) == "x.y"


def test_platform_kind_by_domain_not_id():
    from types import SimpleNamespace

    from v2_executor import platform_kind

    # 同样带 "interceptor" 标签：air 域=无人机、surface 域=无人艇——不能靠编号/标签区分
    uav = SimpleNamespace(domain="air", tags=("defence", "interceptor"))
    usv = SimpleNamespace(domain="surface", tags=("defence", "interceptor"))
    fixed = SimpleNamespace(domain="shore", tags=("defence", "fixed"))
    assert platform_kind(uav) == "uav"
    assert platform_kind(usv) == "usv"
    assert platform_kind(fixed) == "fixed"
    # 无域时标签兜底
    assert platform_kind(SimpleNamespace(domain="", tags=("raider",))) == "usv"
    assert platform_kind(SimpleNamespace(domain="", tags=("airborne",))) == "uav"


def test_edge_approach_fields_three_cases():
    from interception_graph import _edge_approach_fields

    # Case 1：射程外，高速接近 → 应提前准备拦截
    f1 = _edge_approach_fields(distance=9500.0, weapon_range=8000.0,
                               closing_speed=41.7, horizon_ticks=60, eps=1.0)
    assert f1["range_gap"] == 1500.0
    assert f1["approach_status"] == "approaching"
    assert abs(f1["time_to_weapon_range_ticks"] - 35.97) < 0.1
    assert f1["prepare_intercept"] is True

    # Case 2：射程外，正在远离 → 不提前拦截、无预计进射程时间
    f2 = _edge_approach_fields(distance=9000.0, weapon_range=8000.0,
                               closing_speed=-10.0, horizon_ticks=60, eps=1.0)
    assert f2["approach_status"] == "receding"
    assert f2["time_to_weapon_range_ticks"] is None
    assert f2["prepare_intercept"] is False

    # Case 3：已进射程 → gap=0、ttr=0，can_intercept 语义不动（由外层计算）
    f3 = _edge_approach_fields(distance=7000.0, weapon_range=8000.0,
                               closing_speed=50.0, horizon_ticks=60, eps=1.0)
    assert f3["range_gap"] == 0.0
    assert f3["time_to_weapon_range_ticks"] == 0.0
    assert f3["prepare_intercept"] is True

    # 防抖：closing 在 eps 内 → stable，不误报
    f4 = _edge_approach_fields(distance=9000.0, weapon_range=8000.0,
                               closing_speed=0.4, horizon_ticks=60, eps=1.0)
    assert f4["approach_status"] == "stable"
    assert f4["time_to_weapon_range_ticks"] is None
    assert f4["prepare_intercept"] is False


def test_graph_closing_speed_from_distance_cache():
    from types import SimpleNamespace

    from interception_graph import GraphBuilder, GraphConfig
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    builder = GraphBuilder(GraphConfig(top_k=3), weapon_policies=policies,
                           speed_by_tag={"uav": 40.0})
    meta = {"defender.interceptor-001": SimpleNamespace(
        domain="air", tags=("defence", "interceptor"),
        state=SimpleNamespace(ammunition={"ammunition.interceptor-missile@2.0.0": 2}))}

    def obs_at(x):
        return _fake_observation(
            [dict(OWN[0], position_m=(7929.0, 0.0, 800.0))],
            [dict(_contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                           x, 0.0, conf=0.9, observer="defender.interceptor-001"),
                  estimated_position_m=(float(x), 0.0, 800.0))],
        )

    g1 = builder.build(obs_at(20000.0), ROLES, meta, tick=0)
    assert g1.interceptors[0].candidates[0]["closing_speed"] is None  # 首帧无历史
    g2 = builder.build(obs_at(19500.0), ROLES, meta, tick=10)
    cand = g2.interceptors[0].candidates[0]
    assert cand["closing_speed"] == 50.0  # (12071-11571)/10
    assert cand["approach_status"] == "approaching"
    assert cand["time_to_weapon_range_ticks"] == 71.4  # gap 3571 / 50
    assert cand["prepare_intercept"] is False  # 71.4 > horizon 60
    # reset 后缓存清空，防止跨局污染
    builder.reset()
    g3 = builder.build(obs_at(19400.0), ROLES, meta, tick=0)
    assert g3.interceptors[0].candidates[0]["closing_speed"] is None


def test_graph_dedupes_tracks_and_uses_zone_boundary_distance():
    from types import SimpleNamespace

    from interception_graph import GraphBuilder, GraphConfig
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    builder = GraphBuilder(
        GraphConfig(
            top_k=3,
            protected_zone_bounds_m=(-8000.0, -8000.0, 8000.0, 8000.0),
        ),
        weapon_policies=policies,
        speed_by_tag={"uav": 40.0},
    )
    obs = _fake_observation(
        [_own("defender.interceptor-001", 7929.0, 0.0, 800.0)],
        [
            _contact("sensor.contact.defender.picket-001.intruder.wave-1-001",
                     9000.0, 0.0, conf=0.95, observer="defender.picket-001"),
            _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                     9000.0, 0.0, conf=0.80,
                     observer="defender.interceptor-001"),
        ],
    )
    meta = {"defender.interceptor-001": SimpleNamespace(
        domain="air", tags=("defence", "interceptor"),
        state=SimpleNamespace(
            ammunition={"ammunition.interceptor-missile@2.0.0": 2},
        ),
    )}
    graph = builder.build(obs, ROLES, meta, tick=0)
    assert graph.target_count == 1
    candidate = graph.interceptors[0].candidates[0]
    assert candidate["observer_count"] == 2
    assert candidate["can_intercept"] is True
    assert candidate["distance_to_zone"] == 1000.0


def test_attack_route_profiles_are_tag_and_tick_driven():
    from attack_driver import AttackProfileDriverV2

    driver = AttackProfileDriverV2.__new__(AttackProfileDriverV2)
    driver.routes = (
        {"match_tag": "diversion", "until_tick": 100, "objective_m": [0.0, 0.0]},
        {"match_tag": "diversion", "objective_m": [30000.0, 0.0]},
    )
    driver.objective_m = (0.0, 0.0)
    driver.pattern = "direct"
    driver.split_angle_deg = 0.0
    driver.serpentine_angle_deg = 0.0
    driver.serpentine_period_ticks = 1
    driver.speed_mps = 40.0
    driver.speed_cycle_mps = ()
    driver.speed_cycle_ticks = 1
    assert driver._route_for(("intruder", "diversion"), 50)["objective_m"] == [0.0, 0.0]
    assert driver._route_for(("intruder", "diversion"), 100)["objective_m"] == [30000.0, 0.0]
    assert driver._route_for(("intruder", "main"), 50) == {}


def test_deception_scenario_is_registered_and_mobile_only():
    from attack_driver import load_attack_profile_data
    from openmdbench.scenarios.formal_v2 import (
        compile_formal_scenario_v2,
        formal_scenario_registry_v2,
    )

    assert "MD-AD-004-DECEPTION" in formal_scenario_registry_v2()
    resolved, _ = compile_formal_scenario_v2("MD-AD-004-DECEPTION")
    assert not any("fixed" in set(entity.tags) for entity in resolved.entities)
    profile = load_attack_profile_data("MD-AD-004-DECEPTION")
    assert profile["protected_zone_bounds_m"] == [-8000.0, -8000.0, 8000.0, 8000.0]
    assert len(profile["attack"]["timeline"]) == 2
    assert len(profile["attack"]["routes"]) >= 6


def test_pure_llm_parse():
    from pure_llm_agent import parse_actions

    response = (
        '前缀说明\n{"actions": {'
        '"defender.interceptor-001": {"command": "navigate", '
        '"heading_deg": 270, "speed_mps": 40},'
        '"defender.picket-001": {"command": "hold"}}}'
    )
    unit_ids = {a["entity_id"] for a in OWN}
    parsed = parse_actions(response, unit_ids)
    assert parsed["defender.interceptor-001"]["command"] == "navigate"
    assert parsed["defender.picket-001"]["command"] == "hold"
    assert "defender.shore-ew" not in parsed
    assert parse_actions("抱歉，无法输出 JSON。", unit_ids) == {}
    assert parse_actions("", unit_ids) == {}


def test_executor_ammo_from_live_state():
    from types import SimpleNamespace

    from goai_protocol import GOAIBroker
    from v2_executor import ExecutorConfigV2, GOAIExecutorV2

    executor = GOAIExecutorV2(GOAIBroker(), ExecutorConfigV2(faction_id="f"))
    meta = {"u1": SimpleNamespace(
        state=SimpleNamespace(ammunition={"w1": 3}),
        definition=SimpleNamespace(runtime_initial=SimpleNamespace(
            ammunition={"w1": 12})))}
    assert executor._ammo_for(meta, "u1", "w1") == 3  # 实时状态优先
    assert executor._ammo_for(meta, "u1", "w2") is None
    # 无实时状态时回退定义初始值
    meta2 = {"u2": SimpleNamespace(
        state=SimpleNamespace(ammunition=None),
        definition=SimpleNamespace(runtime_initial=SimpleNamespace(
            ammunition={"w1": 12})))}
    assert executor._ammo_for(meta2, "u2", "w1") == 12
    # 命名空间映射：弹药键 ammunition.* 对应武器键 weapon.*
    meta3 = {"u3": SimpleNamespace(
        state=SimpleNamespace(
            ammunition={"ammunition.interceptor-missile@2.0.0": 7}),
        definition=None)}
    assert executor._ammo_for(meta3, "u3",
                              "weapon.interceptor-missile@2.0.0") == 7


def test_interception_graph_builder():
    from types import SimpleNamespace

    from interception_graph import GraphBuilder, GraphConfig
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    builder = GraphBuilder(GraphConfig(top_k=3, history_size=5),
                           weapon_policies=policies,
                           speed_by_tag={"uav": 40.0, "usv": 8.0})
    own = [
        _own("defender.interceptor-001", 7929.0, 0.0, 800.0),
        _own("defender.picket-001", 12334.0, 4995.0, 0.0),
    ]
    # 4 个候选接触：3 个在射程/近距，1 个远距；测试 Top-K 截断
    contacts = [
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                 9000.0, -500.0, conf=0.95, observer="defender.interceptor-001"),
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-002",
                 9500.0, 0.0, conf=0.9, observer="defender.interceptor-001"),
        _contact("sensor.contact.defender.picket-001.intruder.wave-1-003",
                 10000.0, 500.0, conf=0.85, observer="defender.picket-001"),
        _contact("sensor.contact.defender.picket-001.intruder.wave-1-004",
                 30000.0, 0.0, conf=0.8, observer="defender.picket-001"),
    ]
    obs = _fake_observation(own, contacts)
    meta = {
        "defender.interceptor-001": SimpleNamespace(
            domain="air", tags=("defence", "interceptor"),
            state=SimpleNamespace(ammunition={"ammunition.interceptor-missile@2.0.0": 12})),
        "defender.picket-001": SimpleNamespace(
            domain="surface", tags=("defence", "picket"),
            state=SimpleNamespace(ammunition={"ammunition.something@1.0.0": 9})),
    }
    graph = builder.build(obs, ROLES, meta, tick=0)
    # 哨戒艇不武装 → 不入图
    assert [n.id for n in graph.interceptors] == ["defender.interceptor-001"]
    node = graph.interceptors[0]
    assert node.remaining_ammunition == 12  # ammunition.* → weapon.* 映射
    # Top-K：4 个接触只保留 3 个
    assert len(node.candidates) == 3
    # 本机观测的接触 can_intercept=true；pickle 观测的接触 false
    by_target = {c["target"]: c for c in node.candidates}
    assert by_target["sensor.contact.defender.interceptor-001.intruder.wave-1-001"]["can_intercept"] is True
    assert by_target["sensor.contact.defender.picket-001.intruder.wave-1-003"]["can_intercept"] is False
    # 边属性齐全
    edge = node.candidates[0]
    for key in ("distance", "range_ratio", "eta", "can_intercept", "threat",
                "bearing", "distance_to_zone", "observed_by",
                "feasible_eta_ticks", "feasible"):
        assert key in edge, key
    # feasible：已在射程内 → feasible_eta=0；目标距禁区 9 km，拦截机先到 → true
    assert by_target["sensor.contact.defender.interceptor-001.intruder.wave-1-001"]["feasible_eta_ticks"] == 0.0
    assert by_target["sensor.contact.defender.interceptor-001.intruder.wave-1-001"]["feasible"] is True
    text = graph.format_for_prompt()
    assert "range=" in text and "ammo=12" in text and "can_intercept=true" in text
    assert "feasible_eta=" in text

    # feasible=false 用例：远拦截机（15 km）对已近禁区（500 m）的目标赶不上
    own_far = [_own("defender.interceptor-001", 15000.0, 0.0, 800.0)]
    obs2 = _fake_observation(own_far, [
        _contact("sensor.contact.defender.interceptor-001.intruder.wave-1-009",
                 500.0, 0.0, conf=0.9, observer="defender.interceptor-001"),
    ])
    graph2 = builder.build(obs2, ROLES, meta, tick=1)
    cand = graph2.interceptors[0].candidates[0]
    assert cand["feasible_eta_ticks"] > 100  # 到射程边界还要 >100 tick
    assert cand["feasible"] is False        # 目标 ~11 tick 就进禁区 → 赶不上


def test_history_buffer():
    from interception_graph import HistoryBuffer

    buf = HistoryBuffer(size=5)
    for t in range(7):
        buf.record(t, {f"I{t % 2}": f"T{t}"}, {"I0": 12 - t, "I1": 10})
    assert len(buf.entries()) == 5
    assert buf.entries()[0]["tick"] == 2  # 最旧的被挤出
    assert buf.last_assignment() == {"I0": "T6"}  # t=6 → t%2==0 → I0
    text = buf.format_for_prompt()
    assert "assignment=" in text and "ammo=" in text
    buf.reset()
    assert buf.entries() == []


def test_llm_planner_graph_prompt_and_history():
    from types import SimpleNamespace

    from interception_graph import GraphBuilder, GraphConfig
    from llm_planner import LLMPlannerV2
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    builder = GraphBuilder(GraphConfig(top_k=3, history_size=5),
                           weapon_policies=policies,
                           speed_by_tag={"uav": 40.0, "usv": 8.0})
    stub = _StubLLM([
        '{"goal_commands":[{"task_id":"intercept_001","goal_type":"intercept",'
        '"parameters":{"unit_id":"defender.interceptor-001",'
        '"target_id":"sensor.contact.defender.interceptor-001.intruder.wave-1-001"},'
        '"priority":0.9}]}',
        '{"goal_commands":[{"task_id":"intercept_002","goal_type":"intercept",'
        '"parameters":{"unit_id":"defender.interceptor-001",'
        '"target_id":"sensor.contact.defender.interceptor-001.intruder.wave-1-001"},'
        '"priority":0.9}]}',
    ])
    planner = LLMPlannerV2(RulePlannerConfigV2(), llm=stub, graph_builder=builder)
    obs = _fake_observation(
        [dict(OWN[0]), dict(OWN[3])],
        [_contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                  9000.0, -500.0, conf=0.95, observer="defender.interceptor-001")],
    )
    meta = {
        "defender.interceptor-001": SimpleNamespace(
            domain="air", tags=("defence", "interceptor"),
            state=SimpleNamespace(ammunition={"ammunition.interceptor-missile@2.0.0": 12})),
        "defender.picket-001": SimpleNamespace(
            domain="surface", tags=("defence", "picket"),
            state=SimpleNamespace(ammunition={})),
    }
    commands = planner.plan(obs, tick=0, unit_roles=ROLES, meta=meta)
    assert commands and commands[0].goal_type == "intercept"
    # 第一轮提示词为三段式：Interception Graph + Previous Decision
    assert "Interception Graph" in stub.prompts[0][1]
    assert "Previous Decision" in stub.prompts[0][1]
    # 决策已写入 History
    entries = builder.history.entries()
    assert entries and entries[-1]["tick"] == 0
    assert entries[-1]["assignments"]["defender.interceptor-001"].startswith(
        "sensor.contact.")
    # 第二轮：提示词应包含上一轮分配（Previous Decision 内容）
    planner.plan(obs, tick=30, unit_roles=ROLES, meta=meta)
    assert "tick 0:" in stub.prompts[1][1]
    assert builder.history.entries()[-1]["tick"] == 30


def test_pure_llm_history_and_feedback_prompt():
    from types import SimpleNamespace

    from pure_llm_agent import PureLLMAgentV2
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    agent = PureLLMAgentV2(faction_id="coalition.defender", llm=None,
                           weapon_policies=policies)
    meta = {
        "defender.interceptor-001": SimpleNamespace(
            domain="air", tags=("defence", "interceptor"),
            state=SimpleNamespace(ammunition={"ammunition.interceptor-missile@2.0.0": 12})),
        "defender.picket-001": SimpleNamespace(
            domain="surface", tags=("defence", "picket"),
            state=SimpleNamespace(ammunition={})),
    }
    obs = _fake_observation(
        [dict(OWN[0]), dict(OWN[3])],
        [_contact("sensor.contact.defender.picket-001.intruder.wave-1-001",
                  9000.0, -500.0, conf=0.95, observer="defender.picket-001")],
    )
    prompt = agent._build_prompt(
        obs, 10, ROLES, meta,
        history_text=agent.history.format_for_prompt(),
        feedback_text="defender.interceptor-001 -> intruder.wave-1-001: no-ammunition",
    )
    # 修复点 3：bearing/ETA 字段真正传入
    assert "bearing_deg=" in prompt and "estimated_eta_ticks=" in prompt
    # 历史与反馈段落
    assert "Previous Decision" in prompt
    assert "Command feedback from last cycle" in prompt
    assert "no-ammunition" in prompt
    # 历史记录与格式化（纯信息，无约束）
    agent.history.record(10, {"defender.interceptor-001": "fire(wave-1-001)"},
                         {"defender.interceptor-001": 12})
    assert agent.history.entries()[-1]["tick"] == 10
    assert "fire(wave-1-001)" in agent.history.format_for_prompt()


def test_fire_policy_is_shared_action_space():
    """fire_policy 对等性：规则侧确定性下发、LLM 侧自由下发、执行层同一门控。"""
    from v2_executor import ExecutorConfigV2, GOAIExecutorV2, WeaponPolicyV2

    # 1) 规则侧默认 = salvo（恢复基线历史语义：每目标连发 2 发）
    planner = RulePlannerV2(RulePlannerConfigV2())
    commands = planner.plan(_fake_observation(OWN, CONTACTS), tick=5,
                            unit_roles=ROLES)
    intercepts = [c for c in commands if c.goal_type == "intercept"]
    assert intercepts, "应有拦截目标"
    assert all(c.parameters.get("fire_policy") == "salvo" for c in intercepts)

    # 2) 规则侧确定性映射：ETA ≤ 阈值的目标改用紧急教义
    near = [dict(CONTACTS[0], contact_id="near",
                 estimated_position_m=(500.0, 0.0, 100.0)),
            dict(CONTACTS[1], contact_id="far",
                 estimated_position_m=(30000.0, 0.0, 100.0))]
    mapped = RulePlannerV2(RulePlannerConfigV2(
        fire_policy="assess", fire_policy_urgent="salvo",
        fire_policy_urgent_eta_ticks=240, intruder_speed_mps=45.0))
    mapped_cmds = mapped.plan(_fake_observation(OWN, near), tick=5,
                              unit_roles=ROLES)
    by_target = {str(c.parameters.get("target_id")): c.parameters.get("fire_policy")
                 for c in mapped_cmds if c.goal_type == "intercept"}
    assert by_target.get("near") == "salvo", by_target
    assert by_target.get("far") == "assess", by_target

    # 3) 不下发参数（None）→ 由执行层默认教义决定
    silent = RulePlannerV2(RulePlannerConfigV2(fire_policy=None))
    silent_cmds = silent.plan(_fake_observation(OWN, CONTACTS), tick=5,
                              unit_roles=ROLES)
    assert all("fire_policy" not in c.parameters
               for c in silent_cmds if c.goal_type == "intercept")

    # 4) 执行层：goal 参数优先；缺省（空串）→ 回退 config.fire_doctrine
    policy = WeaponPolicyV2(selector_tags=("interceptor",),
                            weapon_ref="weapon.interceptor-missile@2.0.0",
                            minimum_range_m=500.0, maximum_range_m=8000.0,
                            cooldown_ticks=5)
    executor = GOAIExecutorV2(GOAIBroker(), ExecutorConfigV2(
        faction_id="coalition.defender", weapon_policies=(policy,),
        fire_doctrine="salvo"))
    assert executor._doctrine_allows(unit_id="u", target_entity="t", tick=10,
                                     policy=policy, meta_entity=None,
                                     distance=1000.0, fire_policy="") is True
    executor._record_shot("u", "t", 10, policy)
    assert executor._doctrine_allows(unit_id="u", target_entity="t", tick=15,
                                     policy=policy, meta_entity=None,
                                     distance=1000.0, fire_policy="") is True
    executor._record_shot("u", "t", 15, policy)
    assert executor._doctrine_allows(unit_id="u", target_entity="t", tick=20,
                                     policy=policy, meta_entity=None,
                                     distance=1000.0, fire_policy="") is False
    # goal 显式 assess：单发后窗口内不补射（即使 config 默认是 salvo）
    assert executor._doctrine_allows(unit_id="v", target_entity="t2", tick=10,
                                     policy=policy, meta_entity=None,
                                     distance=1000.0, fire_policy="assess") is True
    executor._record_shot("v", "t2", 10, policy)
    assert executor._doctrine_allows(unit_id="v", target_entity="t2", tick=12,
                                     policy=policy, meta_entity=None,
                                     distance=1000.0, fire_policy="assess") is False


def test_lower_layer_tactical_primitives():
    """下层战术原语：新目标类型、提前交点、开火教义、目标速度估计。"""
    from goai_protocol import GOAL_TYPES
    from v2_executor import ExecutorConfigV2, GOAIExecutorV2, WeaponPolicyV2
    from goai_protocol import GOAIBroker

    for goal in ("barrier", "ambush", "reserve", "disengage"):
        assert goal in GOAL_TYPES, goal

    policy = WeaponPolicyV2(selector_tags=("interceptor",),
                            weapon_ref="weapon.interceptor-missile@2.0.0",
                            minimum_range_m=500.0, maximum_range_m=8000.0,
                            cooldown_ticks=5)
    ex = GOAIExecutorV2(GOAIBroker(), ExecutorConfigV2(
        faction_id="coalition.defender", weapon_policies=(policy,)))

    # 提前交点：目标向东 40 m/tick，本机在原点 → 交点必须落在目标当前位置之前方
    lead = ex._lead_point((0.0, 0.0, 800.0), (10000.0, 0.0, 100.0),
                          (40.0, 0.0, 0.0), 40.0)
    assert lead[0] > 10000.0, lead
    # 无速度历史 → 退化为当前位置（不产生虚假提前量）
    fallback = ex._lead_point((0.0, 0.0, 800.0), (10000.0, 0.0, 100.0), None, 40.0)
    assert fallback[0] == 10000.0

    # 目标速度估计：两次观测差分
    ex._target_velocity("intruder.t", (1000.0, 0.0, 100.0), 10)
    velocity = ex._target_velocity("intruder.t", (1040.0, 0.0, 100.0), 11)
    assert velocity is not None and abs(velocity[0] - 40.0) < 1e-6, velocity

    # 开火教义 assess：单发后进入评估窗口，窗口内不补射，窗口过后可补射
    ex._engaged_targets = {}
    assert ex._doctrine_allows(unit_id="u1", target_entity="intruder.t", tick=100,
                               policy=policy, meta_entity=None, distance=1000.0,
                               fire_policy="assess") is True
    ex._record_shot("u1", "intruder.t", 100, policy)
    window = max(policy.cooldown_ticks, ex.config.assess_window_ticks)
    assert ex._doctrine_allows(unit_id="u1", target_entity="intruder.t", tick=105,
                               policy=policy, meta_entity=None, distance=1000.0,
                               fire_policy="assess") is False
    assert ex._doctrine_allows(unit_id="u1", target_entity="intruder.t",
                               tick=100 + window + 1, policy=policy,
                               meta_entity=None, distance=1000.0,
                               fire_policy="assess") is True
    # salvo：最多连发 2 发
    ex2 = GOAIExecutorV2(GOAIBroker(), ExecutorConfigV2(
        faction_id="coalition.defender", weapon_policies=(policy,)))
    assert ex2._doctrine_allows(unit_id="u1", target_entity="t", tick=10,
                                policy=policy, meta_entity=None, distance=1000.0,
                                fire_policy="salvo") is True
    ex2._record_shot("u1", "t", 10, policy)
    ex2._record_shot("u1", "t", 15, policy)
    assert ex2._doctrine_allows(unit_id="u1", target_entity="t", tick=20,
                                policy=policy, meta_entity=None, distance=1000.0,
                                fire_policy="salvo") is False


def test_shared_frontend_parity_and_direct_actions():
    from run_episode import _build_defender

    profile = {
        "objective_m": [1200, -800],
        "protected_zone_bounds_m": [-1000, -1000, 2000, 2000],
        "attack": {"speed_mps": 42, "timeline": []},
        "defence": {
            "faction_id": "coalition.defender",
            "weapon_policies": [{
                "selector_tags": ["interceptor"],
                "weapon_ref": "weapon.interceptor-missile@2.0.0",
                "minimum_range_m": 500, "maximum_range_m": 8000,
                "cooldown_ticks": 5,
            }],
        },
    }
    args = dict(plan_interval=10, llm_base_url=None, llm_model=None,
                llm_max_tokens=768, frontend="graph")
    hybrid = _build_defender(profile, SimpleNamespace(planner="llm", **args))
    pure = _build_defender(profile, SimpleNamespace(planner="pure-llm", **args))
    assert pure.graph_builder.config == hybrid.planner.graph_builder.config
    assert pure.graph_builder is not hybrid.planner.graph_builder
    assert pure.max_tokens == hybrid.planner.max_tokens == 768
    assert not hasattr(pure, "executor") and not hasattr(pure, "broker")
    obs = _fake_observation(OWN, CONTACTS)
    pg = pure.graph_builder.build(obs, ROLES, {}, 0)
    hg = hybrid.planner.graph_builder.build(obs, ROLES, {}, 0)
    assert pg.to_dict() == hg.to_dict()
    prompt = pure._build_prompt(obs, 0, ROLES, {}, graph=pg)
    assert pg.format_for_prompt() in prompt
    assert pg.format_shore_for_prompt() in prompt
    assert "defender.picket-001" in prompt and "speed_limit_mps=" in prompt
    assert '"actions"' in prompt and '"goal_commands"' not in prompt

    # Exercise one decision through the actual controller with harmless holds.
    import json
    pure.llm = _StubLLM([json.dumps({"actions": {
        item["entity_id"]: {"command": "hold"} for item in OWN
    }})])
    world = SimpleNamespace(
        tick=0, authority_tokens={},
        observation=lambda **kwargs: obs, entities_stable=lambda: (),
    )
    pure(SimpleNamespace(world_view=world))
    assert pure.graph_builder.history.entries()[-1]["tick"] == 0
    assert pure.llm_calls == 1 and pure.fallback_count == 0
    raw = _build_defender(profile, SimpleNamespace(
        planner="pure-llm", **dict(args, frontend="raw")))
    assert raw.graph_builder is None and not raw.include_graph


def test_pure_llm_frontend_toggle():
    """前置模块开关（对照实验）：graph=结构化拦截图+时间线；raw=仅原始态势报告。"""
    from pure_llm_agent import PureLLMAgentV2

    obs = _fake_observation(OWN, CONTACTS)
    stub_graph_builder = object()  # 只需非 None：include_graph 自动为 True

    with_graph = PureLLMAgentV2(faction_id="coalition.defender",
                                graph_builder=stub_graph_builder)
    assert with_graph.include_graph is True
    prompt_graph = with_graph._build_prompt(
        obs, 10, ROLES, {}, graph=None,
        history_text="(none yet)", feedback_text="(none)")
    assert "Interception Graph" in prompt_graph
    assert "Scheduled attack timeline" in prompt_graph

    raw_only = PureLLMAgentV2(faction_id="coalition.defender")
    assert raw_only.include_graph is False
    prompt_raw = raw_only._build_prompt(
        obs, 10, ROLES, {}, graph=None,
        history_text="(none yet)", feedback_text="(none)")
    assert "Interception Graph" not in prompt_raw
    assert "Scheduled attack timeline" not in prompt_raw
    assert "Detected contacts" in prompt_raw
    assert '"actions"' in prompt_raw  # 低层命令 schema 保持不变

    # 显式关闭：即使传了 graph_builder 也不注入前置模块
    forced_raw = PureLLMAgentV2(faction_id="coalition.defender",
                                graph_builder=stub_graph_builder,
                                include_graph=False)
    assert forced_raw.include_graph is False


def test_pure_llm_scenario_prompt_context():
    """场景泛化：prompt_context 注入保护区/射程，接触表按 objective_xy 计算。"""
    from pure_llm_agent import PureLLMAgentV2
    from v2_executor import WeaponPolicyV2

    default = PureLLMAgentV2(faction_id="coalition.defender")
    assert "(0,0)" in default._system_prompt
    assert "500-8000" in default._system_prompt

    policies = (WeaponPolicyV2(selector_tags=("gunship",),
                               weapon_ref="weapon.gun@2.0.0",
                               minimum_range_m=1000.0, maximum_range_m=6000.0,
                               cooldown_ticks=5),)
    agent = PureLLMAgentV2(
        faction_id="coalition.defender", llm=None, weapon_policies=policies,
        prompt_context={
            "objective": "(1200,-800)",
            "objective_xy": (1200.0, -800.0),
            "weapon_range": "1000-6000",
        },
    )
    assert "(1200,-800)" in agent._system_prompt
    assert "1000-6000" in agent._system_prompt
    assert agent._objective_xy == (1200.0, -800.0)
    # 接触 (1200, 200) 相对保护区 (1200,-800) 距离应为 1000 m（不再假设原点）
    obs = _fake_observation(
        [dict(OWN[0])],
        [_contact("sensor.contact.defender.interceptor-001.intruder.wave-1-001",
                  1200.0, 200.0, observer="defender.interceptor-001")],
    )
    prompt = agent._build_prompt(obs, 10, ROLES, {}, history_text="x",
                                 feedback_text="y")
    assert "distance_to_zone_m=1000" in prompt


def test_pure_llm_smoke():
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    from attack_driver import AttackProfileDriverV2, load_attack_profile_data
    from pure_llm_agent import PureLLMAgentV2
    from v2_executor import WeaponPolicyV2

    scenario = "MD-AD-002-EASY"
    profile = load_attack_profile_data(scenario)
    defence = profile["defence"]
    policies = tuple(
        WeaponPolicyV2(
            selector_tags=tuple(str(t) for t in p.get("selector_tags", ())),
            weapon_ref=str(p["weapon_ref"]),
            minimum_range_m=float(p["minimum_range_m"]),
            maximum_range_m=float(p["maximum_range_m"]),
            cooldown_ticks=int(p["cooldown_ticks"]),
        )
        for p in defence.get("weapon_policies", ())
    )
    # interceptor-002 速度 100 > 上限 45 → 应被掩码截断；fixed 岸基不发命令
    action_json = (
        '{"actions": {'
        '"defender.interceptor-001": {"command": "navigate", "heading_deg": 270, "speed_mps": 40},'
        '"defender.interceptor-002": {"command": "navigate", "heading_deg": 270, "speed_mps": 100},'
        '"defender.interceptor-003": {"command": "hold"},'
        '"defender.picket-001": {"command": "hold"},'
        '"defender.picket-002": {"command": "navigate", "heading_deg": 90, "speed_mps": 8}}}'
    )
    stub = _StubLLM([action_json] * 6)
    session = create_formal_session_v2(scenario, session_id="eval.purellm.smoke",
                                       seed=7)
    attack = AttackProfileDriverV2(scenario, seed=7)
    agent = PureLLMAgentV2(faction_id=str(defence["faction_id"]), llm=stub,
                           weapon_policies=policies, call_interval=1)
    session.load().start()
    try:
        for _ in range(5):
            tick = session.world_view.tick
            attack(session)
            agent(session)
            session.step(operation_id=f"purellm.tick.{tick}", expected_tick=tick)
        assert session.world_view.tick == 5
        stats = agent.get_stats()
        assert stats["submitted_batches"] > 0
        assert stats["llm_calls"] == 5
        assert stats["masked_count"] >= 5, "超速命令应被逐 tick 截断"
    finally:
        session.stop().close()


# ---------------------------------------------------------------------------
# V2 引擎冒烟（Linux 原生文件系统 + PYTHONPATH）
# ---------------------------------------------------------------------------

def test_fire_receipt_counting():
    """开火计数以引擎回执为准：status=executed 才计数，rejected/no-receipt 不计。"""
    from run_episode import _executed_fire_statuses

    fires = [
        {"tick": 400, "entity_id": "u1", "contact_id": "c1",
         "weapon_ref": "w1", "action_id": "fire.a"},
        {"tick": 400, "entity_id": "u2", "contact_id": "c2",
         "weapon_ref": "w1", "action_id": "fire.b"},
        {"tick": 400, "entity_id": "u3", "contact_id": "c3",
         "weapon_ref": "w1", "action_id": "fire.c"},
    ]
    receipt = SimpleNamespace(child_receipts=(
        SimpleNamespace(child_id="fire.a", kind="discrete", status="executed"),
        SimpleNamespace(child_id="fire.b", kind="discrete", status="rejected",
                        error_code="no-ammunition"),
        SimpleNamespace(child_id="other", kind="persistent", status="active"),
    ))
    verdicts = _executed_fire_statuses(fires, receipt)
    assert sum(v["executed"] for v in verdicts) == 1
    by_status = {v["status"]: v for v in verdicts}
    assert by_status["executed"]["entity_id"] == "u1"
    assert by_status["rejected"]["entity_id"] == "u2"
    assert by_status["no-receipt"]["entity_id"] == "u3"
    assert by_status["no-receipt"]["executed"] is False


def test_shore_defence_decisions():
    """岸基自动近防决策：射程内自持接触开火；无 token/无武器/超龄不开火。"""
    from types import SimpleNamespace

    from goai_protocol import GOAIBroker
    from v2_executor import ExecutorConfigV2, GOAIExecutorV2

    weapon_binding = SimpleNamespace(
        exact_ref="weapon.shore-ciws@2.0.0",
        normalized_content={"min_range_m": 300.0, "max_range_m": 2000.0,
                            "cooldown_ticks": 1},
    )
    shore_meta = SimpleNamespace(
        tags=("defence", "fixed", "early-warning"),
        definition=SimpleNamespace(
            resource_bindings={"weapons": (weapon_binding,)}),
        state=SimpleNamespace(
            ammunition={"ammunition.shore-ciws@2.0.0": 12}),
    )
    own = {"defender.shore-ew": _own("defender.shore-ew", -1057.0, 222.0, 0.0)}
    meta = {"defender.shore-ew": shore_meta}
    contacts = {
        "c1": _contact("sensor.contact.defender.shore-ew.intruder.wave-1-001",
                       500.0, 222.0, conf=0.9, age=2,
                       observer="defender.shore-ew"),
        "c2": _contact("sensor.contact.defender.shore-ew.intruder.wave-1-002",
                       5000.0, 0.0, age=1, observer="defender.shore-ew"),
    }
    executor = GOAIExecutorV2(GOAIBroker(), ExecutorConfigV2(
        faction_id="coalition.defender", weapon_policies=()))
    submitted = []
    fake = SimpleNamespace(session_id="s",
                           submit_actions=lambda **kw: submitted.append(kw))
    tokens = {"defender.shore-ew": "tok-shore"}
    fires = executor._shore_defence(fake, 400, own, contacts, tokens, meta)
    assert len(fires) == 1
    assert fires[0]["entity_id"] == "defender.shore-ew"
    assert fires[0]["contact_id"] == "sensor.contact.defender.shore-ew.intruder.wave-1-001"  # 最近且射程内的自持接触
    assert len(submitted) == 1
    # 冷却已过（cooldown=1）→ 下一 tick 可再发；无 token → 跳过
    assert len(executor._shore_defence(fake, 401, own, contacts, tokens, meta)) == 1
    assert executor._shore_defence(fake, 402, own, contacts, {}, meta) == []
    # 弹药耗尽 → 不开火
    depleted = SimpleNamespace(
        tags=("defence", "fixed", "early-warning"),
        definition=SimpleNamespace(
            resource_bindings={"weapons": (weapon_binding,)}),
        state=SimpleNamespace(
            ammunition={"ammunition.shore-ciws@2.0.0": 0}),
    )
    assert executor._shore_defence(
        fake, 403, own, contacts, tokens,
        {"defender.shore-ew": depleted}) == []


def test_graph_shore_section():
    """图内岸基近防段：有近防设施时列出威胁；无近防场景返回 (none)。"""
    from types import SimpleNamespace

    from interception_graph import GraphBuilder, GraphConfig
    from v2_executor import WeaponPolicyV2

    policies = (WeaponPolicyV2(selector_tags=("interceptor",),
                               weapon_ref="weapon.interceptor-missile@2.0.0",
                               minimum_range_m=500.0, maximum_range_m=8000.0,
                               cooldown_ticks=5),)
    builder = GraphBuilder(GraphConfig(), weapon_policies=policies,
                           speed_by_tag={"uav": 40.0})
    binding = SimpleNamespace(
        exact_ref="weapon.shore-ciws@2.0.0",
        normalized_content={"min_range_m": 300.0, "max_range_m": 2000.0,
                            "cooldown_ticks": 1})
    shore_meta = SimpleNamespace(
        domain="land", tags=("defence", "fixed", "early-warning"),
        definition=SimpleNamespace(resource_bindings={"weapons": (binding,)}),
        state=SimpleNamespace(
            ammunition={"ammunition.shore-ciws@2.0.0": 12}))
    uav_meta = SimpleNamespace(
        domain="air", tags=("defence", "interceptor"),
        definition=SimpleNamespace(resource_bindings={}),
        state=SimpleNamespace(
            ammunition={"ammunition.interceptor-missile@2.0.0": 12}))
    obs = _fake_observation(
        [_own("defender.shore-ew", -1057.0, 222.0, 0.0),
         _own("defender.interceptor-001", 7929.0, 0.0, 800.0)],
        [_contact("sensor.contact.defender.shore-ew.intruder.wave-1-001",
                  500.0, 222.0, conf=0.9, age=2,
                  observer="defender.shore-ew")],
    )
    roles = {"defender.shore-ew": frozenset({"defence", "fixed", "early-warning"}),
             "defender.interceptor-001": frozenset({"defence", "interceptor"})}
    meta = {"defender.shore-ew": shore_meta,
            "defender.interceptor-001": uav_meta}
    graph = builder.build(obs, roles, meta, tick=100)
    assert [site.id for site in graph.shore_sites] == ["defender.shore-ew"]
    site = graph.shore_sites[0]
    assert site.remaining_ammunition == 12
    assert len(site.threats) == 1
    text = graph.format_shore_for_prompt()
    assert "defender.shore-ew" in text and "ammo=12" in text
    assert "dist=" in text
    # 无近防场景 → 空 + (none)
    empty = builder.build(
        _fake_observation([dict(OWN[0])], []), ROLES,
        {"defender.interceptor-001": uav_meta}, tick=101)
    assert empty.shore_sites == []
    assert empty.format_shore_for_prompt() == "(none)"


def test_v2_engine_smoke():
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    from attack_driver import AttackProfileDriverV2, load_attack_profile_data
    from run_episode import _build_defender

    scenario = "MD-AD-002-EASY"
    profile = load_attack_profile_data(scenario)
    args = SimpleNamespace(planner="rule", plan_interval=5,
                           llm_base_url=None, llm_model=None,
                           llm_max_tokens=1024)
    session = create_formal_session_v2(scenario, session_id="eval.selftest",
                                       seed=7)
    attack = AttackProfileDriverV2(scenario, seed=7)
    defender = _build_defender(profile, args)
    session.load().start()
    try:
        for _ in range(60):
            tick = session.world_view.tick
            attack(session)
            defender(session)
            session.step(operation_id=f"eval.selftest.tick.{tick}",
                         expected_tick=tick)
        assert session.world_view.tick == 60
        stats = defender.get_stats()
        assert stats["submitted_batches"] > 0, "执行层应提交过动作批"
        mission = session.world_view.checkpoint().mission_scoring_checkpoint
        assert mission is not None
        score_state = mission.get("score_state", {})
        assert isinstance(score_state, dict)
    finally:
        session.stop().close()


def main() -> int:
    tests = [
        test_broker_accept_and_reject,
        test_broker_supersede_and_negotiation,
        test_rule_planner_goals,
        test_rule_planner_low_energy_return,
        test_rule_planner_policy_driven_weapon_units,
        test_llm_planner_parses_and_falls_back,
        test_llm_planner_resolves_abbreviated_contact_ids,
        test_llm_planner_remaps_intercept_to_armed_observer,
        test_llm_planner_scenario_prompt_context,
        test_contact_entity_suffix,
        test_platform_kind_by_domain_not_id,
        test_executor_ammo_from_live_state,
        test_interception_graph_builder,
        test_history_buffer,
        test_llm_planner_graph_prompt_and_history,
        test_edge_approach_fields_three_cases,
        test_graph_closing_speed_from_distance_cache,
        test_graph_dedupes_tracks_and_uses_zone_boundary_distance,
        test_attack_route_profiles_are_tag_and_tick_driven,
        test_deception_scenario_is_registered_and_mobile_only,
        test_pure_llm_history_and_feedback_prompt,
        test_lower_layer_tactical_primitives,
        test_fire_policy_is_shared_action_space,
        test_pure_llm_frontend_toggle,
        test_shared_frontend_parity_and_direct_actions,
        test_pure_llm_scenario_prompt_context,
        test_pure_llm_parse,
        test_pure_llm_smoke,
        test_fire_receipt_counting,
        test_shore_defence_decisions,
        test_graph_shore_section,
        test_v2_engine_smoke,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}", flush=True)
        except Exception as error:  # noqa: BLE001
            failed += 1
            print(f"FAIL {test.__name__}: {type(error).__name__}: {error}",
                  flush=True)
            # 定位用：打印失败断言所在行（此前只有异常类型，无法定位）
            tb = traceback.extract_tb(error.__traceback__)
            if tb:
                frame = tb[-1]
                print(f"     at {frame.filename}:{frame.lineno} "
                      f"| {frame.line}", flush=True)
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
