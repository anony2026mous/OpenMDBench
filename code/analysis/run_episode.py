"""W1 端到端跑局：MD-AD-002-EASY（防守方 = rule planner / LLM planner / 纯 LLM；突防方 = 脚本驱动）。
只读引擎、只新增文件：本脚本组合 eval 族（AgentV2 + RulePlannerV2/LLMPlannerV2 +
GOAIExecutorV2 + AttackProfileDriverV2）推进正式 V2 会话。
特性：
- 逐 tick 终局检测（step 回执 mission_receipts 里出现 terminal_result 立即终止）；
- 看门狗：--step-timeout 单 tick 超时中止 / --wall-limit 整局墙钟上限中止
  （异常时可中止程序，且中止前保存部分结果与过程日志）；
- 过程日志：每次运行写 JSONL（开火/规划周期/评分/看门狗/异常/终局），--log 指定
  路径，默认写到 ~/eval_w1_runs/logs/；
- 阵营标注按实体定义域（defender/intruder 观察集），不依赖实体编号前缀。
运行（Linux 原生文件系统、仓库根目录）：
    PYTHONPATH=$PWD MPLCONFIGDIR=/tmp/openmdbench-mpl .venv/bin/python \
      ../eval_w1/run_episode.py --planner rule --max-ticks 1800 --seed 7
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections.abc import Mapping

# ---------------------------------------------------------------------------
# Self-locating engine root (do NOT rely on an externally supplied PYTHONPATH).
#
# This file previously had *no* sys.path setup, so which engine tree got imported
# depended entirely on the caller's PYTHONPATH.  The venv carries an editable
# install whose .pth points at a DIFFERENT checkout
# (``C:\Code\source-code\source_codes`` -- 9 scenarios, no IE set).  Any command
# that forgot PYTHONPATH therefore silently imported that stale tree and failed
# with "unknown formal V2 scenario: 'IE-01-SINGLE-TARGET' (registry has 9
# entries)" -- which is exactly what broke the trainer's scorecard evaluation.
# ---------------------------------------------------------------------------
_EVAL_DIR = Path(__file__).resolve().parent
_ENGINE_DEFAULT = _EVAL_DIR.parents[1] / "source-code" / "source_codes"
ENGINE_ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
for _candidate in (str(_EVAL_DIR), str(ENGINE_ROOT)):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from openmdbench.sessions.formal_v2 import create_formal_session_v2
from attack_driver import AttackProfileDriverV2, load_attack_profile_data
from rule_planner import RulePlannerConfigV2, RulePlannerV2
from strategy_metrics import (
    LOST_STATES,
    UnitState,
    classify_role,
    compute_scorecard,
    format_scorecard_line,
)
from v2_agent import AgentV2
from v2_executor import ExecutorConfigV2, WeaponPolicyV2


def _verify_engine_tree() -> None:
    """Fail loudly if ``openmdbench`` resolved outside the intended tree.

    A silently wrong engine tree produces "unknown scenario" errors that look
    like a typo, so the mismatch is turned into an explicit, actionable message.
    """
    import openmdbench
    resolved = Path(openmdbench.__file__).resolve().parent
    expected = (ENGINE_ROOT / "openmdbench").resolve()
    if resolved != expected:
        raise SystemExit(
            "!! 加载了错误的引擎树：\n"
            f"   openmdbench 实际来自 {resolved}\n"
            f"   期望来自           {expected}\n"
            f"   场景注册表随之读到 {(resolved.parent / 'scenarios' / 'formal' / 'registry.yaml')}\n"
            "   请设置 OPENMDBENCH_ROOT 指向正确的引擎根，或清理 venv 里指向旧树的 "
            "editable .pth。")


_verify_engine_tree()


def _contact_suffix(contact_id, known_ids=()) -> str:
    """从接触 id 还原底层实体 id。

    接触 id 形如 ``sensor.contact.<observer_entity_id>.<target_entity_id>``，而实体 id
    自带点（``defender.uav-01``），所以不能按第一个点切分。

    这里优先用**活体实体 id 集合**做最长后缀匹配，而不是硬编码阵营前缀：
    原先只认 ``intruder.`` / ``defender.`` / ``facility.``，一旦场景加入第三个阵营
    （如中立民用 ``civilian.ship-01``），目标归因就会整体失败成 ``unknown``，
    "谁把火力花在民用船上"这条 ROE 证据随之丢失。平台规则也明确禁止固定阵营分支。
    """
    text = str(contact_id or "")
    best = ""
    for entity_id in known_ids:
        candidate = str(entity_id)
        if candidate and text.endswith(candidate) and len(candidate) > len(best):
            best = candidate
    if best:
        return best
    # 回退：没有实体集合可查时，仍按"最后一段像实体 id"的启发式切分。
    parts = text.split(".")
    for index in range(1, len(parts)):
        candidate = ".".join(parts[index:])
        if "." in candidate:
            return candidate
    return text


def _entity_role(session, contact_id, known_ids=()) -> str:
    suffix = _contact_suffix(contact_id, known_ids)
    entity = next(
        (item for item in session.world_view.entities_stable() if item.id == suffix),
        None,
    )
    if entity is None:
        return "unknown"
    domain = str(getattr(entity, "domain", "") or "")
    tags = tuple(str(tag) for tag in (getattr(entity, "tags", ()) or ()))
    return classify_role(domain, tags)


def _fire_record(verdict, tick: int, side: str, faction: str,
                 target_role: str, target: str = "") -> Dict[str, Any]:
    return {
        "tick": int(verdict.get("tick") or tick),
        "side": side,
        "side_faction": faction,
        "shooter": str(verdict.get("entity_id") or ""),
        "weapon": str(verdict.get("weapon_ref") or ""),
        "contact_id": str(verdict.get("contact_id") or ""),
        "target": target or _contact_suffix(verdict.get("contact_id")),
        "target_role": target_role,
    }


def _facility_weights(profile_data: Dict[str, Any], units) -> list:
    """保护目标清单（含权重）：权重取自 agents.yaml 的 facility_weights。"""
    weights = dict(profile_data.get("facility_weights") or {})
    rows = []
    for unit in units.values():
        if unit.role != "facility":
            continue
        rows.append({
            "id": unit.entity_id,
            "position_m": list(unit.position_m),
            "weight": float(weights.get(unit.entity_id, 1.0)),
        })
    return sorted(rows, key=lambda row: row["id"])

def _armed_intruder_tags(profile_data: Dict[str, Any]) -> set:
    """tags that carry a weapon, read from the declared weapon bindings."""
    tags = set()
    for wp in ((profile_data.get("attack") or {}).get("weapon_policies") or ()):
        if isinstance(wp, dict):
            mt = str(wp.get("match_tag") or "")
            if mt and int(wp.get("shots") or 0) > 0:
                tags.add(mt)
    return tags


def _build_roe_notes(profile_data: Dict[str, Any], *,
                     briefing: str = "withheld") -> str:
    """Threat-classification / ROE guidance for the LLM planner.

    修了两个问题（2026-09-27）：

    1. **文本子串匹配会误分类。** 旧实现对 ``f"{label} {behavior}".lower()`` 做
       ``"decoy" in blob`` 判定。IE-11 真正主攻那条的 behavior 恰好写着
       "after the decoys have already drawn attention"，于是 **4 架有武器的主攻 UAV
       被判为非威胁**，提示词里出现 "real air package ... declared NON-THREAT ...
       do NOT intercept or fire at it"。现在改为按**声明的武器装订**分类
       （``attack.weapon_policies``）：没有武器装订的波次才是诱饵/非威胁。
       分类不再依赖任何自然语言措辞。

    2. **未来真值泄漏。** 旧实现把每波的 ``spawn_tick / count / axis / behavior``
       原样写进提示词，而 defender 在 tick 0 的观测接触数为 0 —— 等于把敌方作战计划
       提前交给 LLM，且规则规划器与 RL 执行层拿不到同一文本（对照不对等）。
       现在默认 ``briefing="withheld"``：**只给聚合事实**（武装来袭者总数、
       已声明诱饵数、中立民用数），不给波次时刻/方位/意图。
       ``briefing="declared"`` 保留旧行为，仅用于复现历史读数。

    ``withheld`` 下 LLM 仍然知道"存在诱饵"这一事实（否则会退回历史上那个失效状态：
    混合组把弹药全花在诱饵上），但**必须自己从实时观测里分辨哪个是哪个**。
    """
    attack = profile_data.get("attack") or {}
    timeline = tuple(attack.get("timeline") or ())
    armed_tags = _armed_intruder_tags(profile_data)
    non_threat_tokens = ("decoy", "feint", "diversion", "civilian")

    lines: List[str] = []

    # ---- 敌方兵力情报：仅诊断档给出，主表口径完全不给 ----
    #
    # 为什么主表不能给：实测确认 `"armed vs decoy"` **不是观测字段**
    # （Observation 只有位置/置信度/观测者/标签），所以"有几架武装、几架诱饵"
    # 无法从观测推导，只能来自场景声明；而 rule-rule 与 rl 两臂从不读取该声明。
    # 一旦给出就是特权信息，对照不再公平 —— 与措辞无关。
    if briefing in ("aggregate", "declared"):
        armed_uavs = armed_boats = decoys = 0
        for item in timeline:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", item.get("role", "wave")))
            behavior = str(item.get("behavior", "") or "")
            count = int(item.get("count") or 0)
            blob = f"{label} {behavior}".lower()
            declared_non_threat = any(t in blob for t in non_threat_tokens)
            carries_weapon = bool(armed_tags) and any(t in blob for t in armed_tags)
            if declared_non_threat and not carries_weapon:
                decoys += count
            elif carries_weapon:
                if "boat" in blob or "usv" in blob:
                    armed_boats += count
                else:
                    armed_uavs += count
            else:
                decoys += count
        lines.append(
            f"  * [aggregate briefing] Enemy order of battle: "
            f"{armed_uavs + armed_boats} armed intruder platforms "
            f"({armed_uavs} air, {armed_boats} surface) across all waves.")
        if decoys:
            lines.append(
                f"  * [aggregate briefing] {decoys} additional intruder platform(s) are "
                "UNARMED decoys/feints. Identify which contacts are armed from what "
                "you observe.")

    civ = profile_data.get("civilian_lane") or {}
    civ_n = int(civ.get("count") or 0) if isinstance(civ, dict) else 0
    if civ_n:
        lines.append(
            f"  * {civ_n} neutral civilian platform(s) share the area. The engine "
            "enforces ROE: firing on a civilian contact is a violation. Treat any "
            "contact the engine has not classified as hostile as non-engageable.")

    lines.append(
        "  * Engage hostile contacts as soon as the graph shows can_intercept=true or "
        "prepare_intercept=true; do not hold fire waiting for a wave you have not seen.")

    # ---- 未来波次简报：仅 declared 档（历史口径，复现用）----
    if briefing == "declared":
        for item in timeline:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", item.get("role", "wave")))
            lines.append(
                f"  * [declared briefing] {label}: spawn_tick={item.get('spawn_tick', '?')} "
                f"count={item.get('count', '?')} axis={item.get('axis', '?')}; "
                f"{item.get('behavior', '')}")
    elif briefing == "withheld":
        lines.append(
            "  * NO prior intelligence on the enemy is available: you are NOT told how "
            "many waves will arrive, when, from which axis, or which contacts are "
            "armed. Several waves and unarmed decoys are possible. Classify every "
            "contact from your own observations and preserve missiles for real threats.")

    return "\n".join(lines)


def _build_defender(profile_data: Dict[str, Any], args):
    defence = profile_data["defence"]
    faction_id = str(defence["faction_id"])
    policies = tuple(
        WeaponPolicyV2(
            selector_tags=tuple(str(t) for t in policy.get("selector_tags", ())),
            weapon_ref=str(policy["weapon_ref"]),
            minimum_range_m=float(policy["minimum_range_m"]),
            maximum_range_m=float(policy["maximum_range_m"]),
            cooldown_ticks=int(policy["cooldown_ticks"]),
        )
        for policy in defence.get("weapon_policies", ())
    )
    intercept_speed = float(defence.get("intercept_speed_mps", 40.0))
    speed_by_tag = {"uav": intercept_speed, "usv": 8.0,
                    "interceptor": intercept_speed, "picket": 8.0}
    executor_config = ExecutorConfigV2(
        faction_id=faction_id,
        weapon_policies=policies,
        speed_by_tag=speed_by_tag,
        # 下层能力开关（消融用；默认值 = 当前行为）
        lead_pursuit=bool(getattr(args, "lead_pursuit", True)),
        fire_doctrine=str(getattr(args, "fire_doctrine", "assess")),
        patrol_sweep=bool(getattr(args, "patrol_sweep", True)),
        deconflict_fire=bool(getattr(args, "deconflict_fire", True)),
        retreat_when_out_of_ammo=bool(getattr(args, "retreat_when_dry", True)),
    )
    # 场景泛化：保护目标取自 profile 顶层 objective_m（数据驱动，不再硬编码 (0,0)）
    objective_raw = profile_data.get("objective_m") or (0.0, 0.0)
    objective_m = (float(objective_raw[0]), float(objective_raw[1]))
    # 下层战术（屏障/预备）需要保护区中心作为距离基准
    executor_config.objective_m = objective_m
    planner_config = RulePlannerConfigV2(
        objective_m=objective_m,
        confidence_min=float(defence.get("contact_confidence", 0.55)),
        contact_max_age_ticks=int(defence.get("maximum_contact_age_ticks", 10)),
        weapon_policies=policies,  # 武装判定跟随武器策略 selector 标签
        # 规则侧弹药教义：与 LLM 侧对等（都通过 goal 参数下发 fire_policy）
        fire_policy=(None if getattr(args, "rule_fire_policy", "salvo") == "none"
                     else getattr(args, "rule_fire_policy", "salvo")),
        fire_policy_urgent=(None if getattr(args, "rule_fire_policy_urgent", None)
                            in (None, "none")
                            else getattr(args, "rule_fire_policy_urgent")),
        fire_policy_urgent_eta_ticks=int(
            getattr(args, "rule_fire_policy_urgent_eta", 240)),
        intruder_speed_mps=float(
            profile_data.get("attack", {}).get("speed_mps", 45.0)),
    )
    # 提示词上下文：保护区坐标 + 武器射程（三种规划器共用口径）
    weapon_range = (
        f"{min(p.minimum_range_m for p in policies):.0f}-"
        f"{max(p.maximum_range_m for p in policies):.0f}"
    ) if policies else "500-8000"
    prompt_context = {
        "objective": f"({objective_m[0]:.0f},{objective_m[1]:.0f})",
        "objective_xy": objective_m,
        "weapon_range": weapon_range,
        # 速度包线：由 speed_by_tag 派生、逐平台给出，与逐单位清单同源。
        # 此前 pure-llm 的提示词硬编码 "0-45"，而真实上限是场景声明的 43（IE-08 为
        # 40）—— 提示词比执行层宽松，会诱导 LLM 下达随后被静默裁剪的速度值。
        "speed_range": ", ".join(
            f"{k} 0-{float(v):.0f}" for k, v in sorted(
                {"uav": speed_by_tag["uav"], "usv": speed_by_tag["usv"]}.items())),
        # 场景声明的来袭速度（m/s）：纯 LLM 的接触列表用它算 ETA，
        # 而不是硬编码常数（硬编码会把 ETA 算错数倍，误导提前占位时机）。
        "intruder_speed_mps": float(
            profile_data.get("attack", {}).get("speed_mps", 45.0)),
        # goal 未指定 fire_policy 时执行层采用的默认教义（让 LLM 知情，非特权信息）
        "default_fire_policy": executor_config.fire_doctrine,
        # 目标分类 / ROE 指引：按**声明的武器装订**分类（不再做文本子串匹配，
        # 那会把 IE-11 的"real air package"误判为非威胁），并按 --llm-briefing
        # 决定是否披露未来波次的时刻/方位/意图（默认 withheld = 不给未来真值）。
        "roe_notes": _build_roe_notes(
            profile_data,
            briefing=str(getattr(args, "llm_briefing", "withheld"))),
        "briefing_declared": str(getattr(args, "llm_briefing", "withheld")) == "declared",
    }
    if args.planner == "rl":
        # 强化学习臂：加载训练好的策略，走**完全相同的**规划/提交协议，
        # 从而与另外三臂共用同一套记分卡、开火判定与日志（见 rl_agent.py 说明）。
        from rl_agent import RLAgentV2
        theta_path = getattr(args, "rl_theta", None)
        if not theta_path:
            raise ValueError("--planner rl 需要 --rl-theta 指定训练好的策略文件")
        return RLAgentV2(
            str(args.scenario),
            theta_path,
            faction_id=faction_id,
            # 动作保持时长必须等于**训练时**的保持时长（env 的 decision_interval，
            # 默认 5）。这里过去读的是 `--plan-interval`（LLM 规划节奏，默认 10），
            # 于是纯 RL 臂一直在 2 倍保持时长下评测 —— 一个 train/eval 错配，
            # 会系统性地压低该臂读数，而它正是消融要用的对照列。
            decision_interval=int(getattr(args, "decision_interval", 5) or 5),
            deterministic=not bool(getattr(args, "rl_stochastic", False)),
            # 速度约定：显式参数 > checkpoint 里的训练 provenance > 环境变量 >
            # 默认（并被记成 guessed_default）。留成 None 让 RLAgentV2 走这条链，
            # 而不是在这里再写一遍优先级 —— 两份优先级正是约定漂移的来源。
            speed_source=getattr(args, "rl_speed_source", None),
            seed=int(getattr(args, "seed", 7)),
            name=f"defender.{args.planner}",
        )
    if args.planner in ("pure-llm", "llm", "llm-rl"):
        from llm_client_hifi import LLMClient
        from interception_graph import GraphBuilder, GraphConfig
        llm = LLMClient(
            base_url=args.llm_base_url or None,
            model=args.llm_model or None,
            max_tokens=args.llm_max_tokens,
            # 后端决定"关思考"的开关与 key 的环境变量名（见 llm_client_hifi）：
            # vllm→chat_template_kwargs.enable_thinking + OPENAI_API_KEY
            # deepseek→thinking={"type":"disabled"} + DEEPSEEK_API_KEY
            backend=getattr(args, "llm_backend", None),
        )
        graph_builder = None
        if getattr(args, "frontend", "graph") == "graph":
            graph_builder = GraphBuilder(
                GraphConfig(
                    confidence_min=0.0,  # 图里显示全部接触（带置信度），避免接触
                    contact_max_age_ticks=planner_config.contact_max_age_ticks,
                    objective_m=objective_m,
                    top_k=3,
                    history_size=5,
                    intruder_speed_mps=float(
                        profile_data.get("attack", {}).get("speed_mps", 45.0)),
                    protected_zone_bounds_m=tuple(
                        float(value) for value in profile_data.get(
                            "protected_zone_bounds_m", ())
                    ) or None,
                    attack_timeline=tuple(
                        dict(item) for item in profile_data.get(
                            "attack", {}).get("timeline", ()) or ()
                        if isinstance(item, dict)
                    ),
                ),
                weapon_policies=policies,
                speed_by_tag=speed_by_tag,
            )
        if args.planner == "pure-llm":
            from pure_llm_agent import PureLLMAgentV2
            # 速度包线对等性（论文级公平性）：历史实现把 pure-llm 的上限硬编码成
            # 45/10，而其它所有臂（rule-llm/rule-rl/rl/llm-rl）都走 `executor_config`
            # 的 `speed_by_tag` = 43/8（取自场景 `defence.intercept_speed_mps`）。
            # **水面差 +25% 且有质变**：来袭自爆船是 10 m/s，8 m/s 的我方无人船追不上，
            # 10 m/s 的追得上 —— 这恰好落在 pure-llm 反超混合臂的水面密集场景
            # （IE-10 双轴、IE-11 诱饵）上，因此是必须排除的混淆。
            #
            # 2026-02-05 起**默认改为 `executor`（与其它臂同表 43/8）**：六臂比较必须
            # 同包线，否则"混合 vs 纯 LLM"的差值里混着速度优势。`hardcoded` 仍可显式
            # 指定，仅用于复现 2026-02-05 之前的旧读数。
            if str(getattr(args, "pure_llm_envelope", "executor")) == "hardcoded":
                envelope = {"uav": 45.0, "usv": 10.0,
                            "interceptor": 45.0, "picket": 10.0}
            else:
                envelope = dict(speed_by_tag)
            return PureLLMAgentV2(
                faction_id=faction_id,
                llm=llm,
                weapon_policies=policies,
                speed_max_by_tag=envelope,
                call_interval=args.plan_interval,
                prompt_context=prompt_context,
                graph_builder=graph_builder,
                include_graph=graph_builder is not None,
                max_tokens=args.llm_max_tokens,
            )
        from llm_planner import LLMPlannerV2
        planner = LLMPlannerV2(
            planner_config, llm=llm, fallback_planner=RulePlannerV2(planner_config),
            max_tokens=args.llm_max_tokens,
            graph_builder=graph_builder,
            prompt_context=prompt_context,
        )
    else:
        planner = RulePlannerV2(planner_config)

    # Fifth arm: the SAME LLM planner, but the rule executor is replaced by a learned
    # one.  Only ``executor_factory`` differs from the ``llm`` branch above, so the
    # planner, prompt context, fallback planner, broker and orchestrator are shared
    # by construction rather than by convention.
    #
    # ``rule-rl`` is the cheap DIAGNOSTIC twin of that ablation: the rule planner (no
    # LLM at all) driving the same learned executor.  It exists because the headline
    # comparison ``llm`` vs ``llm-rl`` carries two sources of noise that have nothing
    # to do with the executor -- LLM non-determinism (the same configuration repeated
    # 5 times on the same seed gave sd 0.0295 with 3 bit-identical runs) and the
    # planner's own quality.  With a deterministic planner the pair
    # ``rule`` vs ``rule-rl`` isolates the executor swap alone, for the cost of an
    # RL-only sweep, and can be run at 5 seeds on all 8 scenarios for free.
    executor_factory = None
    if args.planner in ("llm-rl", "rule-rl"):
        theta = getattr(args, "rl_theta", None)
        if not theta:
            raise ValueError(f"--planner {args.planner} requires --rl-theta <theta.npz>")
        from rl_executor import RLExecutorV2

        def executor_factory(broker, _cfg=executor_config, _theta=theta):
            return RLExecutorV2(broker, _cfg, theta_path=_theta,
                                scenario_id=str(args.scenario),
                                decision_interval=int(getattr(args, "decision_interval", 5)),
                                deterministic=not bool(getattr(args, "rl_stochastic", False)),
                                speed_source=getattr(args, "rl_speed_source", None),
                                # 默认 False = 与冻结规则执行器同语义（消融对等）。
                                # 打开它只用于诊断"一轮齐射失败后目标被永久封禁"
                                # 这个缺陷的因果，见 LLMRL_CURRENT_AUDIT.md。
                                overkill_release=bool(getattr(args, "rl_overkill_release", False)),
                                seed=int(getattr(args, "seed", 7)))

    return AgentV2(planner=planner, executor_config=executor_config,
                   faction_id=faction_id, plan_interval=args.plan_interval,
                   name=f"defender.{args.planner}",
                   goal_granularity=getattr(args, "goal_granularity", None),
                   executor_factory=executor_factory)
def _checkpoint_mission(session):
    return session.world_view.checkpoint().mission_scoring_checkpoint


def _safe_checkpoint_mission(session):
    """Read optional score telemetry without aborting a live episode."""
    try:
        return _checkpoint_mission(session), None
    except Exception as error:  # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"


def _receipt_terminal(receipt) -> Optional[Dict[str, Any]]:
    """从 step 回执的 mission_receipts 提取终局结果（每 tick 轻量可用，无需 checkpoint）。
    世界层每个 tick 都会 append MissionTickReceiptV2（terminal_result 非空=终局达成）。
    兼容 pydantic 模型与序列化后的 dict 两种形态。
    """
    world = getattr(receipt, "world_receipt", None)
    receipts = getattr(world, "mission_receipts", None) if world is not None else None
    if not receipts:
        return None
    for item in reversed(receipts):
        value = getattr(item, "terminal_result", None)
        if value is None and isinstance(item, dict):
            value = item.get("terminal_result")
        if value is None:
            continue
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        # 引擎把终局回执冻结成 MappingProxyType：isinstance(x, dict) 对它为 **False**，
        # 早期实现因此退化成 {"result": "<repr 字符串>"}，终局结构（rule_id / outcome /
        # tick / latched）全部丢失，下游只能拿到一段含 ranking 的文本，
        # 甚至会把 ranking 里的 'coalition.intruder' 误判成"突防方胜"。
        if isinstance(value, Mapping):
            return {str(key): _plain_value(item) for key, item in value.items()}
        # 引擎的终局类型是 **frozen slots dataclass**（TerminalMissionResultV2），
        # 既不是 Mapping 也没有 model_dump，所以会掉进下面的字符串兜底 ——
        # 那正是上面注释描述的退化路径。实测后果：``outcome`` 丢失，
        # 消费方（如 RL 训练的奖励函数）永远读不到 defender_success /
        # intruder_success，terminal_win / terminal_loss 两项**恒为 0**，
        # 而记分卡靠 _parse_terminal_blob 解析 repr 才侥幸正确。
        # 这里按字段名把 dataclass/对象还原成普通 dict，并保留 ``result`` 键
        # （等于 outcome）以兼容既有的 ``terminal_result.get('result')`` 调用。
        fields = {}
        for name in ("rule_id", "outcome", "priority", "tick", "latched"):
            if hasattr(value, name):
                fields[name] = _plain_value(getattr(value, name))
        if "outcome" in fields:
            for name in ("trigger_evidence", "ranking"):
                if hasattr(value, name):
                    fields[name] = _plain_value(getattr(value, name))
            fields["result"] = fields["outcome"]
            return fields
        return {"result": str(value)}


def _plain_value(value: Any) -> Any:
    """把 MappingProxyType / tuple / 嵌套结构还原成可 JSON 序列化的普通对象。"""
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value
    return None
def _damage_intent_records(receipt) -> List[Dict[str, Any]]:
    """本 tick 引擎裁决出的毁伤意图（含来源性质与来源实体）。

    ``DamageIntentV2.source_kind`` 区分 ``weapon`` / ``collision`` / ``environment``，
    这是把"被火力击毁"与"自己撞山/搁浅"分开的**唯一权威依据**。此前记分卡把
    全部损失都算成对方击杀：IE-03 实测我方只开火 2 发却被记为 4 个击杀，弹药
    效率因此虚高到 2.0（`ammo` 层直接饱和），交换比也被凭空放大。

    **两条通道都要读**（第 11 轮踩过的坑）：火力毁伤走
    ``world_receipt.damage_receipts[*].applied_intents``（DamageSystemV2 的
    ``DamageApplyReceiptV2``），而边界/环境毁伤走
    ``world_receipt.motion_receipts[*].damage_intents``。只读后者会得到
    "一次 weapon 毁伤都没有" 的假象，把击杀数错误地记成 0。

    同时容忍 dataclass 与序列化 dict 两种回执形态（引擎在不同路径下都会给出）。
    """
    world = getattr(receipt, "world_receipt", None)
    containers: List[Any] = []
    if world is not None:
        containers.extend(getattr(world, "damage_receipts", None) or ())
        containers.extend(getattr(world, "motion_receipts", None) or ())

    def _field(node: Any, name: str, fallback: str) -> Any:
        value = getattr(node, name, None)
        if value is None and isinstance(node, dict):
            value = node.get(name, node.get(fallback))
        return value

    records: List[Dict[str, Any]] = []
    for container in containers:
        intents = _field(container, "applied_intents", "damage_intents")
        for intent in intents or ():
            target = _field(intent, "target_entity_id", "target_entity_id")
            if target is None:
                continue
            source = _field(intent, "source_entity_id", "source_entity_id")
            kind = _field(intent, "source_kind", "source_kind")
            effect = _field(intent, "effect_ref", "effect_ref")
            records.append({
                "source_entity_id": None if source is None else str(source),
                "target_entity_id": str(target),
                "source_kind": None if kind is None else str(kind),
                "effect_ref": None if effect is None else str(effect),
            })
    return records


def _executed_fire_statuses(fires, receipt) -> List[Dict[str, Any]]:
    """把开火提交与引擎 child_receipts 对齐：执行层提交 ≠ 引擎执行。
    引擎对 fire_weapon 离散动作会在 world 推进后按 combat 回执归一化：
    kind="discrete" 且 status="executed" 才算真正开火；弹药/射程/冷却被拒的
    提交会被改写为 "rejected"。返回每个 fire 的判定（含 status/executed）。
    """
    child_by_id = {
        str(child.child_id): child
        for child in getattr(receipt, "child_receipts", ())
    }
    verdicts = []
    for fire in fires:
        child = child_by_id.get(str(fire.get("action_id", "")))
        status = getattr(child, "status", "no-receipt")
        kind = getattr(child, "kind", None)
        verdicts.append({
            **{k: fire.get(k) for k in ("tick", "entity_id", "contact_id",
                                        "weapon_ref")},
            "status": status,
            "error_code": getattr(child, "error_code", None),
            "executed": kind == "discrete" and status == "executed",
        })
    return verdicts
class _RunLog:
    """过程日志：JSONL 逐行事件，即写即刷（中止也能保留到最后一刻）。"""
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = path.open("w", encoding="utf-8")
    def event(self, kind: str, **fields) -> None:
        """Append one JSONL event.

        `tick` may arrive either as an explicit keyword (the harness tick) or inside
        `fields`.  Previously the two were merged with `event(kind, tick=..., **fields)`,
        so a caller whose fields happened to contain `tick` raised
        `TypeError: got multiple values for keyword argument 'tick'` and **destroyed
        the whole episode** - observed on pure-llm IE-05, which aborted at tick 857
        after ~10 minutes of compute.  Logging must never be able to do that, so the
        merge is explicit here and a duplicate simply wins over the default.
        """
        tick = fields.pop("tick", None)
        payload = {"t": kind, "ts": round(time.time(), 3), **fields}
        if tick is not None:
            payload["tick"] = tick
        self._stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        self._stream.flush()
    def close(self) -> None:
        self._stream.close()
def _contact_anomalies(observation) -> Dict[str, int]:
    """接触重叠检查：同一观测者对同一实体后缀持有多个接触 = 真异常。
    （多观测者同时看到同一实体是共享态势的正常情况，不告警——LLM id 解析层
    已对歧义后缀做唯一性保护。）
    """
    seen: Dict[tuple, int] = {}
    for c in observation.contacts_by_faction.get(observation.observer_faction_id, ()):
        cid = str(c["contact_id"])
        owner = str(c["observer_entity_id"])
        prefix = f"sensor.contact.{owner}."
        suffix = cid[len(prefix):] if cid.startswith(prefix) else cid
        key = (owner, suffix)
        seen[key] = seen.get(key, 0) + 1
    return {f"{owner}:{suffix}": count for (owner, suffix), count in seen.items()
            if count > 1}
def _restore_session(args, checkpoint: Dict[str, Any]):
    """从会话检查点恢复（镜像 create_formal_gateway_v2 的 restore 工厂）。"""
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
    from openmdbench.sessions.lifecycle_v2 import SessionCheckpointV2, SessionLifecycleV2
    from openmdbench.world.factory_v2 import WorldFactoryV2
    resolved, catalog = compile_formal_scenario_v2(args.scenario)
    typed = SessionCheckpointV2.model_validate(checkpoint)
    factory = WorldFactoryV2(model_registry=catalog.model_registry)
    return SessionLifecycleV2.restore(
        checkpoint=typed,
        expected_checkpoint_hash=typed.checkpoint_hash,
        resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash,
        model_registry=catalog.model_registry,
        expected_model_registry_hash=resolved.model_registry_hash,
        world_factory=factory,
    )
def run_episode(args, run_log: Optional[_RunLog] = None) -> Dict[str, Any]:
    profile_data = load_attack_profile_data(args.scenario)
    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_path = checkpoint_dir / f"{args.scenario}_{args.seed}.ckpt.json"
    resumed_from: Optional[int] = None
    if args.resume:
        if not checkpoint_path.is_file():
            raise ValueError(f"--resume 但检查点不存在: {checkpoint_path}")
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        session = _restore_session(args, checkpoint)
        print(f"== 从检查点恢复: tick={session.world_view.tick} "
              f"({checkpoint_path})")
        resumed_from = int(session.world_view.tick)
        if session.state.value != "running":
            session.start()
    else:
        session = create_formal_session_v2(
            args.scenario, session_id=f"eval.episode.{args.seed}", seed=args.seed
        )
        session.load().start()
    attack = AttackProfileDriverV2(args.scenario, seed=args.seed)
    defender = _build_defender(profile_data, args)
    # 中立民用船：场景声明了航路就必须有人下机动指令，否则会话用
    # fallback_controls（nps=0）把船停住（见 civilian_transit 模块头）。
    from civilian_transit import CivilianTransitDriverV2, civilian_routes
    _civilian_profile = dict(profile_data.get("civilian_lane") or {})
    _civilian_route_table = civilian_routes(profile_data)
    civilians = (
        CivilianTransitDriverV2(
            faction_id=str(_civilian_profile.get("faction_id", "coalition.civilian")),
            routes=_civilian_route_table,
        )
        if _civilian_route_table else None
    )
    defender_faction = defender.faction_id
    intruder_faction = attack.faction_id
    start_tick = int(session.world_view.tick)
    started = time.perf_counter()
    ticks_run = start_tick
    checkpoint_saved = resumed_from is not None  # 恢复局不再重复存档
    terminal_result: Optional[Dict[str, Any]] = None
    score_state: Optional[Dict[str, Any]] = None
    mission_states: tuple = ()
    total_fires = 0
    total_fires_defender = 0
    total_fires_intruder = 0
    first_fire_tick = None
    first_fire_tick_by_side: Dict[str, Any] = {"defender": None, "intruder": None}
    executed_contacts: list = []
    executed_contacts_intruder: list = []
    # 逐发拒绝原因汇总：key = "<side>:<engine error code>"。分数卡只看结果，
    # 这张表回答"为什么没打成" —— 例如对中立民用船的开火会留下
    # defender:combat.roe_denied，这正是本场景 ROE 维度的可度量证据。
    fire_rejections: Dict[str, int] = {}
    # 交战意图按目标角色的分布（含被拒的尝试）：key = "<side>:<target role>"。
    # 用来回答"谁把注意力花在了民用船上"。
    engagements_by_target_role: Dict[str, int] = {}
    # 逐目标火力分布：key = "<side>:<target entity id>"。
    # 这是"火力是否全砸在同一个目标上"的直接证据 —— 实测 rule 臂在 IE-02 把 6 发
    # 全打在第一架来袭无人机上、第二架一发未受（拦截率 0.50），在 IE-06 把 8/16 发
    # 打在已声明为诱饵的目标上。把它落进报告，就不必再去翻运行日志。
    engagements_by_target: Dict[str, int] = {}
    # ---- 策略记分卡证据（全部来自引擎裁决，不看 harness 意图）----
    loss_records: list = []
    fire_records: list = []
    lifecycle_seen: Dict[str, str] = {
        entity.id: str(entity.state.lifecycle)
        for entity in session.world_view.entities_stable()
    }
    aborted: Optional[str] = None
    last_error: Optional[str] = None
    last_traceback: Optional[str] = None
    step_seconds: list = []
    faction_of: Dict[str, str] = {}
    # 毁伤归因：entity_id -> 最近一次受到的有效毁伤（来源性质 + 来源实体）
    last_damage: Dict[str, Dict[str, Any]] = {}
    faction_by_entity: Dict[str, str] = {}
    damage_by_kind: Dict[str, int] = {}
    def log(*, kind: str, **fields) -> None:
        if run_log is not None:
            run_log.event(kind, tick=session.world_view.tick, **fields)
    if run_log is not None:
        run_log.event("start", scenario=args.scenario, seed=args.seed,
                      planner=args.planner, max_ticks=args.max_ticks)
    try:
        for _ in range(max(1, args.max_ticks - start_tick)):
            tick = session.world_view.tick
            tick_started = time.perf_counter()
            attack_result = attack(session)
            result = defender(session)
            if civilians is not None:
                civilians(session)
            if result.get("submit_result") is not None:
                sub = result["submit_result"]
                log(kind="plan", accepted=sub.get("accepted"),
                    rejected=sub.get("rejected"))
            receipt = session.step(operation_id=f"eval.episode.tick.{tick:08d}",
                                   expected_tick=tick)
            # 真实开火判定：以引擎 combat 回执归一化后的 child_receipts 为准。
            # 提交 ≠ 执行：射程/弹药/冷却被引擎拒绝的 fire 不计入 total_fires
            # （修复：此前 fires=提交数，MEDIUM 曾计出 10 次而引擎只执行 6 次）。
            fires = result["executor"].get("fires", ())
            verdicts = _executed_fire_statuses(fires, receipt)
            # 活体实体 id 集合：目标归因一律以它为准，不硬编码阵营前缀
            # （场景可以有任意多个阵营，第三阵营的 id 前缀无法事先枚举）。
            known_ids = tuple(item.id for item in session.world_view.entities_stable())
            for verdict in verdicts:
                target = _contact_suffix(verdict.get("contact_id"), known_ids)
                target_role = _entity_role(session, verdict.get("contact_id"), known_ids)
                engagements_by_target["defender:" + target] = (
                    engagements_by_target.get("defender:" + target, 0) + 1)
                engagements_by_target_role["defender:" + str(target_role)] = (
                    engagements_by_target_role.get("defender:" + str(target_role), 0) + 1)
                if not verdict["executed"] and verdict.get("error_code"):
                    key = f"defender:{verdict['error_code']}"
                    fire_rejections[key] = fire_rejections.get(key, 0) + 1
                if verdict["executed"]:
                    total_fires += 1
                    total_fires_defender += 1
                    if first_fire_tick is None:
                        first_fire_tick = int(verdict.get("tick") or tick)
                    if first_fire_tick_by_side["defender"] is None:
                        first_fire_tick_by_side["defender"] = int(verdict.get("tick") or tick)
                    executed_contacts.append(str(verdict.get("contact_id") or ""))
                    fire_records.append(_fire_record(
                        verdict, tick, "defender", defender_faction, target_role,
                        target=target))
                err = f" err={verdict.get('error_code')}" if verdict.get("error_code") else ""
                print(f"[tick {tick:>4}] 开火[蓝] {verdict['entity_id']} -> {verdict['contact_id']} ({verdict['weapon_ref']}) status={verdict['status']}{err}", flush=True)
                log(kind="fire", side="defender", entity_id=verdict.get("entity_id"),
                    contact_id=verdict.get("contact_id"),
                    weapon_ref=verdict.get("weapon_ref"),
                    fire_tick=verdict.get("tick"),
                    status=verdict["status"], executed=verdict["executed"])
            # 红方（突防方）同样按引擎 child_receipts 判定：提交 ≠ 执行
            intruder_verdicts = _executed_fire_statuses(
                attack_result.get("fire_actions", ()), receipt)
            for verdict in intruder_verdicts:
                target = _contact_suffix(verdict.get("contact_id"), known_ids)
                target_role = _entity_role(session, verdict.get("contact_id"), known_ids)
                engagements_by_target["intruder:" + target] = (
                    engagements_by_target.get("intruder:" + target, 0) + 1)
                engagements_by_target_role["intruder:" + str(target_role)] = (
                    engagements_by_target_role.get("intruder:" + str(target_role), 0) + 1)
                if not verdict["executed"] and verdict.get("error_code"):
                    key = f"intruder:{verdict['error_code']}"
                    fire_rejections[key] = fire_rejections.get(key, 0) + 1
                if verdict["executed"]:
                    total_fires += 1
                    total_fires_intruder += 1
                    if first_fire_tick is None:
                        first_fire_tick = int(verdict.get("tick") or tick)
                    if first_fire_tick_by_side["intruder"] is None:
                        first_fire_tick_by_side["intruder"] = int(verdict.get("tick") or tick)
                    executed_contacts_intruder.append(str(verdict.get("contact_id") or ""))
                    fire_records.append(_fire_record(
                        verdict, tick, "intruder", intruder_faction, target_role,
                        target=target))
                err = f" err={verdict.get('error_code')}" if verdict.get("error_code") else ""
                print(f"[tick {tick:>4}] 开火[红] {verdict['entity_id']} -> {verdict['contact_id']} ({verdict['weapon_ref']}) status={verdict['status']}{err}", flush=True)
                log(kind="fire", side="intruder", entity_id=verdict.get("entity_id"),
                    contact_id=verdict.get("contact_id"),
                    weapon_ref=verdict.get("weapon_ref"),
                    fire_tick=verdict.get("tick"),
                    status=verdict["status"], executed=verdict["executed"])
            ticks_run = session.world_view.tick
            step_seconds.append(time.perf_counter() - tick_started)
            # 战损记录：本 tick 有实体从"可战"落入 LOST 状态 → 记下当时的位置
            # （这就是权威的"被击落点"，拦截纵深由它算）
            for entity in session.world_view.entities_stable():
                faction_by_entity[str(entity.id)] = str(entity.faction_id)
            # 毁伤归因必须在战损判定之前完成：本 tick 落损的实体，其"死因"就是
            # 同一 tick 引擎裁决出的毁伤意图（或此前累积的最近一次毁伤）。
            for damage in _damage_intent_records(receipt):
                damage["tick"] = ticks_run
                damage["source_faction"] = faction_by_entity.get(
                    damage["source_entity_id"] or "")
                last_damage[damage["target_entity_id"]] = damage
                kind = str(damage["source_kind"] or "unknown")
                damage_by_kind[kind] = damage_by_kind.get(kind, 0) + 1
            for entity in session.world_view.entities_stable():
                state = str(entity.state.lifecycle)
                previous = lifecycle_seen.get(entity.id)
                if (previous is not None and previous not in LOST_STATES
                        and state in LOST_STATES):
                    domain = str(getattr(entity, "domain", "") or "")
                    tags = tuple(str(tag) for tag in (getattr(entity, "tags", ()) or ()))
                    damage = last_damage.get(str(entity.id)) or {}
                    killer = damage.get("source_entity_id")
                    loss_records.append({
                        "tick": ticks_run,
                        "entity_id": entity.id,
                        "faction": str(entity.faction_id),
                        "role": classify_role(domain, tags),
                        "domain": domain,
                        "lifecycle": state,
                        "previous_lifecycle": previous,
                        "position_m": [float(v) for v in entity.state.position_m],
                        # 死因归因：weapon = 被火力击毁；collision / environment =
                        # 碰撞或环境损失（不计入任何一方的击杀数）
                        "damage_source_kind": damage.get("source_kind"),
                        "killer_entity_id": killer,
                        "killer_faction": damage.get("source_faction"),
                        "last_damage_tick": damage.get("tick"),
                        "self_inflicted": bool(killer) and str(killer) == str(entity.id),
                    })
                lifecycle_seen[entity.id] = state
            # 迎敌前检查点：跨过 --checkpoint-tick 时存档一次，供 --resume 续跑
            if (not checkpoint_saved and resumed_from is None
                    and ticks_run >= args.checkpoint_tick):
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                try:
                    checkpoint_path.write_text(
                        json.dumps(session.checkpoint().model_dump(mode="json")),
                        encoding="utf-8",
                    )
                except Exception as error:  # noqa: BLE001
                    checkpoint_saved = True
                    checkpoint_error = f"{type(error).__name__}: {error}"
                    print(f"[tick {ticks_run:>4}] 检查点不可用，继续运行: "
                          f"{checkpoint_error}", flush=True)
                    # NOTE: do NOT pass tick= here. `log()` already injects the harness
                    # tick, so an explicit tick in **fields collides with it and raises
                    # `TypeError: got multiple values for keyword argument 'tick'`,
                    # which aborts the WHOLE episode (observed: pure-llm IE-05 died at
                    # tick 857 this way). `phase` is what distinguishes this site.
                    log(kind="checkpoint_unavailable", error=checkpoint_error,
                        phase="pre_engagement")
                else:
                    checkpoint_saved = True
                    print(f"[tick {ticks_run:>4}] 检查点已存档: {checkpoint_path}",
                          flush=True)
                    log(kind="checkpoint_saved", tick_saved=ticks_run,
                        path=str(checkpoint_path))
            # 单 tick 看门狗：攻击+决策+步进超时 → 中止并保留现场
            if step_seconds[-1] > args.step_timeout:
                aborted = f"step_timeout at tick {tick}: "
                aborted += f"{step_seconds[-1]:.1f}s > {args.step_timeout}s"
                log(kind="watchdog", reason="step_timeout",
                    seconds=round(step_seconds[-1], 2))
                break
            # 逐 tick 轻量终局检测：命中终局规则 → 立即终止
            step_terminal = _receipt_terminal(receipt)
            if step_terminal is not None:
                terminal_result = step_terminal
                print(f"[tick {ticks_run:>4}] 终局达成，立即终止: "
                      f"{terminal_result.get('result', '')} "
                      f"({terminal_result.get('rule_id', '')})", flush=True)
                log(kind="terminal", terminal=terminal_result)
                break
            if ticks_run % args.report_every == 0 or tick == 0:
                mission, checkpoint_error = _safe_checkpoint_mission(session)
                if checkpoint_error:
                    log(kind="checkpoint_unavailable", error=checkpoint_error,
                        phase="periodic")
                if mission is not None:
                    score_state = mission.get("score_state", {})
                    mission_states = tuple(mission.get("mission_states", ()))
                    print(
                        f"[tick {ticks_run:>4}] score={score_state} "
                        f"states={mission_states} "
                        f"fires_total={total_fires}",
                        flush=True,
                    )
                    log(kind="score", score=score_state, states=mission_states,
                        fires_total=total_fires)
                # 接触重叠检查（同一观测者对同一实体重复持有才告警）
                anomalies = _contact_anomalies(
                    session.world_view.observation(
                        observer_faction_id=defender_faction))
                for key, count in anomalies.items():
                    log(kind="contact_overlap", observer_entity=key, count=count)
                    print(f"[tick {ticks_run:>4}] 告警: {key} 重复接触 x{count}",
                          flush=True)
            if args.wall_limit and time.perf_counter() - started > args.wall_limit:
                aborted = f"wall_limit {args.wall_limit}s reached at tick {tick}"
                log(kind="watchdog", reason="wall_limit")
                break
        mission, checkpoint_error = _safe_checkpoint_mission(session)
        if checkpoint_error:
            log(kind="checkpoint_unavailable", error=checkpoint_error,
                phase="final")
        # 收尾单位状态：角色/域/标签/存活/位置（记分卡输入）
        final_units: Dict[str, UnitState] = {}
        for entity in session.world_view.entities_stable():
            domain = str(getattr(entity, "domain", "") or "")
            tags = tuple(str(tag) for tag in (getattr(entity, "tags", ()) or ()))
            final_units[entity.id] = UnitState(
                entity_id=entity.id,
                faction=str(entity.faction_id),
                role=classify_role(domain, tags),
                domain=domain,
                tags=tags,
                lifecycle=str(entity.state.lifecycle),
                health=float(getattr(entity.state, "health", 1.0)),
                position_m=tuple(float(v) for v in entity.state.position_m),
            )
        if mission is not None:
            score_state = mission.get("score_state", {})
            terminal_result = terminal_result or mission.get("terminal_result")
            mission_states = tuple(mission.get("mission_states", ()))
        # ---- 策略记分卡（多维分数 + 总体策略评分）----
        strategy_scorecard: Optional[Dict[str, Any]] = None
        try:
            strategy_scorecard = compute_scorecard(
                units=final_units,
                losses=loss_records,
                fires=fire_records,
                facilities=_facility_weights(profile_data, final_units),
                defender_faction=defender_faction,
                attacker_faction=intruder_faction,
                terminal_result=terminal_result,
                aborted=aborted,
                ticks_run=ticks_run,
                max_ticks=args.max_ticks,
            )
            print("\n== 策略记分卡 ==")
            print("  " + format_scorecard_line(strategy_scorecard, args.planner))
            print(f"  无人机损失 蓝 {strategy_scorecard['force'][defender_faction]['uav']['lost']}"
                  f"/{strategy_scorecard['force'][defender_faction]['uav']['total']}"
                  f"  红 {strategy_scorecard['force'][intruder_faction]['uav']['lost']}"
                  f"/{strategy_scorecard['force'][intruder_faction]['uav']['total']}")
            print(f"  无人船损失 蓝 {strategy_scorecard['force'][defender_faction]['usv']['lost']}"
                  f"/{strategy_scorecard['force'][defender_faction]['usv']['total']}"
                  f"  红 {strategy_scorecard['force'][intruder_faction]['usv']['lost']}"
                  f"/{strategy_scorecard['force'][intruder_faction]['usv']['total']}")
            print(f"  拦截纵深 mean={strategy_scorecard['air_layer']['interception_depth_m']['mean']} m"
                  f"  拦截率={strategy_scorecard['air_layer']['interception_rate']}"
                  f"  漏防率={strategy_scorecard['air_layer']['leak_rate']}")
            print(f"  设施加权存活={strategy_scorecard['facilities']['weighted_survival']}"
                  f"  摧毁={strategy_scorecard['facilities']['destroyed']}"
                  f"  失能={strategy_scorecard['facilities']['out_of_action']}")
            print(f"  总体策略评分 防守方={strategy_scorecard['defender_score']}"
                  f"  突防方={strategy_scorecard['attacker_score']}", flush=True)
        except Exception as error:  # noqa: BLE001 记分卡失败不影响原报告
            print(f"[warn] 策略记分卡计算失败: {type(error).__name__}: {error}",
                  flush=True)
        # 阵营标注：按双方观察集（域判定），不靠编号前缀
        try:
            faction_of.update({
                str(item["entity_id"]): "defender"
                for item in session.world_view.observation(
                    observer_faction_id=defender_faction).own_entities
            })
            faction_of.update({
                str(item["entity_id"]): "intruder"
                for item in session.world_view.observation(
                    observer_faction_id=intruder_faction).own_entities
            })
        except Exception:  # noqa: BLE001 标注失败不影响结果
            pass
        entities = [
            {
                "entity_id": entity.id,
                "faction": faction_of.get(entity.id, entity.id.split(".", 1)[0]),
                "lifecycle": str(entity.state.lifecycle),
                "health": round(float(getattr(entity.state, "health", 1.0)), 3),
                "tags": list(getattr(entity, "tags", ()) or ()),
            }
            for entity in session.world_view.entities_stable()
        ]
        # 0830 论文多维评估指标 (Layered Evaluation Metrics)
        defender_units = [e for e in entities if e.get("faction") == "defender"]
        intruder_units = [e for e in entities if e.get("faction") == "intruder"]
        defender_alive = sum(1 for e in defender_units if e["lifecycle"] in {"active", "degraded"})
        defender_total = len(defender_units)
        intruder_neutralized = sum(1 for e in intruder_units if e["lifecycle"] in {"destroyed", "wreck"})
        intruder_total = len(intruder_units)
        term_text = str(terminal_result or "")
        states_text = " ".join(str(s) for s in mission_states)
        if "intruder_success" in term_text or "breach-failure" in states_text:
            outcome = "intruder_success"
            mission_success = False
        elif "defender_success" in term_text or "defence-success" in states_text or "raiders-neutralized" in states_text:
            outcome = "defender_success"
            mission_success = True
        elif "timeout" in term_text or "timeout-success" in states_text:
            outcome = "timeout_defender"
            mission_success = True
        elif aborted:
            outcome = "aborted"
            mission_success = False
        elif ticks_run >= args.max_ticks and "breach" not in states_text:
            outcome = "timeout_hold"
            mission_success = True
        else:
            outcome = "horizon_end"
            mission_success = False
        tagset = {str(e.get("entity_id")): set(str(x) for x in (e.get("tags") or ())) for e in entities}
        def _role(cid: str) -> str:
            suffix = cid.rsplit(".", 1)[-1] if cid else ""
            tags = tagset.get(suffix, set())
            blob = " ".join(tags) + " " + suffix
            if any(k in blob for k in ("civilian", "decoy", "feint", "diversion")):
                if "civilian" in blob:
                    return "civilian"
                return "decoy"
            if any(k in blob for k in ("civilian",)):
                return "civilian"
            if any(k in blob for k in ("decoy", "feint", "diversion")):
                return "decoy"
            return "threat"
        fires_civilian = sum(1 for c in executed_contacts if _role(c) == "civilian")
        fires_decoy = sum(1 for c in executed_contacts if _role(c) == "decoy")
        fires_threat = sum(1 for c in executed_contacts if _role(c) == "threat")
        sr_rate = 1.0 if mission_success else 0.0
        # ---- 旧口径与新记分卡对齐（第 11 轮）--------------------------------
        # 这一块是 0830 论文期的旧指标，与 `strategy_scorecard` 并行存在且口径不同：
        #   * `intruder_neutralized` 只数 {destroyed, wreck}，漏掉 `disabled`，
        #     于是 `threat_neutralization_rate` 与记分卡 `interception_rate` 对不上
        #     （实测 IE-01：0.5 vs 0.75）；
        #   * `ammo_eff` 的分母 `total_fires` 是**双方**发射总数，红方一开火就把
        #     我方弹药效率算错（IE-08：59 发总数 vs 我方 21 发）。
        # 同一份报告里出现两个互相矛盾的口径，正是"指标口径不一致"的来源。
        # 这里把有权威对应项的字段改为引用记分卡，并显式标注旧块已弃用。
        authoritative = strategy_scorecard.get("force", {}).get(intruder_faction, {})
        neutralized_lost = sum(
            int((authoritative.get(role) or {}).get("lost") or 0)
            for role in ("uav", "usv"))
        neut_rate = round(neutralized_lost / max(1, intruder_total), 4)
        alive_rate = round(defender_alive / max(1, defender_total), 4)
        performance_v = round(0.6 * sr_rate + 0.2 * neut_rate + 0.2 * alive_rate, 4)
        ammo_eff = round(
            float(strategy_scorecard.get("fire", {}).get(
                "defender_ammo_efficiency") or 0.0), 4)
        planner_stats = {}
        try:
            planner_stats = dict(defender.get_stats() or {})
        except Exception as error:  # noqa: BLE001
            # Record WHY instead of silently reporting an empty stats block: an
            # empty block reads as "this arm has no health metrics", which is
            # indistinguishable from a working arm whose metrics were dropped.
            planner_stats = {"get_stats_error": f"{type(error).__name__}: {error}"}
        layered_metrics = {
            "mission_success": mission_success,
            "outcome": outcome,
            "performance_v": performance_v,
            "defender_survival_rate": alive_rate,
            "threat_neutralization_rate": neut_rate,
            "defender_alive_count": defender_alive,
            "defender_total_count": defender_total,
            "intruder_neutralized_count": intruder_neutralized,
            "intruder_total_count": intruder_total,
            "total_fires": total_fires,
            "total_fires_defender": total_fires_defender,
            "total_fires_intruder": total_fires_intruder,
            "first_fire_tick": first_fire_tick,
            "first_fire_tick_defender": first_fire_tick_by_side["defender"],
            "first_fire_tick_intruder": first_fire_tick_by_side["intruder"],
            "fires_threat": fires_threat,
            "fires_decoy": fires_decoy,
            "fires_civilian": fires_civilian,
            "ammo_efficiency": ammo_eff,
            "score_denial": score_state.get("score.denial", 0.0) if score_state else 0.0,
            "score_survival": score_state.get("score.survival", 1.0) if score_state else 1.0,
            "score_efficiency": score_state.get("score.efficiency", 1.0) if score_state else 1.0,
            "plan_cycles": planner_stats.get("plan_cycles"),
            "goals_accepted": (planner_stats.get("broker") or {}).get("goals_accepted"),
            "goals_rejected": (planner_stats.get("broker") or {}).get("goals_rejected"),
            # ``planner`` is a dict for AgentV2/PureLLMAgentV2 but an arm may
            # legitimately report a string (as the RL arm first did, and as the
            # rule arm's top-level stats do).  Guard both shapes so a stats-shape
            # mismatch can no longer abort an otherwise complete episode and
            # zero the scorecard's terminal layer.
            "parse_failures": (
                (planner_stats.get("planner") or {}).get("parse_failures")
                if isinstance(planner_stats.get("planner"), dict)
                else planner_stats.get("parse_failures")),
            "fallback_count": (
                (planner_stats.get("planner") or {}).get("fallback_count")
                if isinstance(planner_stats.get("planner"), dict)
                else planner_stats.get("fallback_count")),
        }
    except Exception as error:  # noqa: BLE001 任何异常都优雅中止并保存部分结果
        last_error = f"{type(error).__name__}: {error}"
        # Full traceback into the report as well: storing only str(error) made a
        # mid-episode abort undiagnosable -- the RL arm aborted at tick 899 with
        # "AttributeError: 'str' object has no attribute 'get'" and there was no
        # way to tell where it came from without re-running under a debugger.
        _tb = traceback.format_exc()
        last_traceback = _tb
        layered_metrics = {"mission_success": False, "performance_v": 0.0, "total_fires": total_fires}
        aborted = aborted or f"exception: {last_error}"
        print(f"[中止] {aborted}", flush=True)
        print(_tb, flush=True)
        if run_log is not None:
            run_log.event("abort", reason=aborted,
                          traceback=_tb.strip().splitlines()[-12:])
        try:
            checkpoint = session.world_view.checkpoint()
            mission = checkpoint.mission_scoring_checkpoint
            score_state = mission.get("score_state", {}) if mission else {}
            mission_states = tuple(mission.get("mission_states", ())) if mission else ()
        except Exception:  # noqa: BLE001 failed-op 状态下 checkpoint 可能不可用
            pass
        entities = []
        # 中止局同样要出记分卡：此前这里只设了 layered_metrics，报告组装处引用
        # strategy_scorecard 会直接抛 UnboundLocalError，把整局的证据全部丢掉
        # （实测 DeepSeek 后端中途 SSL 断连时就是这样丢掉了一局 1200 tick 的数据）。
        # 中止局以 aborted 入参计算，terminal 层按"中断=0 分"口径记录。
        def _snapshot_units() -> Dict[str, UnitState]:
            snapshot: Dict[str, UnitState] = {}
            for item in session.world_view.entities_stable():
                tags = tuple(str(tag) for tag in (getattr(item, "tags", ()) or ()))
                domain = str(getattr(item, "domain", "") or "")
                snapshot[str(item.id)] = UnitState(
                    entity_id=str(item.id),
                    faction=str(item.faction_id),
                    role=classify_role(domain, tags),
                    domain=domain,
                    tags=tags,
                    lifecycle=str(item.state.lifecycle),
                    health=float(getattr(item.state, "health", 1.0)),
                    position_m=tuple(float(v) for v in item.state.position_m),
                )
            return snapshot

        try:
            abort_units = _snapshot_units()
            strategy_scorecard = compute_scorecard(
                units=abort_units,
                losses=loss_records,
                fires=fire_records,
                facilities=_facility_weights(profile_data, abort_units),
                defender_faction=defender_faction,
                attacker_faction=intruder_faction,
                terminal_result=terminal_result,
                aborted=aborted,
                ticks_run=ticks_run,
                max_ticks=args.max_ticks,
            )
        except Exception as score_error:  # noqa: BLE001 记分卡失败也不能丢掉报告
            print(f"[中止] 记分卡不可用: {type(score_error).__name__}: {score_error}",
                  flush=True)
    finally:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
    elapsed = time.perf_counter() - started
    report = {
        "scenario": args.scenario,
        "seed": args.seed,
        "planner": args.planner,
        "start_tick": start_tick,
        "resumed_from": resumed_from,
        "ticks_run": ticks_run,
        "elapsed_seconds": round(elapsed, 2),
        "ticks_per_second": round(ticks_run / elapsed, 2) if elapsed > 0 else None,
        "aborted": aborted,
        "error": last_error,
        "traceback": last_traceback,
        "terminal_result": terminal_result,
        "score_state": score_state,
        "mission_states": mission_states,
        "total_fires": total_fires,
        "total_fires_defender": total_fires_defender,
        "total_fires_intruder": total_fires_intruder,
        "step_mean_seconds": round(sum(step_seconds) / len(step_seconds), 3)
        if step_seconds else None,
        "step_max_seconds": round(max(step_seconds), 3) if step_seconds else None,
        "entities": entities,
        # 逐发拒绝原因与交战意图的目标角色分布：分数卡之外的"为什么"证据。
        # 中立民用船相关的 ROE 维度就靠 fire_rejections 里的
        # combat.roe_denied / combat.relationship_denied 计数来度量。
        "fire_rejections": dict(sorted(fire_rejections.items())),
        "engagements_by_target_role": dict(sorted(engagements_by_target_role.items())),
        "engagements_by_target": dict(sorted(engagements_by_target.items())),
        # 毁伤来源分布（weapon / collision / environment）：战损归因的原始证据，
        # 供记分卡区分"被击毁"与"自己撞山"，也便于事后审计击杀口径。
        "damage_by_kind": dict(sorted(damage_by_kind.items())),
        "layered_metrics": layered_metrics,
        "strategy_scorecard": strategy_scorecard,
        "defender": defender.get_stats(),
        "attack": attack.get_stats(),
    }
    if run_log is not None:
        run_log.event("finish", ticks_run=ticks_run, elapsed=round(elapsed, 2),
                      terminal=terminal_result, aborted=aborted,
                      score=score_state, fires_total=total_fires)
        run_log.close()
    return report
def build_parser() -> argparse.ArgumentParser:
    """The CLI parser, exposed so other callers can derive a COMPLETE args object.

    The training worker needs an ``args`` for ``_build_defender`` and used to
    hand-build an ``argparse.Namespace`` listing the fields it thought mattered.
    That broke the moment ``_build_defender`` read one more field
    (``llm_base_url``): the worker died with a missing-attribute error, and the
    same thing would happen again on every future CLI addition.  Deriving the
    namespace from the real parser cannot drift.
    """
    parser = argparse.ArgumentParser(description="W1 端到端跑局（V2 正式会话）")
    parser.add_argument("--scenario", default="MD-AD-002-EASY")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-ticks", type=int, default=1800)
    parser.add_argument("--planner",
                        choices=("rule", "llm", "pure-llm", "rl", "llm-rl", "rule-rl"),
                        default="rule",
                        help="rule=规则规划+GOAI执行；llm=千问规划+GOAI执行（混合）；"
                             "pure-llm=千问每 tick 直接出低层命令（论文 System B）；"
                             "rl=训练好的 PPO 策略直接出低层命令（第四臂，需 --rl-theta）；"
                             "llm-rl=**千问规划不变**，把规则执行器换成 RL 执行层"
                             "（第五臂消融，需 --rl-theta）；"
                             "rule-rl=规则规划 + RL 执行层（廉价诊断臂：无 LLM 噪声地"
                             "隔离'执行器换成学习型'这一个变量，需 --rl-theta）")
    parser.add_argument("--rl-theta", default=None,
                        help="--planner rl 用的策略参数 .npz（ie_rl_train.py 产出的 checkpoint）")
    parser.add_argument("--rl-stochastic", action="store_true",
                        help="RL 臂按分布采样而非取众数（默认确定性，便于复现）")
    parser.add_argument("--rl-speed-source", default=None,
                        choices=("catalog", "legacy_tags"),
                        help="RL 臂速度包线约定，**必须等于该 checkpoint 训练时的值**。"
                             "legacy_tags=规则执行器的 40/8 表（消融对照口径）；"
                             "catalog=平台真实上限 80/10。留空则按 "
                             "checkpoint 训练 provenance > 环境变量 RL_SPEED_SOURCE > "
                             "默认 的顺序解析，并在报告里给出 "
                             "speed_source_provenance（guessed_default 表示没有依据）。")
    parser.add_argument("--llm-briefing", default="withheld",
                        choices=("withheld", "declared"),
                        help="LLM 提示词是否包含场景声明的攻击时间线（作战简报）。"
                             "**withheld（默认，公平口径）**=只给聚合事实（武装来袭者"
                             "总数、诱饵数、中立民用数），不给波次时刻/方位/意图，"
                             "LLM 必须自己从实时观测分辨诱饵；declared=历史口径，"
                             "逐条给出 spawn_tick/count/axis/behavior（含未来真值），"
                             "**仅用于复现 2026-09-27 之前的旧读数**。"
                             "注意 rule-rule 与 rl 两臂从不读取该文本。")
    parser.add_argument("--pure-llm-envelope", default="executor",
                        choices=("hardcoded", "executor"),
                        help="pure-llm 臂的速度上限来源。**默认 executor**=与其它所有臂"
                             "同表（场景 defence.intercept_speed_mps，IE 集为 43/8），"
                             "六臂比较必须同包线。hardcoded=历史的 45/10，**仅供复现"
                             "2026-02-05 之前的旧读数**；来袭自爆船 10 m/s，8 m/s 的我方"
                             "无人船追不上、10 m/s 的追得上，故 45/10 会在水面密集场景上"
                             "给 pure-llm 质变优势。")
    parser.add_argument("--rl-overkill-release", action="store_true",
                        help="仅 RL 执行层：一轮齐射被评估为失败（评估窗过后目标仍在）时"
                             "归还超杀计数，使活目标可以重新交战。**默认关闭**，"
                             "以保持与冻结规则执行器同语义（消融对等）；打开它用于诊断"
                             "IE-03 seed 19 那个 0 分（14 枚弹却只允许打 6 发）。")
    parser.add_argument("--decision-interval", type=int, default=5,
                        help="llm-rl：RL 执行层的决策间隔。规则执行器每 tick 重解，"
                             "此默认 5 意味着第五臂的控制带宽更粗（已知未隔离因素）；"
                             "设 1 可对齐带宽，代价是评测更慢且随机采样会逐 tick 抖动。")
    parser.add_argument("--plan-interval", type=int, default=10,
                        help="rule/llm：规划间隔 tick（LLM 思考间隔，默认 10）；"
                             "pure-llm：LLM 调用间隔")
    parser.add_argument("--report-every", type=int, default=100)
    parser.add_argument("--step-timeout", type=float, default=60.0,
                        help="单 tick（攻击+决策+步进）超时秒数，超过即中止")
    parser.add_argument("--wall-limit", type=float, default=0.0,
                        help="整局墙钟上限秒数（0=不限），超过即中止并保存部分结果")
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--llm-backend", choices=("vllm", "deepseek"), default=None,
                        help="LLM 后端；决定关思考开关与 API key 的环境变量名")
    parser.add_argument("--llm-max-tokens", type=int, default=1024,
                        help="LLM 输出 token 上限（只影响上限与最坏耗时，不影响生成速率）")
    parser.add_argument("--checkpoint-dir", type=Path,
                        default=Path.home() / "eval_w1_runs" / "checkpoints",
                        help="迎敌前检查点目录")
    parser.add_argument("--checkpoint-tick", type=int, default=300,
                        help="迎敌前检查点存档时刻（首次跨过即存）")
    parser.add_argument("--resume", action="store_true",
                        help="从该场景+seed 的检查点恢复续跑（跳过前期无效时间）")
    parser.add_argument("--goal-granularity", choices=("weak", "medium", "strong"), default=None,
                        help="目标命令三档粒度裁剪 (B_if 归因操纵)")
    parser.add_argument("--frontend", choices=("graph", "raw"), default="graph",
                        help="前置模块开关（对照实验）：graph=结构化态势图/时间线"
                             "（默认，mixed 与 pure-llm 同前置）；raw=关闭前置模块，"
                             "pure-llm 仅收到原始接触报告（裸 LLM 对照臂）")
    # ---- 规则侧弹药教义（与 LLM 侧对等：都通过 goal 参数下发 fire_policy）----
    parser.add_argument("--rule-fire-policy", choices=("none", "salvo", "assess", "pk"),
                        # 第 14 轮改为 assess：逐发日志证实 salvo 让每架一次性打光 2 发，
                        # 而认领会在单位阵亡后轮换 → IE-02 出现三架接力把 6 发全倾泻在
                        # 同一个目标上、另一架来袭者一发未受（拦截率 0.50）。
                        # assess 是"打一发、等约 12 tick 评估再决定"，与两个 LLM 臂的
                        # 执行层默认教义一致，同时消除规则侧被默认赋予更强教义的不对称。
                        default="assess",
                        help="规则组基准教义：assess=单发后评估（默认）；salvo=每目标连发 2 发；"
                             "pk=等杀伤概率达标；none=不下发")
    parser.add_argument("--rule-fire-policy-urgent", choices=("none", "salvo", "assess", "pk"),
                        default="none",
                        help="规则组确定性映射：目标距禁区 ETA ≤ 阈值时改用该教义"
                             "（例如 base=assess + urgent=salvo 表示省弹优先、"
                             "对即将破防者确保击毁）")
    parser.add_argument("--rule-fire-policy-urgent-eta", type=int, default=240,
                        help="紧急教义触发的 ETA 阈值（tick）")
    # ---- 下层能力消融开关（三组同施；默认值 = 当前行为）----
    parser.add_argument("--fire-doctrine", choices=("salvo", "assess", "pk"),
                        default="assess",
                        help="下层默认教义（goal 未指定 fire_policy 时生效）")
    parser.add_argument("--no-lead-pursuit", dest="lead_pursuit",
                        action="store_false", default=True,
                        help="关闭提前量拦截（退化为尾追），用于下层消融")
    parser.add_argument("--no-patrol-sweep", dest="patrol_sweep",
                        action="store_false", default=True,
                        help="关闭巡逻/屏障到位后的扇面扫掠，用于下层消融")
    parser.add_argument("--no-deconflict", dest="deconflict_fire",
                        action="store_false", default=True,
                        help="关闭同 tick 目标去冲突，用于下层消融")
    parser.add_argument("--no-retreat-when-dry", dest="retreat_when_dry",
                        action="store_false", default=True,
                        help="关闭弹尽自动脱离，用于下层消融")
    parser.add_argument("--output", type=Path, default=None,
                        help="把完整结果写入 JSON 文件")
    parser.add_argument("--log", type=Path, default=None,
                        help="过程日志 JSONL 路径；默认 "
                             "~/eval_w1_runs/logs/<planner>_seed<seed>_<ts>.jsonl")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.log is None:
        log_path = Path.home() / "eval_w1_runs" / "logs" / (
            f"{args.planner}_seed{args.seed}_{int(time.time())}.jsonl")
    else:
        log_path = args.log
    run_log = _RunLog(log_path)
    print(f"== eval episode: scenario={args.scenario} seed={args.seed} "
          f"planner={args.planner} max_ticks={args.max_ticks}")
    print(f"== 过程日志: {run_log.path}")
    report = run_episode(args, run_log)
    print("== 终局结果 ==")
    print(json.dumps({
        "ticks_run": report["ticks_run"],
        "aborted": report["aborted"],
        "terminal_result": report["terminal_result"],
        "score_state": report["score_state"],
        "mission_states": report["mission_states"],
        "total_fires": report["total_fires"],
        "elapsed_seconds": report["elapsed_seconds"],
        "ticks_per_second": report["ticks_per_second"],
        "step_mean_seconds": report["step_mean_seconds"],
        "step_max_seconds": report["step_max_seconds"],
    }, indent=2, ensure_ascii=False, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"== 结果已写入 {args.output}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())





