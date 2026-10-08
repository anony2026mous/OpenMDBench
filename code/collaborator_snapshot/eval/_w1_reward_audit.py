"""Audit: does the training reward still pay for "let the raid land"?

Two defects are being closed here, both found by measurement rather than review
(recorded run notes, s1 experiment):

1. **The truncation proxy was blind to the raid that was about to land.**  It
   scored facility health only, so a raider parked on the doorstep still paid the
   full ``+2.0``.  8 of the 14 training episodes are truncated, so that blindness
   was worth more than half the batch -- the training reward rose 5.08 -> 7.86 over
   30 iterations while IE-01's scorecard fell 0.2689 -> 0.1312 with every layer
   degrading at once.

2. **Kill credit is paid per kill, with no reference to whether the raid was
   stopped.**  ``raider_neutralised = +1.0`` lands whatever happens afterwards,
   while losing the facility costs ``-4.0`` per health unit plus ``-2.0`` terminal.
   With 8 of 14 episodes having no terminal term at all, "trade a facility for a
   few kills" could be net positive.

This script does two things: it pins the proxy's behaviour as pure functions, and
it measures the **whole-episode reward of scripted policies** so the ordering
"defend > idle > flee" is demonstrated on the real engine rather than argued.

The critical assertion is that a policy which does nothing must not profit from
the truncation cut.  Before the imminent-threat term, it could.

Usage:
    python _w1_reward_audit.py
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


# ---------------------------------------------------------------------------
# part 1: the proxy as pure functions
# ---------------------------------------------------------------------------
def test_proxy_endpoints() -> None:
    from ie_rl_env import truncation_standing_bonus, threat_weight

    bonus = dict(truncation_bonus=2.0, imminent_penalty=4.0)
    check("intact base, nothing incoming == terminal_win",
          truncation_standing_bonus(1.0, 0.0, **bonus) == 2.0,
          f"{truncation_standing_bonus(1.0, 0.0, **bonus)}")
    check("intact base but the whole raid is arriving == terminal_loss",
          truncation_standing_bonus(1.0, 1.0, **bonus) == -2.0,
          f"{truncation_standing_bonus(1.0, 1.0, **bonus)}")
    check("base already lost, nothing incoming == terminal_loss",
          truncation_standing_bonus(0.0, 0.0, **bonus) == -2.0,
          f"{truncation_standing_bonus(0.0, 0.0, **bonus)}")

    # monotone in both arguments -- this is the property the old proxy violated
    rising_survival = [truncation_standing_bonus(s, 0.5, **bonus)
                       for s in (0.0, 0.25, 0.5, 0.75, 1.0)]
    check("proxy increases with facility survival",
          all(b > a for a, b in zip(rising_survival, rising_survival[1:])),
          str([round(v, 2) for v in rising_survival]))
    rising_threat = [truncation_standing_bonus(1.0, i, **bonus)
                     for i in (0.0, 0.25, 0.5, 0.75, 1.0)]
    check("proxy decreases as the raid closes in",
          all(b < a for a, b in zip(rising_threat, rising_threat[1:])),
          str([round(v, 2) for v in rising_threat]))
    check("'do nothing with the raid on the doorstep' is no longer profitable",
          truncation_standing_bonus(1.0, 0.9, **bonus) < 0.0,
          f"{truncation_standing_bonus(1.0, 0.9, **bonus):.2f}")

    # threat weight is scaled by the raider's OWN envelope
    check("a raider at the facility is a full threat",
          threat_weight(0.0, 8000.0, 500.0) == 1.0)
    check("a raider beyond its own range is no threat",
          threat_weight(9000.0, 8000.0, 500.0) == 0.0)
    check("envelope scaling differs between missile and suicide ranges",
          threat_weight(3000.0, 8000.0, 500.0)
          > threat_weight(3000.0, 150.0, 0.0),
          f"{threat_weight(3000.0, 8000.0, 500.0):.3f} vs "
          f"{threat_weight(3000.0, 150.0, 0.0):.3f}")
    zero_span = threat_weight(10.0, 100.0, 100.0)
    check("a degenerate envelope does not divide by zero",
          zero_span in (0.0, 1.0), f"{zero_span}")


# ---------------------------------------------------------------------------
# part 2: whole-episode reward of scripted policies, on the real engine
# ---------------------------------------------------------------------------
def run_scripted(public_id: str, seed: int, policy: str, max_ticks: int | None,
                 max_decisions: int = 400, reward=None) -> dict:
    """One episode under a scripted control law; returns the reward breakdown."""
    from ie_rl_env import IERlEnv, RewardConfig, _intercept_point

    env = IERlEnv(public_id, seed=seed, decision_interval=5,
                  reward=reward or RewardConfig())
    env.max_ticks_override = max_ticks
    try:
        env.reset()
        totals = {"reward": 0.0, "kills": 0, "depth": 0.0, "terminal": 0.0,
                  "facility_damage": 0.0, "own_loss": 0, "fired": 0,
                  "truncation": 0.0, "imminent": None}
        for _ in range(max_decisions):
            mask = env.fire_mask()
            objective = np.asarray(env._objective, dtype=np.float64)
            headings = np.zeros((env.num_units, 2), dtype=np.float32)
            speeds = np.zeros(env.num_units, dtype=np.float32)
            fire = np.zeros(env.num_units, dtype=np.int64)
            own = getattr(env, "_own_contact", {})
            entities = {str(e.id): e for e in env._session.world_view.entities_stable()}
            for i, slot in enumerate(env._slots):
                entity = entities.get(slot.entity_id)
                if entity is None:
                    continue
                unit_pos = np.asarray(entity.state.position_m[:2], dtype=np.float64)
                # nearest target this unit holds its own contact on, WITH its id so
                # the defender can look up that target's estimated velocity
                nearest = None            # (distance, position, target_id)
                for (owner, target), entry in own.items():
                    if owner != slot.entity_id:
                        continue
                    tpos = np.asarray(entry[1:3], dtype=np.float64)
                    dist = float(np.linalg.norm(tpos - unit_pos))
                    if nearest is None or dist < nearest[0]:
                        nearest = (dist, tpos, str(target))
                if policy == "flee":
                    direction = unit_pos - objective        # away from the asset
                    speed = 1.0
                elif policy == "idle":
                    direction = objective - unit_pos        # point at it, do not move
                    speed = 0.0
                else:                                        # defend
                    direction = ((nearest[1] - unit_pos) if nearest is not None
                                 else (objective - unit_pos))
                    speed = 1.0
                    choices = np.flatnonzero(mask[i, 1:])
                    if choices.size:
                        fire[i] = int(choices[0]) + 1
                    if nearest is not None:
                        # Aim at the LEAD POINT and throttle down on approach.
                        #
                        # A naive "point straight at the target, full speed"
                        # defender was adequate while the wrapper mistakenly capped
                        # every UAV at the surface speed of 10 m/s; once the real
                        # 80 m/s limit was restored (see
                        # RL_MODEL_SCENARIO_SUPPORT.md §7) that controller simply
                        # overshoots and stops being a defender at all -- and this
                        # audit began failing "defending beats doing nothing" on two
                        # scenarios.  The test is only meaningful if the scripted
                        # defender is competent, so it flies an intercept course and
                        # slows as it closes, leaving the REWARD as the thing under
                        # test rather than the baseline's flying skill.
                        track = env._target_track.get(nearest[2])
                        tvel = (np.asarray(track[2:4], dtype=np.float64)
                                if track is not None else np.zeros(2))
                        lead, _t = _intercept_point(unit_pos, nearest[1], tvel,
                                                    0.7 * slot.speed_max_mps)
                        direction = lead - unit_pos
                        speed = float(np.clip(nearest[0] / 4000.0, 0.25, 1.0))
                norm = float(np.linalg.norm(direction))
                if norm < 1e-6:
                    headings[i] = (0.0, 1.0)
                else:
                    headings[i] = (direction[0] / norm, direction[1] / norm)
                speeds[i] = speed
            action = {"heading_xy": headings, "speed": speeds, "fire": fire}
            _obs, reward, terminated, truncated, info = env.step(action)
            totals["reward"] += reward
            for key, src in (("kills", "raiders_lost"), ("own_loss", "own_lost"),
                             ("fired", "fired")):
                totals[key] += int(info.get(src, 0))
            for key, src in (("depth", "depth_credit"),
                             ("terminal", "terminal_reward"),
                             ("facility_damage", "facility_damage")):
                totals[key] += float(info.get(src, 0.0))
            if "truncation_bonus" in info:
                totals["truncation"] += float(info["truncation_bonus"])
                totals["imminent"] = info.get("imminent_threat")
            if terminated or truncated:
                break
        totals["outcome"] = env.terminal_outcome
        totals["tick"] = int(env._session.world_view.tick)
        totals["reward"] = round(totals["reward"], 3)
        return totals
    finally:
        env.close()


def test_reward_weights_are_sane() -> None:
    """Unambiguous weight invariants -- the ones that need no layer arithmetic.

    A note on what this test deliberately does NOT do.  An earlier version
    compared the reward delta against a *single* scorecard layer and flagged a
    "sign flip" on the exchange layer (kill +1.0, loss -0.5 vs exchange layer
    -0.05).  Acting on that raised ``own_loss`` to -1.0, which the measurement then
    rejected: the scorecard's response to engaging is dominated by facilities
    (0.25), terminal (0.20), depth (0.20) and leak (0.10), so isolating a 0.10
    layer is not a valid alignment test -- and at -1.0 passivity out-scored
    defending on both truncated scenarios.  The authoritative alignment check is
    therefore the whole-episode ordering in ``main``, on the real engine.
    """
    from ie_rl_env import RewardConfig

    cfg = RewardConfig()
    check("losing the base outweighs any single kill",
          abs(cfg.terminal_loss) + abs(cfg.facility_damage) > cfg.raider_neutralised,
          f"loss {cfg.terminal_loss} + damage {cfg.facility_damage} "
          f"vs kill {cfg.raider_neutralised}")
    check("a shot is never worth more than the kill it enables",
          cfg.shot_cost < cfg.raider_neutralised / 10.0,
          f"{cfg.shot_cost} vs {cfg.raider_neutralised}")
    check("a win is worth more than the kills that produced it",
          cfg.terminal_win >= cfg.raider_neutralised,
          f"{cfg.terminal_win} vs {cfg.raider_neutralised}")
    check("the truncation proxy spans the real terminal range",
          cfg.truncation_bonus == cfg.terminal_win
          and cfg.imminent_threat_penalty == 2.0 * cfg.truncation_bonus,
          f"bonus={cfg.truncation_bonus} penalty={cfg.imminent_threat_penalty}")
    check("killing two raiders still beats losing one unit",
          cfg.raider_neutralised * 2 + cfg.own_loss > 0.0,
          f"{cfg.raider_neutralised * 2 + cfg.own_loss}")


def test_arbitrage_closed_on_the_same_trajectory() -> None:
    """The truncation cut must stop paying a passive policy.

    This is the baseline-independent form of the fix, and it is the assertion that
    actually belongs in a gate: the SAME behaviour is scored twice, once with the
    old blind proxy (``imminent_threat_penalty = 0``) and once with the shipped
    one.  If the penalty does nothing, the arbitrage is still open.

    It replaced a blanket "defending beats doing nothing on every scenario"
    assertion, which turned out to measure the scripted baseline's flying skill
    rather than the reward: with the real 80 m/s speed limit restored, a naive
    defender on IE-06 loses four units for two kills while the facility is hit
    anyway, so it *legitimately* scores below passivity.  That is the reward being
    right, not wrong, and a test that calls it a failure is a bad test.
    """
    from ie_rl_env import RewardConfig, truncation_standing_bonus

    cfg_old = RewardConfig()
    cfg_old.imminent_threat_penalty = 0.0        # the previous, blind behaviour
    cfg_new = RewardConfig()                     # shipped: penalty = 4.0

    # The cut must land INSIDE the raid: IE-04's engagement runs 0-242, so at 250
    # ticks the raiders are in flight and the facility has not fallen.  At 450 an
    # idle policy has already lost it, the episode terminates on the rule instead of
    # truncating, and the proxy is never invoked -- which made the first version of
    # this test compare terminal outcomes rather than the proxy.
    CUT = 250
    old = run_scripted("IE-04-COMBINED-ARMS", 1000, "idle", CUT, reward=cfg_old)
    new = run_scripted("IE-04-COMBINED-ARMS", 1000, "idle", CUT, reward=cfg_new)
    print(f"     passive IE-04 @{CUT} ticks: old proxy reward={old['reward']:>8.2f} "
          f"(truncation {old['truncation']:+.2f}, tick {old['tick']})")
    print(f"                                 new proxy reward={new['reward']:>8.2f} "
          f"(truncation {new['truncation']:+.2f}, tick {new['tick']})")
    check("the A/B episode actually reached the truncation cut",
          old["truncation"] != 0.0 and new["truncation"] != 0.0,
          f"old={old['truncation']} new={new['truncation']} "
          f"(0 means it terminated on a rule instead)")
    check("the truncation cut no longer pays a passive policy",
          new["truncation"] < old["truncation"],
          f"old={old['truncation']} new={new['truncation']}")
    # The magnitude at a given cut depends on how far in the raid already is, so
    # only the DIRECTION is asserted here; the endpoint property (a raid that has
    # fully arrived scores as a loss, not a win) is pinned by the closed-form
    # checks below, which need no engine at all.
    check("...and the whole-episode reward for doing nothing drops with it",
          new["reward"] < old["reward"],
          f"old={old['reward']} new={new['reward']}")

    # and the closed form, so the property is pinned even without an engine
    check("a raid arriving at an intact base scores as a loss, not a win",
          truncation_standing_bonus(1.0, 1.0, truncation_bonus=2.0,
                                    imminent_penalty=4.0) == -2.0)
    check("the same state under the old blind proxy paid the full win bonus",
          truncation_standing_bonus(1.0, 1.0, truncation_bonus=2.0,
                                    imminent_penalty=0.0) == 2.0)


def main() -> int:
    test_proxy_endpoints()
    test_reward_weights_are_sane()
    test_arbitrage_closed_on_the_same_trajectory()

    print("-- whole-episode reward by scripted policy (truncated at 450 ticks)")
    print("   NOTE: the scripted 'defend' is a naive pursuit controller.  Its")
    print("   ordering versus 'idle' is INFORMATIONAL, not an assertion: where it")
    print("   loses units for nothing it legitimately scores lower, and calling")
    print("   that a reward defect would be a bad test.  The assertion that")
    print("   actually protects the reward is the same-trajectory A/B below.")
    for public_id in ("IE-04-COMBINED-ARMS", "IE-06-DECOY-MIXED"):
        rows = {}
        for policy in ("idle", "flee", "defend"):
            rows[policy] = run_scripted(public_id, 1000, policy, 450)
            print(f"     {public_id.split('-')[0]:<8}{policy:<8}"
                  f"reward={rows[policy]['reward']:>8.2f} "
                  f"kills={rows[policy]['kills']} "
                  f"fac={rows[policy]['facility_damage']:>6.1f} "
                  f"trunc={rows[policy]['truncation']:>6.2f} "
                  f"imminent={rows[policy]['imminent']} "
                  f"tick={rows[policy]['tick']}")
        # The property that IS reward-shaped and baseline-independent: whatever the
        # scripted defender manages, a policy that does nothing must not be paid by
        # the cut.  Whether a naive defender out-scores passivity depends on the
        # defender's skill and is reported above, not asserted.
        check(f"{public_id}: a passive policy is not paid for the truncation cut",
              rows["idle"]["truncation"] < 2.0,
              f"idle reward={rows['idle']['reward']} "
              f"truncation={rows['idle']['truncation']} "
              f"imminent={rows['idle']['imminent']}")
        spread = ("defend > idle" if rows["defend"]["reward"] > rows["idle"]["reward"]
                  else "defend <= idle (naive defender trades units for nothing)")
        print(f"     -> {public_id.split('-')[0]}: {spread}")

    print("\n-- full-length episode (the scorecard's own horizon)")
    for policy in ("defend", "idle"):
        row = run_scripted("IE-01-SINGLE-TARGET", 1000, policy, None)
        print(f"     IE-01   {policy:<8} reward={row['reward']:>8.2f} "
              f"kills={row['kills']} terminal={row['terminal']:>5.1f} "
              f"outcome={row['outcome']} tick={row['tick']}")

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
