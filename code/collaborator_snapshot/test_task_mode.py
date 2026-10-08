"""Quick behavioral check for task_mode standoff gates (§4.5)."""
import sys

sys.path.insert(0, ".")
from grid_env.grid_env import GridEnv, EntityType

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    print(f"  {'PASS' if cond else 'FAIL'}: {name}")
    PASS += int(cond)
    FAIL += int(not cond)


def standoff_attempt(mode, mark_target=False, active_lock=False):
    """Place red at Chebyshev 3 from USV0, try intercept, return intercepted."""
    env = GridEnv(difficulty="complex", seed=7, task_mode=mode)
    red = next(iter(env.red_units))
    usv = env.blue_units[0]
    env.entities[usv].x, env.entities[usv].y = 10, 10
    env.entities[red].x, env.entities[red].y = 13, 10  # Chebyshev 3, standoff
    if mark_target:
        env.handed_over_targets.add(red)
    if active_lock:
        from grid_env.grid_env import LockState
        env.lock = LockState(target_id=red, age=5, acquired=True)
    env.entities[usv].ammo = 5
    env._attempt_intercept(usv)
    return not env.entities[red].alive


print("== independent: no gate ==")
check("no lock, no mark -> intercept OK", standoff_attempt("independent"))
print("== sequential: persistent mark gate ==")
check("no mark -> blocked", not standoff_attempt("sequential"))
check("marked -> intercept OK", standoff_attempt("sequential", mark_target=True))
print("== continuous: active lock gate (v2 default) ==")
check("no lock -> blocked", not standoff_attempt("continuous"))
check("marked but no active lock -> blocked (mark is not enough)",
      not standoff_attempt("continuous", mark_target=True))
check("active lock -> intercept OK", standoff_attempt("continuous", active_lock=True))

# regression: default constructor unchanged
env = GridEnv(difficulty="simple", seed=1)
check("default task_mode is continuous", env.task_mode == "continuous")
m = GridEnv(difficulty="simple", seed=1).get_episode_metrics()
check("metrics expose task_mode", m.get("task_mode") == "continuous")
obs = env._get_observation("blue")
check("obs exposes task_mode",
      obs["situational_data"].get("task_mode") == "continuous")
check("situational report mentions guidance",
      "lock" in env._generate_situational_report().lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
