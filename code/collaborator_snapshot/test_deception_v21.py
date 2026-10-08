"""v2.1 deception-mechanism regression tests (reviewer concern C2).

Verifies that the feint/deception gamble has real game consequences and
that intent inference is routed through OBSERVABLE cues only:

1.  A real-threat transport entering the port counts as a penetration.
2.  Intercepting a friendly (feint) transport is allowed but penalised
    (neutral_intercepted metric + -30 reward delta).
3.  Red contacts expose an observable `heading` step-delta (never the
    hidden is_real_threat flag).
4.  Feint transports drift laterally; genuine ones close on the port.
5.  The UAV auto-lock preference uses only the observed type, never the
    hidden threat flag.
6.  The situational report describes transport kinematics in NL.
"""

from grid_env.grid_env import GridEnv, EntityType, PORT_AREA, Direction


def _complex_env(seed: int = 7) -> GridEnv:
    env = GridEnv(difficulty="complex", seed=seed)
    # Waves 1+ carry the transports (wave 0 is combatant-heavy); spawn
    # them up-front so every test can locate both feints and threats.
    for w in range(1, env.wave_count):
        env._spawn_wave(w)
    return env


def _find(env: GridEnv, et: EntityType, threat: bool = None):
    for uid in env.red_units:
        e = env.entities[uid]
        if e.entity_type == et and e.alive:
            if threat is None or e.is_real_threat == threat:
                return uid, e
    return None, None


def _ensure(env: GridEnv, et: EntityType, threat: bool):
    """Return one entity of the type, FORCING the hidden threat flag.

    v2.1.2 has only 2 transports split across waves (50% threat each), so
    a specific class may be absent under a given seed; the mechanism
    tests below care about the BRANCHES, not the spawn distribution.
    """
    uid, e = _find(env, et)
    if e is None:
        return None, None
    e.is_real_threat = threat
    return uid, e


def test_real_threat_transport_penetrates():
    """A genuine transport that reaches the port must count as penetration."""
    env = _complex_env()
    uid, e = _ensure(env, EntityType.RED_TRANSPORT, threat=True)
    assert e is not None, "no transport spawned"
    e.x, e.y = list(PORT_AREA)[0]
    before = env.metrics["red_units_entered_port"]
    env._check_port_penetration()
    assert env.metrics["red_units_entered_port"] == before + 1, \
        "real-threat transport in port must count as a penetration"


def test_feint_transport_no_penetration():
    """A feint transport in the port does NOT count (harmless by design)."""
    env = _complex_env()
    uid, e = _ensure(env, EntityType.RED_TRANSPORT, threat=False)
    assert e is not None, "no transport spawned"
    e.x, e.y = list(PORT_AREA)[0]
    before = env.metrics["red_units_entered_port"]
    env._check_port_penetration()
    assert env.metrics["red_units_entered_port"] == before, \
        "feint transport must not inflate penetration count"


def test_intercept_feint_penalised():
    """Firing on a feint transport: allowed, recorded, -30 reward."""
    env = _complex_env()
    usv_uid = env.usv_units[0]
    usv = env.entities[usv_uid]
    uid, e = _ensure(env, EntityType.RED_TRANSPORT, threat=False)
    assert e is not None, "no transport spawned"
    # Place adjacent so the intercept resolves (within ROE range)
    usv.x, usv.y = e.x + 1, e.y
    env.entities[usv_uid].ammo = 2

    env._prev_metrics = dict(env.metrics)
    env._attempt_intercept(usv_uid)
    assert not e.alive, "intercept on feint transport must be executed"
    assert env.metrics["neutral_intercepted"] == 1
    r = env.compute_reward("blue")
    assert r <= -30.0 + 1e-6, f"expected ≈-30 own-goal penalty, got {r}"


def test_heading_cue_observable_no_truth_leak():
    """Red contacts carry a heading step-delta; never is_real_threat."""
    env = _complex_env()
    # Teleport a USV next to a transport so the contact is detected
    uid, e = _find(env, EntityType.RED_TRANSPORT)
    usv = env.entities[env.usv_units[0]]
    usv.x, usv.y = e.x + 1, e.y
    env.step({"blue": {env.usv_units[0]: int(Direction.STAY)}})
    obs = env._get_observation()
    contacts = obs["situational_data"]["detected_contacts"]
    assert contacts, "expected at least one detected contact"
    for c in contacts:
        assert "is_real_threat" not in c, "ground-truth flag leaked into obs"
    tr = [c for c in contacts if "transport" in c["type"]]
    assert tr and "heading" in tr[0], "transport contact must expose heading"


def test_feint_behaviour_diverges():
    """Statistically: feints drift away from port; genuine close in."""
    env = _complex_env(seed=11)
    real, feint = [], []
    for _ in range(30):
        env.step({"blue": {env.usv_units[0]: int(Direction.STAY)}})
        for uid in env.red_units:
            e = env.entities[uid]
            if not e.alive or e.entity_type != EntityType.RED_TRANSPORT:
                continue
            d = abs(e.x - 1) + abs(e.y - 18)  # Manhattan distance to port
            (real if e.is_real_threat else feint).append(d)
    # Compare first vs last half for each class via simple means
    mid = len(real) // 2
    real_drift = sum(real[mid:]) / max(1, len(real) - mid) - sum(real[:mid]) / max(1, mid)
    midf = len(feint) // 2
    feint_drift = sum(feint[midf:]) / max(1, len(feint) - midf) - sum(feint[:midf]) / max(1, midf)
    assert real_drift < feint_drift, (
        f"genuine transports should close on port faster than feints "
        f"(real Δ={real_drift:.2f}, feint Δ={feint_drift:.2f})")


def test_lock_ignores_hidden_threat_flag():
    """Auto-lock prefers OBSERVED combatants; nearest wins otherwise —
    never the hidden is_real_threat."""
    env = _complex_env()
    uav = env.entities[env.uav_id]
    near_uid, near = _ensure(env, EntityType.RED_TRANSPORT, threat=True)
    assert near is not None, "no transport spawned"
    # Park UAV+transport at the port corner: every scripted red spawn
    # lies on the east/south edges, far outside the UAV's range-8 vision,
    # so the only visible candidate is the teleported transport.
    uav.x, uav.y = 0, 19
    near.x, near.y = 1, 19
    env._update_locks()
    assert env.lock is not None and env.lock.target_id == near_uid, \
        "with no combatant visible, the nearest transport must be locked"

    # Now bring ONE combatant into view: observed-type preference wins
    # over the transport regardless of the hidden threat flag.
    combatants = [uid for uid in env.red_units
                  if env.entities[uid].entity_type == EntityType.RED_COMBATANT]
    c_uid = combatants[0]
    env.entities[c_uid].x, env.entities[c_uid].y = 2, 19
    env._update_locks()
    assert env.lock.target_id == c_uid, \
        "combatant (observed type) must take lock priority over transport"


def test_report_mentions_kinematics():
    """NL report describes transport movement without ground truth."""
    env = _complex_env(seed=3)
    # Teleport a USV next to a transport for guaranteed visibility
    uid, e = _find(env, EntityType.RED_TRANSPORT)
    assert e is not None
    usv = env.entities[env.usv_units[0]]
    usv.x, usv.y = min(19, e.x + 1), e.y
    env.step({"blue": {env.usv_units[0]: int(Direction.STAY)}})
    rep = env._generate_situational_report()
    ok = ("Transport" not in rep) or ("closing on port" in rep
                                      or "moving away/lateral" in rep)
    assert ok, f"report must label transport kinematics or see none: {rep}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as ex:
            print(f"  FAIL: {t.__name__}: {ex}")
    print(f"\n{passed}/{len(tests)} passed")
    raise SystemExit(0 if passed == len(tests) else 1)
