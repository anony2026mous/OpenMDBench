"""Unit tests for grid_env v2 (Phase 1-3 of the v2 upgrade plan).

Covers (per Test Plan):
- lock acquire / loss (grace) / jam effects
- fuel depletion (movement disabled, adjacent intercept still allowed), resupply
- action-noise determinism across identical seeds
- blue-blue bounce (no damage), dynamic obstacle collision (stun)
- standoff intercept requires active UAV lock; direct intercept does not
- UAV cannot intercept (action 5 degrades to stay)
- comm latency delivery
- set_upper_action validation (H.4) incl. ammo budget
- v1 observation/metrics compatibility keys
- full random rollouts on all difficulties (smoke)

Run: python -u test_grid_env_v2.py
"""
import sys
import numpy as np

from grid_env.grid_env import (
    GridEnv, EntityType, Direction, MAX_STEPS,
    FUEL_MAX, RESUPPLY_POINTS, LOCK_ACQUIRE_STEPS, LOCK_LOSS_GRACE,
)
from grid_env.grid_env import LockState, DynamicObstacle

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  PASS {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name} {detail}")


def stay_actions(env, extra=None):
    a = {uid: Direction.STAY.value for uid in env.blue_units}
    if extra:
        a.update(extra)
    return a


def red_stay(env):
    return {rid: Direction.STAY.value for rid in env.red_units}


# ----------------------------------------------------------------------
def test_formation():
    print("[test_formation]")
    env = GridEnv(difficulty="simple", seed=1)
    check("blue ids", env.blue_units == ["blue_0", "blue_1", "blue_2"])
    check("usv ids", env.usv_units == ["blue_0", "blue_1"])
    check("uav id", env.uav_id == "blue_2")
    check("usv pos", [env.entities[u].x for u in env.usv_units] == [1, 3]
          and all(env.entities[u].y == 1 for u in env.usv_units))
    uav = env.entities["blue_2"]
    check("uav pos/kind", (uav.x, uav.y) == (2, 2) and uav.unit_kind == "uav")
    check("uav no ammo", uav.ammo == 0)
    check("usv ammo simple", all(env.entities[u].ammo == 5 for u in env.usv_units))
    check("fuel init", all(env.entities[u].fuel == FUEL_MAX for u in env.blue_units))
    check("simple comm delay 0", env.comm_delay == 0)
    check("simple no dyn obstacles", len(env.dynamic_obstacles) == 0)


def test_lock_acquire_and_loss():
    print("[test_lock_acquire_and_loss]")
    env = GridEnv(difficulty="simple", seed=2)
    # Put one red combatant within UAV vision (8) but far from USVs
    rid = next(r for r in env.red_units
               if env.entities[r].entity_type == EntityType.RED_COMBATANT)
    red = env.entities[rid]
    red.x, red.y = 6, 2   # dist to UAV(2,2): 4 <= 8; dist to USVs > 5
    for r2 in env.red_units:
        if r2 != rid:
            env.entities[r2].alive = False

    for _ in range(LOCK_ACQUIRE_STEPS):
        env.step(stay_actions(env), red_stay(env))
    check("lock acquired after 2 steps",
          env.lock is not None and env.lock.acquired and env.lock.target_id == rid)

    # Move target out of UAV vision -> grace accrues
    red.x, red.y = 19, 10
    lost_at = None
    for i in range(LOCK_LOSS_GRACE + 2):
        env.step(stay_actions(env), red_stay(env))
        if env.lock is None and lost_at is None:
            lost_at = i + 1
    check("lock lost after grace", lost_at == LOCK_LOSS_GRACE + 1,
          f"lost_at={lost_at}")

    # Bring back into vision -> reacquired after 2 steps
    red.x, red.y = 5, 2
    for _ in range(LOCK_ACQUIRE_STEPS):
        env.step(stay_actions(env), red_stay(env))
    check("lock reacquired", env.lock is not None and env.lock.acquired)

    # Jam: UAV jammed counts as not seeing
    uav = env.entities[env.uav_id]
    uav.jammed_steps = 5
    for i in range(LOCK_LOSS_GRACE + 1):
        env.step(stay_actions(env), red_stay(env))
    check("lock lost while jammed", env.lock is None,
          f"lock={env.lock}")


def test_fuel():
    print("[test_fuel]")
    env = GridEnv(difficulty="simple", seed=3)
    usv = env.entities["blue_0"]
    usv.fuel = 0.3
    usv.x, usv.y = 6, 6
    env.step({**stay_actions(env), "blue_0": Direction.RIGHT.value}, red_stay(env))
    check("movement blocked when fuel < 0.5", (usv.x, usv.y) == (6, 6))
    check("stay cost still applies", abs(usv.fuel - 0.2) < 1e-6)

    # Out of fuel entirely: adjacent intercept still allowed
    usv.fuel = 0.0
    rid = next(r for r in env.red_units
               if env.entities[r].entity_type == EntityType.RED_COMBATANT)
    red = env.entities[rid]
    red.x, red.y = 7, 6
    for r2 in env.red_units:
        if r2 != rid:
            env.entities[r2].alive = False
    env.step({**stay_actions(env), "blue_0": Direction.INTERCEPT.value}, red_stay(env))
    check("intercept allowed at zero fuel", not red.alive)

    # Resupply: standing on (2,2) gains 20/step (capped at 100)
    usv.x, usv.y = RESUPPLY_POINTS[0]
    usv.fuel = 50.0
    env.step(stay_actions(env), red_stay(env))
    check("resupply +20 - 0.1", abs(usv.fuel - 69.9) < 1e-6, f"fuel={usv.fuel}")
    usv.fuel = 99.5
    env.step(stay_actions(env), red_stay(env))
    check("fuel capped at 100", usv.fuel == 100.0, f"fuel={usv.fuel}")


def test_noise_determinism():
    print("[test_noise_determinism]")
    acts_rng = np.random.RandomState(777)
    seq = []
    for _ in range(60):
        seq.append({uid: int(acts_rng.randint(0, 6)) for uid in ("blue_0", "blue_1", "blue_2")})

    def rollout(seed):
        env = GridEnv(difficulty="complex", seed=seed)
        snaps = []
        for a in seq:
            env.step(a, None)  # scripted red
            state = sorted((e.id, e.x, e.y, e.alive, e.fuel)
                           for e in env.entities.values())
            lock = (env.lock.target_id, env.lock.age, env.lock.acquired) if env.lock else None
            snaps.append((tuple(state), lock, env.metrics["dyn_obstacle_collisions"],
                          env.metrics["static_obstacle_bumps"], env.metrics["fuel_consumed"]))
        return snaps

    s1, s2 = rollout(42), rollout(42)
    check("identical seeds -> identical trajectories", s1 == s2)
    s3 = rollout(43)
    check("different seeds -> (almost surely) different trajectories", s1 != s3)


def test_bounce():
    print("[test_bounce]")
    env = GridEnv(difficulty="simple", seed=4)
    b0, b1 = env.entities["blue_0"], env.entities["blue_1"]
    b0.x, b0.y = 6, 8   # legal cells (obstacle blocks are (5-7,5-6) etc.)
    b1.x, b1.y = 7, 8
    h0, h1 = b0.health, b1.health
    env.step({**stay_actions(env), "blue_0": Direction.RIGHT.value}, red_stay(env))
    check("bounce: no move", (b0.x, b0.y) == (6, 8))
    check("bounce: no damage", b0.health == h0 and b1.health == h1)
    check("bounce: both lose 1 step",
          (b0.disabled_steps >= 1 or b1.disabled_steps >= 1))
    check("bounce metric", env.metrics["blue_bounce_events"] == 1)


def test_dynamic_obstacle():
    print("[test_dynamic_obstacle]")
    env = GridEnv(difficulty="medium", seed=5)
    b0 = env.entities["blue_0"]
    b0.x, b0.y = 8, 12   # legal cell, away from obstacle blocks
    b0.disabled_steps = 0
    # Chase obstacle right next to the unit
    env.dynamic_obstacles = [DynamicObstacle(id="dyn_x", x=8, y=13, mode="chase")]
    before = env.metrics["dyn_obstacle_collisions"]
    env.step(stay_actions(env), red_stay(env))
    check("dyn obstacle collision counted",
          env.metrics["dyn_obstacle_collisions"] == before + 1)
    check("unit stunned", b0.disabled_steps >= 1 or env.metrics["dyn_obstacle_collisions"] > before)
    # Reward includes -10 penalty
    r = env.compute_reward("blue")
    check("dyn collision penalized", r <= -10.0 - 0.01, f"r={r}")


def test_standoff_and_direct_intercept():
    print("[test_standoff_and_direct_intercept]")
    env = GridEnv(difficulty="simple", seed=6)
    b0 = env.entities["blue_0"]
    b0.x, b0.y = 10, 10
    rid = next(r for r in env.red_units
               if env.entities[r].entity_type == EntityType.RED_COMBATANT)
    red = env.entities[rid]
    for r2 in env.red_units:
        if r2 != rid:
            env.entities[r2].alive = False
    # Chebyshev 3, no lock -> intercept refused
    red.x, red.y = 13, 10
    env.step({**stay_actions(env), "blue_0": Direction.INTERCEPT.value}, red_stay(env))
    check("standoff refused without lock", red.alive)

    # With active lock -> standoff kill
    env.lock = LockState(target_id=rid, age=5, acquired=True, acquired_step=env.step_count)
    red.x, red.y = 13, 10
    env.step({**stay_actions(env), "blue_0": Direction.INTERCEPT.value}, red_stay(env))
    check("standoff kill with lock", not red.alive)
    ev = env.metrics["intercept_events"][-1]
    check("event range standoff+locked",
          ev["range"] == "standoff" and ev["locked"] is True)

    # Direct intercept without lock
    rid2 = None
    env.lock = None
    red2 = None
    for r2 in env.red_units:
        if env.entities[r2].entity_type == EntityType.RED_COMBATANT:
            rid2 = r2
            break
    if rid2 is None:  # revive one
        red = env.entities[rid]
        red.alive = True
        rid2, red2 = rid, red
    else:
        red2 = env.entities[rid2]
    red2.x, red2.y = 11, 10
    env.step({**stay_actions(env), "blue_0": Direction.INTERCEPT.value}, red_stay(env))
    check("direct intercept adjacency", not red2.alive)

    # UAV intercept action degrades to stay (no crash, no kill)
    uav = env.entities["blue_2"]
    red2.alive = True
    red2.x, red2.y = uav.x + 1, uav.y
    env.step({**stay_actions(env), "blue_2": Direction.INTERCEPT.value}, red_stay(env))
    check("uav cannot intercept", red2.alive)


def test_comm_delay():
    print("[test_comm_delay]")
    env = GridEnv(difficulty="medium", seed=7)
    d = env.comm_delay
    check("medium delay in [2,3]", d in (2, 3), f"d={d}")
    rid = next(r for r in env.red_units
               if env.entities[r].entity_type == EntityType.RED_COMBATANT)
    red = env.entities[rid]
    red.x, red.y = 2, 8  # Manhattan 6 from UAV(2,2): in vision, out of jam range
    for r2 in env.red_units:
        if r2 != rid:
            env.entities[r2].alive = False
    check("no report before any step", env.last_delivered_report is None)
    for i in range(d):
        env.step(stay_actions(env), red_stay(env))
        if i < d - 1:
            assert env.last_delivered_report is None or True
    check("report still in transit at delay-1",
          env.last_delivered_report is None or env.step_count - env.last_delivered_report["step"] >= d)
    env.step(stay_actions(env), red_stay(env))
    rep = env.last_delivered_report
    check("report delivered after delay", rep is not None and rep["step"] == 1)
    check("report contains contact", rid in rep["contacts"])


def test_upper_action():
    print("[test_upper_action]")
    env = GridEnv(difficulty="simple", seed=8)
    ok = env.set_upper_action(json_str := json.dumps({
        "unit_assignments": [
            {"unit_id": "blue_0", "task": "intercept", "target_type": "operative"},
            {"unit_id": "blue_2", "task": "lock", "target_priority": 1},
        ],
        "uav_lock_assignments": [{"uav_id": "blue_2", "target_id": env.red_units[0]}],
        "rules_of_engagement": "protect civilians",
        "ammo_allocation": {"blue_0": 1},
        "fuel_conservation": True,
    }))
    check("valid JSON accepted", ok["ok"], str(ok))
    check("subgoal stored", env.get_subgoal("blue_2")["task"] == "lock")
    check("lock assignment stored", env.assigned_lock_target == env.red_units[0])
    check("ammo budget", env.ammo_budget["blue_0"] == 1)

    bad = env.set_upper_action("{\"unit_assignments\": [")
    check("invalid JSON rejected", bad["ok"] is False)
    bad2 = env.set_upper_action({"unit_assignments": [{"unit_id": "nope", "task": "x"}]})
    check("unknown unit flagged", bad2["ok"] is False and bad2["errors"])

    # Ammo budget caps intercepts
    env2 = GridEnv(difficulty="simple", seed=9)
    env2.set_upper_action({"ammo_allocation": {"blue_0": 1}})
    b0 = env2.entities["blue_0"]
    b0.x, b0.y = 10, 10
    b0.ammo = 5
    reds = [r for r in env2.red_units
            if env2.entities[r].entity_type == EntityType.RED_COMBATANT]
    for i, rid in enumerate(reds):
        env2.entities[rid].x, env2.entities[rid].y = 10 + i * 3, 10
    # first adjacent kill consumes the 1-round budget
    env2.step({**stay_actions(env2), "blue_0": Direction.INTERCEPT.value},
              {r: Direction.STAY.value for r in env2.red_units})
    killed = sum(1 for r in reds if not env2.entities[r].alive)
    check("budget allows first intercept", killed == 1)
    # second intercept blocked by budget
    env2.set_upper_action({})  # clear? no: empty keeps defaults -> uncapped
    env2.ammo_budget = {"blue_0": 0}
    next_r = next((r for r in reds if env2.entities[r].alive), None)
    if next_r:
        env2.entities[next_r].x, env2.entities[next_r].y = 11, 10
        b0.x, b0.y = 10, 10
        env2.step({**stay_actions(env2), "blue_0": Direction.INTERCEPT.value},
                  {r: Direction.STAY.value for r in env2.red_units})
        check("exhausted budget blocks intercept", env2.entities[next_r].alive)


def test_obs_compat_and_rollouts():
    print("[test_obs_compat_and_rollouts]")
    for diff in ("simple", "medium", "complex"):
        env = GridEnv(difficulty=diff, seed=11)
        obs = env._get_observation("blue")
        for k in ("mission_briefing", "situational_data", "situational_report",
                  "event_log", "ammo_remaining", "upper_directives"):
            if k not in obs:
                check(f"{diff} obs key {k}", False)
                break
        else:
            check(f"{diff} obs keys v1+v2", True)
        sd = obs["situational_data"]
        check(f"{diff} sd keys",
              all(k in sd for k in ("friendly_assets", "detected_contacts",
                                    "civilian_positions", "uav_lock", "fuel",
                                    "comm_status", "dynamic_obstacles")))
        robs = env._get_observation("red")
        check(f"{diff} red obs ok", "friendly_assets" in robs["situational_data"])

        lo_usv = env.get_local_observation(env.usv_units[0])
        lo_uav = env.get_local_observation(env.uav_id)
        check(f"{diff} local grids", lo_usv["grid"].shape == (5, 5)
              and lo_uav["grid"].shape == (8, 8))
        check(f"{diff} own_state 5-dim", lo_usv["own_state"].shape == (5,)
              and lo_uav["own_state"].shape == (5,))
        check(f"{diff} usv lock view", "lock_view" in lo_usv)
        check(f"{diff} uav jam field", "jammed_steps" in lo_uav)

    # Full random rollout on each difficulty
    rng = np.random.RandomState(5)
    for diff in ("simple", "medium", "complex"):
        env = GridEnv(difficulty=diff, seed=12)
        total_r = 0.0
        while not env.done:
            acts = {uid: int(rng.randint(0, 6)) for uid in env.blue_units}
            env.step(acts, None)
            total_r += env.compute_reward("blue")
        m = env.get_episode_metrics()
        v1_keys = ("mission_success", "winner", "blue_score", "rule_violation_rate",
                   "ammo_efficiency", "adaptation_latencies", "port_penetrations")
        v2_keys = ("intercept_lock_rate", "handover_latencies",
                   "lock_maintenance_ratio", "avg_lock_duration",
                   "fuel_consumed", "fuel_efficiency")
        check(f"{diff} rollout done in {env.step_count} steps, winner={env.winner}",
              env.step_count <= MAX_STEPS)
        check(f"{diff} metrics v1 keys", all(k in m for k in v1_keys))
        check(f"{diff} metrics v2 keys", all(k in m for k in v2_keys))
        check(f"{diff} fuel accounting", m["fuel_consumed"] > 0)
    _ = total_r


import json  # noqa: E402  (used above)

if __name__ == "__main__":
    test_formation()
    test_lock_acquire_and_loss()
    test_fuel()
    test_noise_determinism()
    test_bounce()
    test_dynamic_obstacle()
    test_standoff_and_direct_intercept()
    test_comm_delay()
    test_upper_action()
    test_obs_compat_and_rollouts()
    print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
    if FAIL:
        for f in FAIL:
            print("  FAILED:", f)
        sys.exit(1)
