"""Gate for the goal encoder used by the fifth arm (LLM plan + RL executor).

Every check here must be able to FAIL on a plausible implementation mistake, because
the encoder is the only channel by which the LLM's plan reaches the network: if it is
wrong, the ablation silently measures "a learned executor with no plan" and the
conclusion "the LLM adds nothing" would be an artefact of this file.

Usage:
    python _w1_test_goal_features.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> int:
    from ie_goal_features import (GOAL_TYPE_ORDER, N_TYPES, PER_UNIT_WIDTH,
                                  active_by_unit, encode_goals, goal_terms,
                                  goal_type_index)

    units = ["defender.uav-01", "defender.uav-02", "defender.usv-01"]
    positions = {"defender.uav-01": (0.0, 0.0, 800.0),
                 "defender.uav-02": (1000.0, 0.0, 800.0),
                 "defender.usv-01": (2000.0, 0.0, 0.0)}

    print(f"-- layout: {PER_UNIT_WIDTH} features/unit, {N_TYPES} goal types")
    check("declared width matches the term list",
          len(list(goal_terms())) == PER_UNIT_WIDTH,
          f"{len(list(goal_terms()))} vs {PER_UNIT_WIDTH}")
    check("vocabulary matches goai_protocol.GOAL_TYPES",
          set(GOAL_TYPE_ORDER) == set(__import__("goai_protocol").GOAL_TYPES),
          str(set(GOAL_TYPE_ORDER) ^ set(__import__("goai_protocol").GOAL_TYPES)))

    # ---- no goals at all --------------------------------------------------
    block = encode_goals({}, units, positions)
    check("shape follows the unit list",
          block.shape == (len(units), PER_UNIT_WIDTH), str(block.shape))
    check("a unit with no goal has has_goal == 0 and encodes nothing else",
          float(block[:, N_TYPES].sum()) == 0.0
          and float(np.abs(block).sum()) == 0.0,
          f"sum={float(np.abs(block).sum())}")

    # ---- an intercept with a target --------------------------------------
    goal = {"task_id": "intercept_001", "goal_type": "intercept",
            "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.uav-91",
                           "speed_mps": 40.0},
            "priority": 0.9, "deadline": 20, "issued_at": 0}
    block = encode_goals({"defender.uav-01": [goal]}, units, positions,
                         speed_limits={"defender.uav-01": 80.0},
                         target_positions={"intruder.uav-91": (0.0, 5000.0, 200.0)},
                         tick=5)
    row = block[0]
    check("the goal lands in ITS OWN unit's slot, not slot 0 by accident",
          float(row[goal_type_index("intercept")]) == 1.0
          and float(block[1].sum()) == 0.0 and float(block[2].sum()) == 0.0,
          f"uav-01 intercept={row[goal_type_index('intercept')]}, "
          f"uav-02 sum={float(block[1].sum())}")
    check("has_goal and has_target are set",
          float(row[N_TYPES]) == 1.0 and float(row[N_TYPES + 1]) == 1.0)
    # target is due north 5 km -> bearing 0 -> sin 0, cos 1
    check("target bearing is the true bearing to the target",
          abs(float(row[N_TYPES + 2])) < 1e-6 and abs(float(row[N_TYPES + 3]) - 1.0) < 1e-6,
          f"sin={row[N_TYPES + 2]:.4f} cos={row[N_TYPES + 3]:.4f}")
    check("target distance is normalised and in range",
          0.0 < float(row[N_TYPES + 4]) <= 1.0,
          f"{row[N_TYPES + 4]:.4f} (5000 m / 40000 m = 0.125)")
    check("speed is expressed as a fraction of THIS unit's limit",
          abs(float(row[N_TYPES + 7]) - 40.0 / 80.0) < 1e-6,
          f"{row[N_TYPES + 7]:.4f}")
    check("priority is carried through", abs(float(row[N_TYPES + 8]) - 0.9) < 1e-6)
    check("deadline counts down from issue", 0.0 < float(row[N_TYPES + 9]) <= 1.0,
          f"{row[N_TYPES + 9]:.4f} (15 ticks remaining / 100)")

    # the speed fraction must follow the unit, not a constant: same goal, other unit
    block2 = encode_goals({"defender.usv-01": [dict(goal, parameters={
        **goal["parameters"], "unit_id": "defender.usv-01"})]},
        units, positions, speed_limits={"defender.usv-01": 10.0})
    check("the same cruise speed reads differently for a slower platform",
          abs(float(block2[2][N_TYPES + 7]) - 1.0) < 1e-6,
          f"usv 40/10 clamped to {block2[2][N_TYPES + 7]:.3f}")

    # ---- priority picks the goal, and unknown types must raise ------------
    low = {"goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01"},
           "priority": 0.2}
    high = {"goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01"},
            "priority": 0.95}
    block = encode_goals({"defender.uav-01": [low, high]}, units, positions)
    check("the highest-priority active goal is the one encoded",
          float(block[0][goal_type_index("intercept")]) == 1.0
          and float(block[0][goal_type_index("patrol")]) == 0.0)
    close = dict(high, goal_type="hold", priority=0.955)
    block = encode_goals({"defender.uav-01": [high, close]}, units, positions)
    check("priority epsilon matches the rule executor's active goal",
          float(block[0][goal_type_index("intercept")]) == 1.0
          and float(block[0][goal_type_index("hold")]) == 0.0)

    try:
        encode_goals({"defender.uav-01": [{"goal_type": "teleport",
                                           "parameters": {"unit_id": "defender.uav-01"}}]},
                     units, positions)
        check("an unknown goal_type raises instead of encoding as 'no goal'",
              False, "no exception raised")
    except ValueError:
        check("an unknown goal_type raises instead of encoding as 'no goal'", True)

    # ---- broker grouping semantics ---------------------------------------
    class _State:
        def __init__(self, command, status="executing", terminal=False):
            self.command, self.status, self.terminal = command, status, terminal

    class _Cmd:
        def __init__(self, unit, goal_type, priority=0.5):
            self.unit_id, self.goal_type, self.priority = unit, goal_type, priority

    active = {
        "a": _State(_Cmd("defender.uav-01", "intercept")),
        "b": _State(_Cmd("defender.uav-02", "patrol"), status="superseded"),
        "c": _State(_Cmd("defender.uav-01", "hold"), terminal=True),
        "d": _State(_Cmd(None, "patrol")),                     # no unit -> dropped
    }
    grouped = active_by_unit(active)
    check("superseded and terminal goals are excluded",
          sorted(len(v) for v in grouped.values()) == [1]
          and list(grouped) == ["defender.uav-01"],
          str({k: [c.goal_type for c in v] for k, v in grouped.items()}))
    check("a goal with no unit_id is dropped rather than assigned to slot 0",
          all(v for k, v in grouped.items()) and "None" not in grouped)

    from ie_rl_train import initial_goal_observation
    from ie_rl_train import evaluation_policy_args
    from argparse import Namespace
    from run_episode import build_parser
    for goal_features, goal_source, expected_planner in (
            (True, "llm", "llm-rl"), (True, "rule", "rule-rl"),
            (False, "rule", "rl")):
        evaluation_args = evaluation_policy_args(Namespace(
            goal_features=goal_features, goal_source=goal_source,
            decision_interval=3, plan_interval=17, speed_source="legacy_tags"),
            "candidate.npz")
        parsed = build_parser().parse_args(evaluation_args)
        check(f"automatic evaluation preserves {expected_planner} architecture and cadence",
              parsed.planner == expected_planner
              and parsed.decision_interval == 3 and parsed.plan_interval == 17
              and parsed.rl_speed_source == "legacy_tags"
              and Path(parsed.rl_theta).is_absolute())
    from ie_rl_train import _make_goal_source
    from unittest.mock import Mock, patch
    hook_env = Mock()
    hook_env._session = None
    hook_agent = Mock()
    hook_status = Mock()
    with patch("attack_driver.load_attack_profile_data", return_value={}), \
            patch("run_episode._build_defender", return_value=hook_agent), \
            patch("rl_executor.RLExecutorV2", return_value=hook_status):
        _, training_hook, _ = _make_goal_source(
            hook_env, {"theta": "unused.npz", "goal_source": "llm"},
            "IE-01-SINGLE-TARGET")
    training_hook(0)
    check("training hook does not mark an absent session as planned",
          hook_agent.plan_once.call_count == 0)
    hook_env._session = Mock()
    for hook_tick in (0, 0, 1, 5, 5, 10, 10):
        training_hook(hook_tick)
    check("training hook plans once per tick and defers reporting to actual execution",
          [call.args[1] for call in hook_agent.plan_once.call_args_list]
          == [0, 1, 5, 10]
          and hook_status.report_goals_only.call_count == 0
          and hook_env.rollout_executor is hook_status)
    class InitialGoalEnv:
        def __init__(self):
            self._session = type("Session", (), {"world_view": type(
                "View", (), {"tick": 0})()})()
            self.calls = []
            self._attack = lambda session: self.calls.append(("attack", 0))
            self.pre_tick_hook = lambda tick: self.calls.append(("plan", tick))

        def observe(self):
            self.calls.append(("observe", 0))
            return "planned observation"

    initial_env = InitialGoalEnv()
    initial = initial_goal_observation(initial_env, "empty observation")
    check("training first action sees tick-zero goals",
          initial == "planned observation"
          and initial_env.calls == [("attack", 0), ("plan", 0),
                                    ("observe", 0)])

    # ---- the target_id form a real planner emits -------------------------
    # Real planners set ``target_id`` to a CONTACT id
    # (``sensor.contact.defender.uav-03.intruder.uav-01``) while the environment
    # keys its contacts by ENTITY id (``intruder.uav-01``).  The first version of
    # the env indexed only the entity id, so no intercept goal ever resolved its
    # target and ``has_target`` stayed at 0 -- the network could not see where it
    # had been told to intercept.  Both forms must work.
    from ie_goal_features import encode_goals as _enc
    contact_id = "sensor.contact.defender.uav-03.intruder.uav-01"
    goal = {"goal_type": "intercept",
            "parameters": {"unit_id": "defender.uav-01", "target_id": contact_id},
            "priority": 0.9}
    for form in (contact_id, "intruder.uav-01"):
        row = _enc({"defender.uav-01": [dict(goal, parameters={
            **goal["parameters"], "target_id": form})]},
            ["defender.uav-01"], {"defender.uav-01": (0.0, 0.0, 800.0)},
            target_positions={contact_id: (0.0, 5000.0, 200.0),
                              "intruder.uav-01": (0.0, 5000.0, 200.0)})[0]
        check(f"a target_id in {form.split('.')[0]!r} form resolves to a bearing",
              float(row[N_TYPES + 1]) == 1.0
              and abs(float(row[N_TYPES + 3]) - 1.0) < 1e-6,
              f"has_target={row[N_TYPES + 1]} cos={row[N_TYPES + 3]:.4f}")

    # ---- environment integration -----------------------------------------
    # The encoder being right is not enough: the block has to be appended at the
    # right offset, padded to MAX_UNITS (the encoder returns one row per REAL unit),
    # and left entirely zero for an arm that has no planner above it.
    from ie_rl_env import GOAL_FEATURE_WIDTH, MAX_CONTACTS, MAX_UNITS, IERlEnv

    check("the env takes the block width from the encoder",
          GOAL_FEATURE_WIDTH == PER_UNIT_WIDTH,
          f"{GOAL_FEATURE_WIDTH} vs {PER_UNIT_WIDTH}")

    plain = IERlEnv("IE-01-SINGLE-TARGET", goal_features=False)
    with_goals = IERlEnv("IE-01-SINGLE-TARGET", goal_features=True)
    try:
        check("enabling goals adds the plan block AND the assignment mask",
              with_goals.observation_size - plain.observation_size
              == MAX_UNITS * PER_UNIT_WIDTH + MAX_UNITS * MAX_CONTACTS,
              f"{with_goals.observation_size} - {plain.observation_size}")

        env = IERlEnv("IE-01-SINGLE-TARGET", seed=1000, decision_interval=5,
                      max_ticks=60, goal_features=True)
        try:
            env.reset()
            planned_ticks = []
            env.pre_tick_hook = planned_ticks.append
            env.goal_provider = lambda: {
                "defender.uav-01": [{"goal_type": "hold", "parameters": {
                    "unit_id": "defender.uav-01"}, "priority": 0.5}]}
            attack_ticks = []
            original_attack = env._attack
            def record_attack(session):
                attack_ticks.append(int(session.world_view.tick))
                return original_attack(session)
            env._attack = record_attack
            neutral = {
                "heading_xy": np.tile(np.array([0.0, 1.0], dtype=np.float32),
                                      (env.num_units, 1)),
                "speed": np.zeros(env.num_units, dtype=np.float32),
                "fire": np.zeros(env.num_units, dtype=np.int64),
            }
            next_obs, _, terminated, truncated, _ = env.step(neutral)
            check("next decision observes goals planned at its own tick",
                  not terminated and not truncated
                  and planned_ticks[-1] == env._session.world_view.tick
                  and next_obs.shape == (env.observation_size,),
                  str(planned_ticks))
            check("training drives the attacker exactly once per engine tick",
                  attack_ticks == list(range(env.decision_interval + 1)),
                  str(attack_ticks))
            original_max_ticks = env._max_ticks
            env._max_ticks = int(env._session.world_view.tick) + env.decision_interval
            next_obs, _, terminated, truncated, cut_info = env.step(neutral)
            check("truncated successor observes its own current plan for bootstrap",
                  truncated and not terminated
                  and planned_ticks[-1] == env._session.world_view.tick
                  and next_obs.shape == (env.observation_size,))
            check("truncation standing is diagnostic, not an extra terminal reward",
                  cut_info["truncation_bonus"] == 0.0
                  and "truncation_standing_diagnostic" in cut_info)
            env._max_ticks = original_max_ticks
            env.pre_tick_hook = None
            env.goal_provider = None
            execution_ticks = []
            rollout_executor = Mock()
            def record_execution(session, tick):
                execution_ticks.append(tick)
                return {"fires": []}
            rollout_executor.act.side_effect = record_execution
            env.rollout_executor = rollout_executor
            starting_tick = int(env._session.world_view.tick)
            with patch.object(env, "submit_action",
                              side_effect=AssertionError("direct action submission bypassed executor")):
                env.step(neutral)
            check("goal-conditioned rollout executes through shared executor on every engine tick",
                  execution_ticks == list(range(starting_tick, starting_tick + 5)))
            check("goal-conditioned rollout caches the PPO sample once per decision",
                  rollout_executor.prepare_action.call_count == 1
                  and rollout_executor.prepare_action.call_args.args[0] is env
                  and rollout_executor.prepare_action.call_args.args[1] is neutral
                  and rollout_executor.prepare_action.call_args.args[2] == starting_tick)
            env.rollout_executor = None
            obs = env.observe()
            check("the observation is exactly the advertised size",
                  obs.shape == (env.observation_size,), str(obs.shape))
            offset = 6 + MAX_UNITS * 10 + MAX_CONTACTS * 7 \
                + MAX_UNITS * MAX_CONTACTS * env.pair_width
            # The plan block is followed by a (MAX_UNITS, MAX_CONTACTS) "assigned to
            # me" mask, so the block must be sliced by its OWN width: reshaping the
            # remainder of the observation yields rows that straddle both blocks and
            # the assertions below would pass on the wrong data.
            block = obs[offset:offset + MAX_UNITS * PER_UNIT_WIDTH].reshape(
                MAX_UNITS, PER_UNIT_WIDTH)
            check("with no goal provider the block is entirely zero",
                  float(np.abs(block).sum()) == 0.0,
                  f"sum={float(np.abs(block).sum())}")

            real = env.real_units
            env.goal_provider = lambda: {
                "defender.uav-01": [{"goal_type": "intercept",
                                     "parameters": {"unit_id": "defender.uav-01",
                                                    "target_id": "intruder.uav-91"},
                                     "priority": 0.9}]}
            block = env.observe()[offset:offset + MAX_UNITS * PER_UNIT_WIDTH].reshape(MAX_UNITS, PER_UNIT_WIDTH)
            check("a goal appears in its own slot and nowhere else",
                  float(block[0][N_TYPES]) == 1.0
                  and float(block[0][goal_type_index("intercept")]) == 1.0
                  and float(np.abs(block[1:]).sum()) == 0.0,
                  f"slot0 has_goal={block[0][N_TYPES]} rest="
                  f"{float(np.abs(block[1:]).sum())}")
            check("padded slots beyond the real roster stay zero",
                  float(np.abs(block[real:]).sum()) == 0.0,
                  f"real units={real}, MAX_UNITS={MAX_UNITS}")
            target = "intruder.uav-01"
            first = "sensor.contact.defender.uav-01.intruder.uav-01"
            second = "sensor.contact.defender.uav-02.intruder.uav-01"
            contacts = [
                {"contact_id": first, "estimated_position_m": (100.0, 200.0, 0.0)},
                {"contact_id": second, "estimated_position_m": (300.0, 400.0, 0.0)},
            ]
            positions = env._goal_target_positions(
                contacts, (target,), [target], [(100.0, 200.0, 0.0)])
            check("every observer's contact resolves to its own estimate",
                  tuple(positions[first]) == (100.0, 200.0, 0.0)
                  and tuple(positions[second]) == (300.0, 400.0, 0.0),
                  str(positions))
            from rl_executor import RLExecutorV2
            executor = object.__new__(RLExecutorV2)
            executor._contact_to_target = {first: target}
            executor._shots_on_target = {target: 2}
            executor._last_shot_tick = {target: 10}
            check("adherence resolves another observer's contact to the same target",
                  executor._target_of_contact(second) == target)
            executor._prune_shot_ledger(set())
            check("lost targets release both shot and assess ledgers",
                  not executor._shots_on_target and not executor._last_shot_tick)
            from types import SimpleNamespace
            action_env = Mock()
            action_env._slots = [SimpleNamespace(entity_id="defender.uav-01")]
            action_env._last_contacts = [target]
            action_env._own_contact = {("defender.uav-01", target): (first,)}
            action_env.decode_unit_action.return_value = (90.0, 20.0, first)
            action_env.num_fire_choices = 2
            receipt_env = object.__new__(IERlEnv)
            receipt_env._slots = action_env._slots
            receipt_env._last_fire_tick = {}
            fire_records = [
                {"action_id": "executor-shot", "entity_id": "defender.uav-01"},
                {"action_id": "rejected-shot", "entity_id": "defender.uav-01"},
                {"action_id": "shore-shot", "entity_id": "defender.shore-01"}]
            shot_receipt = SimpleNamespace(child_receipts=[
                SimpleNamespace(child_id="executor-shot", kind="discrete", status="executed"),
                SimpleNamespace(child_id="rejected-shot", kind="discrete", status="rejected"),
                SimpleNamespace(child_id="shore-shot", kind="discrete", status="executed"),
                SimpleNamespace(child_id="rl.fire.defender.uav-01.10",
                                kind="discrete", status="executed")])
            check("shared executor shot accounting counts only submitted executed mobile shots",
                  receipt_env._executed_shots(shot_receipt, 10, fire_records) == 1
                  and receipt_env._last_executed_fire_ids == {"executor-shot"}
                  and receipt_env._last_fire_tick == {"defender.uav-01": 10})
            check("direct RL shot accounting retains legacy receipt support",
                  receipt_env._executed_shots(shot_receipt, 11) == 1
                  and receipt_env._last_fire_tick == {"defender.uav-01": 11})
            sampled_action = {"fire": np.array([1])}
            executor.stats = {"rl_decisions": 0, "rl_forward_ticks": 0}
            executor._shots_on_target = {target: 1, "gone": 2}
            executor._last_shot_tick = {target: 7, "gone": 3}
            executor.prepare_action(action_env, sampled_action, 10)
            cached = dict(executor._pending)
            check("external RL action keeps live doctrine and removes lost targets",
                  executor._shots_on_target == {target: 1}
                  and executor._last_shot_tick == {target: 7}
                  and executor._contact_to_target == {first: target})
            executor.decision_interval = 5
            executor._theta = {}
            executor._rng = np.random.default_rng(1)
            executor.deterministic = True
            executor._ensure_env = Mock(return_value=action_env)
            with patch("rl_executor.numpy_sample",
                       return_value=(sampled_action, None, None, None)) as sampler:
                executor._run_policy_once(None, 11)
                check("cached training action does not trigger another network sample",
                      sampler.call_count == 0 and executor._pending == cached)
                executor._fire_issued.add("defender.uav-01")
                executor._run_policy_once(None, 15)
                check("evaluation inference uses identical cached action decoding",
                      sampler.call_count == 1 and executor._pending == cached
                      and executor._decision_tick == 15
                      and executor._fire_issued == set()
                      and executor.stats["rl_decisions"] == 2)
            from goai_protocol import GOAIBroker, GoalCommand
            from v2_executor import ExecutorConfigV2
            from types import SimpleNamespace
            broker = GOAIBroker()
            command = GoalCommand(task_id="intercept_901", goal_type="intercept",
                                  parameters={"unit_id": "defender.uav-01",
                                              "target_id": first}, priority=0.9)
            broker.submit_goals([command], step=0)
            status_executor = object.__new__(RLExecutorV2)
            status_executor.broker = broker
            status_executor.config = ExecutorConfigV2(
                faction_id="coalition.defender")
            status_executor._reported_terminal = set()
            status_executor.last_goal_tick = -(10 ** 9)
            status_executor.safe_mode = False
            status_executor.last_periodic_report = 0
            status_executor.stats = {"goals_completed": 0,
                                     "goals_infeasible": 0,
                                     "goals_timeout": 0, "goals_failed": 0}
            own = {"entity_id": "defender.uav-01", "lifecycle_state": "active",
                   "position_m": (0.0, 0.0, 800.0)}
            observation = SimpleNamespace(
                observer_faction_id=status_executor.config.faction_id,
                own_entities=(own,),
                                          contacts_by_faction={
                                              status_executor.config.faction_id: ()})
            session = SimpleNamespace(world_view=SimpleNamespace(
                observation=lambda observer_faction_id: observation))
            status_executor.report_goals_only(session, 5)
            reports = broker.poll_reports()
            check("training status bridge reports a lost goal",
                  any(report.task_id == "intercept_901"
                      and report.status == "infeasible" for report in reports),
                  str([(report.task_id, report.status) for report in reports]))
            periodic_broker = GOAIBroker()
            periodic_broker.submit_goals([
                GoalCommand(task_id="waypoint_periodic", goal_type="waypoint",
                            parameters={"unit_id": "defender.uav-01",
                                        "position": (1000.0, 0.0, 800.0)},
                            priority=0.9)], step=0)
            periodic_executor = object.__new__(RLExecutorV2)
            periodic_executor.broker = periodic_broker
            periodic_executor.config = status_executor.config
            periodic_executor._reported_terminal = set()
            periodic_executor.last_goal_tick = -(10 ** 9)
            periodic_executor.safe_mode = False
            periodic_executor.last_periodic_report = 0
            periodic_executor.stats = {"goals_completed": 0,
                                       "goals_infeasible": 0,
                                       "goals_timeout": 0, "goals_failed": 0}
            periodic_executor.report_goals_only(session, 1)
            periodic_broker.poll_reports()
            from goai_protocol import T_STATUS_PERIOD
            periodic_executor.report_goals_only(session, T_STATUS_PERIOD)
            periodic_reports = periodic_broker.poll_reports()
            check("training status bridge emits periodic executing report once",
                  sum(report.task_id == "waypoint_periodic"
                      and report.status == "executing"
                      and report.reported_at == T_STATUS_PERIOD
                      for report in periodic_reports) == 1,
                  str([(report.task_id, report.status, report.reported_at)
                       for report in periodic_reports]))
            own["position_m"] = (1000.0, 0.0, 800.0)
            periodic_executor.report_goals_only(session, T_STATUS_PERIOD + 1)
            arrival_reports = periodic_broker.poll_reports()
            check("RL status bridge completes a three-dimensional waypoint on arrival",
                  any(report.task_id == "waypoint_periodic"
                      and report.status == "completed" for report in arrival_reports),
                  str([(report.task_id, report.status) for report in arrival_reports]))
            env.goal_provider = None
        finally:
            env.close()
    finally:
        plain.close()
        with_goals.close()

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
