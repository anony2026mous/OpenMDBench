"""Gate: the fire mask must agree with the units' REAL weapon envelopes.

Round-2 audit finding.  ``fire_mask`` used to test a hard-coded ``500 <= d <=
8000`` window for every slot.  That is the interceptor UAV's envelope; the armed
USV carries ``weapon.surface-missile`` with ``min_range_m = 0`` and
``max_range_m = 3000`` and ``target_domains = [surface]``.  Consequences:

  * every legal boat shot closer than 500 m was hidden from the policy, and
  * boat shots between 3000 m and 8000 m were offered even though the engine
    cannot execute them, and
  * an air-only interceptor was offered boats, which the engine rejects with
    ``combat.target_domain_denied`` -- the exact defect ``interception_graph``
    had already been fixed for in the rule/hybrid arms.

This checks the mask and the observation's "in envelope" feature against the
envelope read from each unit's own resolved weapon binding, on live scenarios.

Usage:
    python _w1_test_fire_envelope.py
"""
from __future__ import annotations

import math
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
    from ie_rl_env import IERlEnv

    for public_id in ("IE-03-SURFACE-RAID", "IE-04-COMBINED-ARMS"):
        print(f"-- {public_id}")
        env = IERlEnv(public_id, seed=7, decision_interval=5, max_ticks=120)
        try:
            env.reset()
            env.observe()                 # populates the contact snapshot
            by_class: dict[str, set] = {}
            for slot in env._slots:
                by_class.setdefault(slot.klass, set()).add(
                    (slot.min_range_m, slot.max_range_m, slot.target_domains))
            for klass, profiles in sorted(by_class.items()):
                print(f"     {klass:<8} " +
                      " | ".join(f"{lo:.0f}-{hi:.0f} {dom}"
                                 for lo, hi, dom in sorted(profiles)))
            check(f"{public_id}: every armed slot resolved a real envelope",
                  all(s.max_range_m > s.min_range_m
                      for s in env._slots if s.weapon_ref),
                  str([(s.entity_id, s.min_range_m, s.max_range_m)
                       for s in env._slots if s.weapon_ref
                       and s.max_range_m <= s.min_range_m]))
            check(f"{public_id}: surface slots and air slots differ in reach",
                  len({(s.min_range_m, s.max_range_m) for s in env._slots}) > 1,
                  "a single shared window means the envelope is still hard-coded")

            # every masked-on (unit, target) pair must satisfy the unit's OWN
            # envelope and domain pairing, and every pair inside the envelope with
            # an owned contact must be masked on
            mask = env.fire_mask()
            targets = env._last_contacts
            classes = env._last_contact_class
            own = env._own_contact
            entities = {str(e.id): e for e in env._session.world_view.entities_stable()}
            violations = []
            missing = []
            for i, slot in enumerate(env._slots):
                entity = entities.get(slot.entity_id)
                if entity is None:
                    continue
                pos = np.asarray(entity.state.position_m[:2], dtype=np.float64)
                for j, target in enumerate(targets):
                    entry = own.get((slot.entity_id, str(target)))
                    if entry is None:
                        continue
                    dist = float(np.hypot(entry[1] - pos[0], entry[2] - pos[1]))
                    inside = (slot.min_range_m <= dist <= slot.max_range_m)
                    from ie_rl_env import _domain_pairing_allowed
                    dom_ok = _domain_pairing_allowed(
                        slot.target_domains, classes[j]) if j < len(classes) else True
                    should = inside and dom_ok
                    got = bool(mask[i, j + 1])
                    if got and not should:
                        violations.append((slot.entity_id, target, round(dist),
                                           slot.min_range_m, slot.max_range_m))
                    if should and not got:
                        missing.append((slot.entity_id, target, round(dist)))
            check(f"{public_id}: no masked-on shot is outside its own envelope "
                  f"or domain", not violations, str(violations[:4]))
            check(f"{public_id}: no in-envelope owned shot is masked off",
                  not missing, str(missing[:4]))

            # the observation's "in envelope" flag must equal the mask
            # The pair block's width is a property of the layout, not a constant: it
            # grew from 6 to 8 when the lead-point bearing was added, and this slice
            # used to hard-code 6.  Read it from the env so a future layout change
            # fails loudly here instead of silently reshaping the wrong bytes.
            obs = env.observe()
            pair = obs[6 + env.num_units * 10 + env.max_contacts * 7:].reshape(
                env.num_units, env.max_contacts, env.pair_width)
            mismatch = 0
            for i, slot in enumerate(env._slots):
                for j in range(len(targets)):
                    if abs(float(pair[i, j, 3]) - float(mask[i, j + 1])) > 1e-6:
                        mismatch += 1
            check(f"{public_id}: observation 'in envelope' flag matches the mask",
                  mismatch == 0, f"{mismatch} disagreeing entries")
        finally:
            env.close()

    # regression guard: the old hard-coded window must not come back
    source = (Path(__file__).resolve().parent / "ie_rl_env.py").read_text(
        encoding="utf-8")
    body = source.split("def fire_mask")[1].split("def ")[0]
    check("fire_mask no longer contains a hard-coded 8000 m window",
          "8000" not in body, "found an 8000 literal inside fire_mask")

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
