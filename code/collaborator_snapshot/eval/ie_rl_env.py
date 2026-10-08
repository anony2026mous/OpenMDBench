"""Multi-unit Gymnasium-style environment for the IE interception scenarios.

Why this file exists
--------------------
The engine ships ``openmdbench.envs.OpenMDBenchEnv``, but its action space is a
single ``Box([speed, heading])`` driving **one** "primary compatibility entity"
(``envs/benchmark.py``: ``primary_entity_id`` / ``compatibility_goal``).  The IE
scenarios need 12+ friendly units (9 interceptor UAVs + 3 armed USVs) so that
environment cannot express them.  This wrapper drives every mobile friendly
entity through the public session API instead.

Information parity (hard requirement)
-------------------------------------
The rule / hybrid-LLM / pure-LLM arms do not plan from the bare ``ObservationV2``:
``v2_agent.AgentV2._refresh_unit_roles`` additionally hands every planner

    _unit_roles : entity_id -> frozenset(tags)     (who is armed / air / surface)
    _meta       : entity_id -> live entity object  (live ammunition, bindings)

The bare observation carries **no ammunition and no tags** (verified with
``_w1_obs_probe.py``).  The RL observation therefore concatenates the
faction-filtered ``ObservationV2`` with the same own-side metadata, and nothing
else:

    * giving less would cripple the RL arm relative to the others;
    * giving more (truth positions of intruders) would be cheating.

Red is driven by the very same ``AttackProfileDriverV2`` the other arms use, so
the threat behaves identically across arms.

Control level
-------------
The network's output *is* the action: per unit an absolute heading, an absolute
speed in m/s, and an optional fire target.  There is no goal abstraction, no
executor, no rule fallback and no second network -- the wrapper only encodes the
observation and decodes the numbers into the two engine messages the interface
requires (``navigation`` + ``fire_weapon``).  Absolute heading/speed rather than
deltas also breaks the previous slow wrap-around: a delta head had to be applied
every decision just to hold a course.

Usage:
    env = IERlEnv("IE-01-SINGLE-TARGET", seed=7)
    obs, info = env.reset()
    obs, reward, terminated, truncated, info = env.step(action)
"""
from __future__ import annotations

import math
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_EVAL = str(Path(__file__).resolve().parent)
if _EVAL not in sys.path:
    sys.path.insert(0, _EVAL)

# Position scale: the shared map spans about 60 km, and the longest ingress in
# the IE set is 30 km, so this keeps normalised coordinates in a sane range.
POS_SCALE_M = 40000.0
# Target slots for the fire head.  The engine publishes one contact per
# (observer, target) pair, so the raw list is observers x targets (up to ~200
# entries).  Slots are therefore keyed by **distinct target**, unranked, and the
# per-unit mask decides which of them that unit may actually shoot at.  This
# removes the previous "rank by distance to the objective, keep top 8" prior,
# which was the wrapper silently choosing candidate targets for the network.
MAX_CONTACTS = 20
# Fixed unit-slot capacity.  The scenarios need 5..12 controllable units, and a
# policy whose input/output shape is tied to one scenario's roster **cannot be
# evaluated on the others at all** (measured: an IE-01 policy, obs_dim 410,
# aborts on IE-02 with "size 410 is different from 352").  Padding every
# scenario to the same slot count makes one checkpoint run all eight, which is
# the whole point of the four-arm comparison.
MAX_UNITS = 16
# FALLBACK ONLY -- used when a unit's dynamics binding carries no
# ``max_speed_mps``.  The real value must come from the catalog, and the numbers
# here are deliberately marked as approximate: a hard-coded 43.0 for "air" was
# wrong for these scenarios (the interceptor UAV's truth is 80.0), which is the
# third place this same mistake appeared -- see ``_platform_profile`` and
# ``legacy_executor_speed``.  Prefer a fallback that is obviously a guess over one
# that looks authoritative.
SPEED_BY_CLASS = {"air": 50.0, "surface": 10.0}
# Width of the per-unit goal feature block, used only by the fifth arm
# (LLM plan + RL executor).  Imported from the encoder so the two cannot drift.
try:
    from ie_goal_features import PER_UNIT_WIDTH as GOAL_FEATURE_WIDTH
except Exception:  # pragma: no cover - encoder is optional for the other arms
    GOAL_FEATURE_WIDTH = 24


@dataclass
class RewardConfig:
    """Training reward.  Deliberately NOT the scorecard.

    The scorecard is the *evaluation* instrument and stays untouched; this is a
    dense training signal that shadows it.  The mapping is documented so the two
    can never silently drift apart:

        def scorecard_layer      -> reward term
        terminal             -> ``terminal_win`` / ``terminal_loss``
                                (and ``truncation_standing_bonus`` when the episode
                                 is cut short before the terminal rule can latch --
                                 the proxy now spans the same +-2.0 range, including
                                 the share of the raid that is about to land)
        facilities           -> ``facility_damage`` (per unit of health lost)
        exchange             -> ``own_loss`` / ``raider_neutralised``
        depth                -> ``depth_bonus`` (scaled by reference depth)
        ammo                 -> ``shot_cost`` (charged per executed shot)
        leak / surface       -> covered by ``raider_neutralised`` (a leaker is a
                                raider that was not neutralised) and, at the
                                truncation cut, by ``imminent_threat_penalty``
    """

    terminal_win: float = 2.0
    terminal_loss: float = -2.0
    raider_neutralised: float = 1.0
    facility_damage: float = -4.0
    # Loss of one friendly unit.
    #
    # I first "fixed" a sign disagreement here by raising this from -0.5 to -1.0:
    # ``raider_neutralised = +1.0`` made a 1-for-1 trade worth +0.5, while the
    # scorecard's ``exchange`` layer (defender_kills/defender_losses against a
    # reference of 2.0) scores a 1-for-1 trade at 0.5 of a 0.10 layer, i.e. -0.05.
    #
    # That reasoning was wrong, and the measurement said so: comparing a single
    # layer in isolation is not a valid alignment test, because the scorecard's
    # response to *engaging at all* is dominated by facilities (0.25), terminal
    # (0.20), depth (0.20) and leak (0.10) -- the exchange layer is 0.10.  At -1.0
    # the whole-episode ordering inverted and **passivity out-scored defending on
    # both truncated scenarios** (IE-04: idle -6.95 vs defend -9.10; IE-06:
    # idle -5.82 vs defend -6.89), which is the same failure by a different route:
    # defending costs units, and paying a full kill's worth per unit makes
    # defending a losing move.  On the full-length scenario defending won either
    # way (IE-01: defend -4.76 vs idle -6.00).
    #
    # -0.5 is kept, and the arbitrage it supposedly created is closed by the
    # imminent-threat term instead -- measured: with the proxy fixed, defend beats
    # idle beats flee on both truncated scenarios, and a passive policy's
    # truncation term is -1.82..-1.95 rather than the +2.0 it used to collect.
    own_loss: float = -0.5
    depth_bonus: float = 0.5          # max, at or beyond reference depth
    depth_reference_m: float = 20000.0
    # Charged per executed shot.  Kept deliberately small: at 0.02 with a
    # kill worth 1.0 the trade is still clearly profitable in expectation
    # (1.33 shots per neutralisation => 0.027 cost), but the penalty lands
    # immediately while the reward is delayed, which is exactly the shape that
    # lets a policy collapse onto "never fire".  Measured: at 0.02 the fire head
    # collapsed to entropy ~0.25 of a possible ln(9)=2.2 within 8 iterations.
    shot_cost: float = 0.005
    time_penalty: float = 0.0
    # Truncated episodes never reach the scenario's terminal rule (IE-01's
    # defence-success only latches at tick 899), so without this the sparse
    # terminal signal would be *entirely absent* in training and the agent would
    # only ever see dense shaping.  At truncation we therefore score the current
    # standing on exactly the quantity the ``facilities`` layer measures:
    # facility survival, centred so intact = +bonus and destroyed = -bonus.
    truncation_bonus: float = 2.0
    # ...but scoring *only* facility health made the cut blind to a raid that was
    # seconds from landing, and that blindness was worth 8 of 14 training
    # episodes.  Measured consequence (recorded run notes, s1 experiment): the
    # training reward rose 5.08 -> 7.86 across 30 iterations while IE-01's
    # scorecard fell 0.2689 -> 0.1312 with all seven layers degrading at once --
    # the agent had learned to let raiders close in the truncated scenarios
    # ("they arrive, the episode ends, I still collect +2.0") and pay for it on
    # the one scenario it could not trade away.
    #
    # ``imminent_threat_penalty`` subtracts the share of the raid that is already
    # inside its own weapon envelope of a protected facility, weighted by how far
    # in it has closed.  The default 4.0 = 2 x ``truncation_bonus`` is chosen so
    # the proxy spans exactly the real terminal range:
    #     all raiders destroyed            -> +2.0  (= terminal_win)
    #     all raiders arriving, intact base-> -2.0  (= terminal_loss)
    imminent_threat_penalty: float = 4.0
    # ---- goal-conditioned shaping (fifth arm only) ---------------------
    #
    # WHY THIS EXISTS.  Measured on `theta_arm5_v2`, which was trained with the plan
    # block as a plain input: zeroing the whole block moved the commanded heading by
    # only 7-8 deg, while the policy's own action noise sigma is 12.8 deg, and
    # removing the much wider pair block moved it 14-30 deg
    # (`_w1_policy_input_attribution.py`).  In other words the network received the
    # plan and steered almost as if it had not.  That is not a bug in the encoder
    # (every live unit does get its target -- measured 1.000); it is what the
    # objective rewards: the mission reward is indifferent to *which* raider a unit
    # is told to take, so nothing ever pushed gradient into the plan block.
    #
    # A fine-tune cannot fix that, which is why the three-hour LLM-goal run was
    # stopped before it finished an iteration.
    #
    # THE FIX is the potential-based form (Ng, Harada & Russell 1999):
    #
    #     Phi(s) = -sum_units dist(unit, its ASSIGNED target) / POS_SCALE
    #     r_shape = weight * (Phi(s') - Phi(s))
    #
    # Potential-based shaping leaves the optimal policy of the underlying MDP
    # unchanged, so this cannot teach blind obedience -- it cannot make a tactically
    # bad plan good.  What it does do is make the *assignment itself* reward
    # relevant: closing on the target the plan named now pays, so the policy has a
    # reason to read the plan and to distinguish one assignment from another.
    #
    # Only distances to the unit's OWN contact estimate are used, so no truth leaks
    # in (the same information set the encoder uses).
    # CALIBRATION.  The first attempt used 0.25 and a 3-iteration probe measured the
    # plan block's influence on the commanded heading **falling** (IE-01 7.2 -> 5.6
    # deg, IE-05 8.0 -> 4.9 deg) rather than rising: the shaped term totalled only
    # 0.06-0.13 against a return of ~6, i.e. 1-2%, which is not gradient pressure.
    # Compare with the terms the policy already responds to: a kill is 1.0, the
    # terminal bonus is 2.0, a facility loss is up to 4.0.  The weight is therefore
    # set so a fully-executed plan is worth roughly one kill, and the cap so two
    # kills' worth is the most this term can ever contribute.
    goal_progress_bonus: float = 2.0
    # Per *executed* shot whose target is the unit's assigned target, paid at most
    # ``goal_shot_budget`` times per (unit, target).  The fire head is where "execute
    # the plan" is most tactical, and it is otherwise indifferent between two raiders
    # that are equally shootable.
    goal_shot_bonus: float = 0.15
    # How many shots at one (unit, target) the bonus will pay for.  Kept equal to the
    # executor's ``overkill_cap`` (2), because that is exactly the salvo the doctrine
    # considers legitimate: paying for the second shot is paying for kill probability
    # (one shot 0.5, two 0.75), not for spray.  Measured: cutting the bonus to *once*
    # per target made both cheap scenarios grow a failure tail (IE-01 sd 0.0002 ->
    # 0.138, with a 0.663 reading) even though doctrine was unchanged.
    goal_shot_budget: int = 2
    # Episode cap on the whole goal-shaped credit.  The progress term is dense (per
    # unit per tick) and a long episode could otherwise accumulate more from flying
    # towards a distant assigned target than from winning, which would trade the
    # mission for the shaping.
    goal_credit_cap: float = 2.5


@dataclass
class Slot:
    """One fixed friendly-unit slot in the observation / action layout."""

    entity_id: str
    klass: str                     # "air" | "surface" | ... from the entity domain
    weapon_ref: str
    ammo_full: int
    # Real weapon envelope and allowed target domains, read from the unit's own
    # resolved weapon binding.  These are **not** constants: the interceptor UAV
    # carries 500-8000 m against air, while the armed USV carries 0-3000 m
    # against surface only.  A single hard-coded window (the previous 500-8000)
    # hid every legal boat shot under 500 m and offered boat shots the engine
    # cannot execute beyond 3000 m, and ignored the domain pairing entirely.
    min_range_m: float = 0.0
    max_range_m: float = 0.0
    target_domains: tuple[str, ...] = ()
    # Physical speed limit from this unit's own dynamics binding.  Also not a
    # constant -- see ``_platform_profile``.
    speed_max_mps: float = 40.0
    # Weapon cooldown from the catalog, used by the fire mask.
    cooldown_ticks: int = 0
    # Ticks for this unit's guided round to fly its full envelope, from the catalog
    # (``ceil(max_range_m / cruise_speed_mps)``).  A shot's outcome is unknown until
    # the round arrives, so any "assess the salvo" doctrine must wait at least this
    # long; the surface missile needs ~200 ticks against 12 for the air rounds.
    flight_ticks: int = 0


def _normalise_domain(raw: Any) -> str:
    """'Domain.AIR' / 'air' / None -> 'air'."""
    text = str(raw or "").strip().split(".")[-1].lower()
    return text if text and text != "none" else ""


def legacy_executor_speed(entity) -> float:
    """The speed the RULE executor would command for this entity.

    Read from ``ExecutorConfigV2.speed_by_tag`` rather than re-typed here, so the
    two layers cannot drift apart: that table is keyed on tags and gives air units
    40 m/s while the catalog says 80, and surface units 8 while the catalog says
    10.  Measured on IE-01 (``ARM5_LLM_RL_EXECUTOR_DESIGN.md`` §3.1):

        defender.uav-01..04  tags ('defence','combat-unit','interceptor')
                             executor 40.0  vs catalog 80.0   (2x)
        defender.usv-01..02  tags ('defence','combat-unit','usv','surface')
                             executor  8.0  vs catalog 10.0   (1.25x)

    It survives the ``uav`` tag trap only because of the ``interceptor`` fallback
    key, at the cost of using half the physical envelope for every air unit.  That
    is a pre-existing handicap on the recorded rule / hybrid / pure-LLM baselines,
    and it is why ``speed_source`` exists: comparing an executor that reads the
    catalog against one that reads this table would measure the table, not the
    executor.
    """
    try:
        from v2_executor import ExecutorConfigV2
        table = ExecutorConfigV2(faction_id="").speed_by_tag
    except Exception:  # noqa: BLE001
        table = {"uav": 40.0, "usv": 8.0, "interceptor": 40.0, "picket": 8.0}
    tags = tuple(getattr(entity, "tags", ()) or ())
    for key in ("uav", "usv", "interceptor", "picket"):
        if key in tags:
            return float(table.get(key, 12.0))
    return float(table.get("default", 12.0))


def _platform_profile(entity) -> tuple[str, float]:
    """(domain, physical max speed) from the entity's own resolved bindings.

    Both numbers are read from the catalog rather than guessed, because the
    previous tag heuristic (``"uav" in tags``) was simply wrong for these
    scenarios: ``defender.uav-01`` carries the tags
    ``('defence', 'combat-unit', 'interceptor')`` -- **no 'uav' tag** -- so every
    interceptor UAV was classified ``surface`` and capped at the surface speed of
    10 m/s instead of its real 43 m/s.  The observation's air/surface feature was
    therefore constant zero, and the wrapper handicapped every air unit by more
    than 4x in every training run and every evaluation.  It also plausibly
    explains the weak ``depth`` layer: an interceptor limited to 10 m/s cannot run
    down a 43 m/s intruder, so it can only engage on the doorstep.

    Reading ``max_speed_mps`` from the dynamics binding means the speed scale
    follows the scenario instead of a table that has to be kept in sync.
    """
    definition = getattr(entity, "definition", None)
    bindings = getattr(definition, "resource_bindings", None) or {}
    domain = _normalise_domain(getattr(definition, "domain", None))
    if not domain:
        for binding in bindings.get("platforms", ()) or ():
            content = (getattr(binding, "normalized_content", None)
                       or getattr(binding, "content", None) or {})
            domain = _normalise_domain(content.get("domain"))
            if domain:
                break
    speed = 0.0
    for binding in bindings.get("dynamics", ()) or ():
        content = (getattr(binding, "normalized_content", None)
                   or getattr(binding, "content", None) or {})
        try:
            speed = max(speed, float(content["max_speed_mps"]))
        except (KeyError, TypeError, ValueError):
            continue
    if speed <= 0.0:
        speed = SPEED_BY_CLASS.get(domain, 40.0)
    return domain or "surface", speed


def _weapon_profile_for(entity) -> tuple[Optional[str], float, float, tuple[str, ...]]:
    """(weapon_ref, min_range_m, max_range_m, target_domains) from the bindings."""
    ref, lo, hi, domains, _cool, _flight = _weapon_profile_full(entity)
    return ref, lo, hi, domains


def _weapon_profile_full(entity) -> tuple[Optional[str], float, float,
                                          tuple[str, ...], int, int]:
    """As above plus ``cooldown_ticks``, read from the catalog rather than assumed.

    Cooldown is currently non-binding -- every blue weapon in both bundles has
    ``cooldown_ticks`` of 0, 3 or 5 against a decision interval of 5, so a unit can
    fire at most once per decision anyway (verified from ``ie_set.yaml`` and
    ``md_ad_006.yaml`` in audit round 3).  It is read anyway because "the numbers
    happen to line up today" is exactly how the speed table and the 500-8000 m
    envelope became bugs: the moment a scenario ships a weapon with a longer
    cooldown, the mask would offer a choice the engine rejects and the policy would
    be charged for a shot that never happened.
    """
    definition = getattr(entity, "definition", None)
    bindings = getattr(definition, "resource_bindings", None) or {}
    for binding in bindings.get("weapons", ()) or ():
        ref = getattr(binding, "exact_ref", None)
        if not ref:
            continue
        content = (getattr(binding, "normalized_content", None)
                   or getattr(binding, "content", None) or {})
        try:
            lo = float(content["min_range_m"])
            hi = float(content["max_range_m"])
        except (KeyError, TypeError, ValueError):
            continue
        domains = tuple(str(item) for item in (content.get("target_domains") or ()))
        try:
            cooldown = int(content.get("cooldown_ticks") or 0)
        except (TypeError, ValueError):
            cooldown = 0
        # Flight time of a guided round at full range, in ticks.
        #
        # Every weapon in this bundle is ``delivery_model: guided_missile`` and the
        # engine flies the round rather than rolling a hit at launch
        # (`combat/system_v2.py` stages a ``MissileFlightV2``), so a shot's outcome is
        # unknown until the round arrives.  The speeds differ by an order of magnitude:
        # the air rounds cruise at 250-320 m/s (25-32 ticks to 8000 m) while the
        # surface missile does 15 m/s (200 ticks to 3000 m).  A flat 12-tick "assess"
        # window is therefore 16x too short on the surface round: measured on IE-03,
        # a release keyed to 12 ticks fired 8 extra missiles into boats whose first
        # salvo was still in the air, taking the ammo layer from 1.0 to 0.429.
        flight_ticks = 0
        missile = content.get("missile")
        # ``normalized_content`` is a ``mappingproxy``, not a dict -- an
        # ``isinstance(..., dict)`` test silently reports "no missile block" for every
        # weapon in the bundle (measured: flight_ticks came out 0 for the surface
        # missile, which is exactly the value the doctrine fix depends on).
        if isinstance(missile, Mapping):
            try:
                cruise = float(missile.get("cruise_speed_mps") or 0.0)
                launch = float(missile.get("launch_speed_mps") or 0.0)
                speed = max(cruise, launch)
                if speed > 0.0:
                    flight_ticks = int(math.ceil(hi / speed))
            except (TypeError, ValueError):
                flight_ticks = 0
        if hi > lo:
            return str(ref), lo, hi, domains, max(0, cooldown), flight_ticks
    return None, 0.0, 0.0, (), 0, 0


def _weapon_ref_for(entity) -> Optional[str]:
    """First weapon the entity can fire (from its resolved resource bindings)."""
    return _weapon_profile_for(entity)[0]


def _ammo_total(entity) -> int:
    state = getattr(entity, "state", None)
    ammo = dict(getattr(state, "ammunition", {}) or {})
    return int(sum(int(v) for v in ammo.values()))


def truncation_standing_bonus(survival: float, imminent: float, *,
                              truncation_bonus: float,
                              imminent_penalty: float) -> float:
    """Terminal substitute for an episode cut before its rule can latch.

    A pure function on purpose: this is the term whose blindness was worth 8 of 14
    training episodes, so its behaviour is pinned by a unit test rather than
    trusted.

    ``survival`` = facility health share in [0, 1]; ``imminent`` = share of the
    raid already inside its own weapon envelope of a protected facility, weighted
    by how far in it has closed, in [0, 1].

    Endpoints (with the shipped defaults truncation_bonus=2.0,
    imminent_penalty=4.0 -- the 2x ratio is what makes the proxy span the real
    terminal range)::

        survival=1, imminent=0  -> +2.0   equals terminal_win
        survival=1, imminent=1  -> -2.0   equals terminal_loss
        survival=0, imminent=0  -> -2.0   base lost, nothing left incoming

    Without the ``imminent`` term the first row was paid even when every raider
    was parked on the doorstep, which is the arbitrage that trained IE-01 from
    0.2689 down to 0.1312.
    """
    standing = truncation_bonus * (2.0 * float(survival) - 1.0)
    return standing - imminent_penalty * float(imminent)


def _intercept_point(unit_pos: np.ndarray, target_pos: np.ndarray,
                     target_vel: np.ndarray,
                     unit_speed: float) -> tuple[np.ndarray, float]:
    """Lead point: where to fly to meet the target, and the time to get there.

    Solves ``|R + V t| = s t`` for the smallest positive ``t`` (``R`` = target -
    unit, ``V`` = target velocity, ``s`` = unit speed), i.e. the classic
    collision-course triangle a fire-control computer solves.  Falls back to the
    target's current position when the target is faster than the unit and
    receding, which has no positive solution -- aiming at where it is beats
    aiming at a point that does not exist.

    Pure and side-effect free so it can be unit-tested; the training signal
    depends on this being right, and a wrong lead point is indistinguishable from
    a bad policy once the returns are noisy.
    """
    rel = np.asarray(target_pos, dtype=np.float64) - np.asarray(unit_pos,
                                                                dtype=np.float64)
    vel = np.asarray(target_vel, dtype=np.float64)
    speed = max(float(unit_speed), 1e-6)
    a = float(vel @ vel) - speed * speed
    b = 2.0 * float(rel @ vel)
    c = float(rel @ rel)
    best = None
    if abs(a) < 1e-9:
        if abs(b) > 1e-9:
            candidate = -c / b
            if candidate > 0.0:
                best = candidate
    else:
        discriminant = b * b - 4.0 * a * c
        if discriminant >= 0.0:
            root = math.sqrt(discriminant)
            for candidate in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if candidate > 0.0 and (best is None or candidate < best):
                    best = candidate
    if best is None:
        return np.asarray(target_pos, dtype=np.float64), 0.0
    return np.asarray(target_pos, dtype=np.float64) + vel * best, best


def threat_weight(distance_m: float, max_range_m: float,
                  min_range_m: float = 0.0) -> float:
    """How much of its own engagement envelope a raider has closed, in [0, 1].

    0 at (or beyond) its weapon's maximum range, 1 at the facility.  Scaling by
    the raider's **own** envelope keeps this data-driven and self-correcting: a
    suicide boat (max range 150 m) only becomes a threat when it is essentially
    touching, while an 8 km missile carrier is a threat from 8 km out.
    """
    if max_range_m <= min_range_m:
        return 1.0 if distance_m <= min_range_m else 0.0
    span = max_range_m - min_range_m
    return float(min(1.0, max(0.0, (max_range_m - distance_m) / span)))


# Target-domain legality, using the SAME rule the rule / hybrid arms apply via
# ``interception_graph``: the observation carries no domain field, so a contact is
# classified by its observable altitude.  Sharing the rule keeps the four arms on
# one definition of "this shot is legal".
AIR_ALTITUDE_THRESHOLD_M = 50.0
# Minimum confidence for the firing unit's OWN contact.  0.30 mirrors the rule
# executor's ``min_conf = min(0.30, contact_confidence)``: the local gate must not
# be stricter than the engine's (the engine uses the sensor's declared
# ``minimum_contact_confidence``), or the arm offers shots the engine rejects.
# Without any floor the RL arm could aim at a contact the engine does not consider
# current, which ABORTS the whole episode with ``session.contact_invalid``.
MIN_CONTACT_CONFIDENCE = 0.30


def _contact_domain_class(contact) -> str:
    position = contact.get("estimated_position_m") or (0.0, 0.0, 0.0)
    try:
        altitude = float(position[2])
    except (TypeError, ValueError, IndexError):
        altitude = 0.0
    return "air" if altitude > AIR_ALTITUDE_THRESHOLD_M else "surface"


def _domain_pairing_allowed(domains: tuple[str, ...], target_class: str) -> bool:
    if not domains:
        return True                      # empty declaration = unrestricted
    if target_class == "air":
        return "air" in domains
    return "surface" in domains or "land" in domains


class IERlEnv:
    """One IE scenario exposed as a fixed-shape, multi-unit control problem."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        public_id: str,
        *,
        seed: int = 7,
        decision_interval: int = 5,
        max_ticks: Optional[int] = None,
        reward: Optional[RewardConfig] = None,
        defender_faction: str = "coalition.defender",
        intruder_faction: str = "coalition.intruder",
        max_contacts: int = MAX_CONTACTS,
        episode_index: int = 0,
        lead_features: bool = True,
        slot_shuffle_seed: int | None = None,
        speed_source: str = "catalog",
        goal_features: bool = False,
    ) -> None:
        self.public_id = public_id
        self.seed = int(seed)
        self.decision_interval = max(1, int(decision_interval))
        self.max_ticks_override = max_ticks
        self.reward_cfg = reward or RewardConfig()
        self.defender_faction = defender_faction
        self.intruder_faction = intruder_faction
        self.max_contacts = int(max_contacts)
        # 8-wide pair block includes the lead-point bearing; 6-wide is the
        # pre-lead layout.  Kept selectable so a checkpoint trained before the
        # lead features existed can still be evaluated (the pair block is 86% of
        # the observation, so the two are not interchangeable): ``rl_agent``
        # infers the variant from the checkpoint's own ``trunk0.w`` shape.
        self.lead_features = bool(lead_features)
        # Diagnostic only: relabel the slots (a consistent relabelling of BOTH the
        # observation rows and the action rows, so the decoded command still goes to
        # the same unit).  A policy that has learned "any unit in any slot" scores
        # the same under a permutation; one that has memorised "slot k does X"
        # does not.  That distinction is exactly what decides whether the network
        # transfers to a scenario with a different roster.
        self.slot_shuffle_seed = slot_shuffle_seed
        # Which speed envelope the action's ``speed`` fraction is scaled by.
        #   "catalog"     -- the unit's real ``dynamics.max_speed_mps`` (80/10).
        #   "legacy_tags" -- the rule executor's ``speed_by_tag`` table (40/8), i.e.
        #                    the convention the recorded rule / hybrid / pure-LLM
        #                    baselines were measured under.
        # The two differ by 2x for every air unit, so an executor ablation MUST
        # pin this to the same value on both sides or it measures the table.
        if speed_source not in ("catalog", "legacy_tags"):
            raise ValueError(f"speed_source must be 'catalog' or 'legacy_tags', "
                             f"got {speed_source!r}")
        self.speed_source = str(speed_source)
        # Fifth arm only: append the LLM's plan as a per-unit feature block.  Off
        # for the pure-RL arm, whose whole point is that nothing above it plans.
        self.goal_features = bool(goal_features)
        # Callable () -> {entity_id: [GoalCommand, ...]} returning the CURRENTLY
        # active goals.  The RL executor sets this to read the broker; a getter
        # rather than a snapshot because goals are preempted between decisions.
        self.goal_provider: Optional[Any] = None
        # Optional per-engine-tick hook, invoked just before each ``session.step``
        # inside a decision window.  The fifth arm's training needs it: a decision
        # covers ``decision_interval`` engine ticks, but the planner above the
        # executor runs on its own cadence and must be driven every tick to produce
        # the same goal stream the evaluation path produces.  Driving it once per
        # decision instead would silently train on a different goal sequence.
        self.pre_tick_hook: Optional[Any] = None
        self.rollout_executor: Optional[Any] = None
        # Each episode in a training run must differ, otherwise the policy
        # overfits one RNG draw.  session_id feeds the engine's hit-roll seed
        # (combat/system_v2.py seeds from resolved_hash + session_id), so a new
        # session_id is exactly the supported way to resample an episode.
        self.episode_index = int(episode_index)

        self._session = None
        self._attack = None
        self._slots: list[Slot] = []
        self.slots_ready = False
        self._objective = np.zeros(2, dtype=np.float64)
        self._max_ticks = 0
        self._scenario_duration_ticks = 1800
        self._prev: dict[str, Any] = {}
        self._credited_kills: set[str] = set()
        self._last_contacts: list[str] = []
        self._last_contact_owner: list[str] = []
        self._last_contact_pos: list[Any] = []
        self._last_contact_class: list[str] = []
        self._own_contact: dict[Any, Any] = {}
        self._target_slots: list[str] = []
        self.steps_taken = 0
        self.terminal_outcome: Optional[str] = None

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    @property
    def num_units(self) -> int:
        """Tensor slot count -- **always** ``MAX_UNITS``, not the roster size.

        Keeping this constant is what makes one checkpoint usable on every IE
        scenario; see the MAX_UNITS comment.
        """
        return MAX_UNITS

    @property
    def real_units(self) -> int:
        """How many slots are actually backed by a controllable unit."""
        return len(self._slots)

    @property
    def num_fire_choices(self) -> int:
        """0 = do not fire, 1..max_contacts = fire at that contact slot."""
        return self.max_contacts + 1

    @property
    def pair_width(self) -> int:
        return 8 if self.lead_features else 6

    @property
    def observation_size(self) -> int:
        n, k = self.num_units, self.max_contacts
        # global(6) + units(10) + targets(7) + pairs(6 or 8) [+ goals(24) + assign(n*k)]
        size = 6 + n * 10 + k * 7 + n * k * self.pair_width
        if self.goal_features:
            # GOAL_FEATURE_WIDTH per unit, plus the per-(unit,target) assignment mask
            # (see ``_assignment_block`` for why the assignment is stated twice).
            size += n * GOAL_FEATURE_WIDTH + n * k
        return size

    def action_shapes(self) -> dict[str, tuple[int, ...]]:
        """Direct action layout, matching ``ie_rl_policy.numpy_sample``:
        an absolute heading as a tanh-bounded (sin, cos) pair, an absolute speed
        fraction, and a fire choice per slot."""
        n = self.num_units
        return {"heading_xy": (n, 2), "speed": (n,), "fire": (n,)}

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def reset(self) -> tuple[np.ndarray, dict[str, Any]]:
        from attack_driver import AttackProfileDriverV2, load_attack_profile_data
        from openmdbench.sessions.formal_v2 import create_formal_session_v2

        self.close()
        profile = load_attack_profile_data(self.public_id)
        session_id = f"rl.{self.public_id}.{self.seed}.{self.episode_index}"
        session = create_formal_session_v2(self.public_id, session_id=session_id,
                                          seed=self.seed)
        session.load().start()
        self._session = session
        self._attack = AttackProfileDriverV2(self.public_id, seed=self.seed)
        self.steps_taken = 0
        self.terminal_outcome = None

        objective_raw = profile.get("objective_m") or (0.0, 0.0)
        self._objective = np.asarray([float(objective_raw[0]),
                                      float(objective_raw[1])], dtype=np.float64)
        self.steps_taken = 0
        self.terminal_outcome = None
        self._reset_episode_state()
        duration = int(session.resolved.world.duration_ticks or 1800)
        self._scenario_duration_ticks = duration or 1800
        self._max_ticks = (self.max_ticks_override if self.max_ticks_override
                           else (duration or 1800))

        if not self.slots_ready:
            self._slots = self._discover_slots()
            self.slots_ready = True
            if not self._slots:
                raise RuntimeError(f"{self.public_id}: no mobile friendly units")
            if len(self._slots) > MAX_UNITS:
                raise RuntimeError(
                    f"{self.public_id} has {len(self._slots)} controllable units "
                    f"but MAX_UNITS={MAX_UNITS}; raise the constant (it changes "
                    f"the observation size, so policies must be retrained)")
        self._prev = self._snapshot()
        return self._observe(), {"units": [s.entity_id for s in self._slots]}

    def _reset_episode_state(self) -> None:
        """Clear every piece of state that must not survive into a new episode.

        The rollout worker deliberately keeps **one** env object and calls
        ``reset()`` for each episode (it only rebuilds when the scenario changes),
        and entity ids are identical across episodes.  Any per-episode ledger left
        behind therefore silently corrupts later episodes.  ``_credited_kills``
        was exactly that: after episode 1 every raider id was already credited, so
        ``new_kills`` came out empty and neutralising a raider -- the largest
        positive reward term -- paid nothing at all.  Measured on IE-01: episode 1
        returned +3.79 with 3 neutralisations, episodes 2 and 3 returned -0.06
        with the same 12 shots fired and 0 credited.
        """
        self._credited_kills: set[str] = set()
        self._last_fire_tick: dict[str, int] = {}
        self._prev = {}
        self._goal_credit_total = 0.0
        self._goal_prev_distances = {}
        # (unit, target) -> shots already paid the "you engaged what you were told to
        # engage" bonus this episode, capped by ``goal_shot_budget`` (see
        # ``_executed_assigned_shots``).
        self._goal_shot_credited: dict[tuple[str, str], int] = {}
        self._goal_shot_budget: int = max(1, int(getattr(
            self.reward_cfg, "goal_shot_budget", 2) or 2))
        # Contact snapshots are keyed to the previous session; drop them so a
        # decision taken before the first ``_observe`` cannot act on stale ids.
        self._last_contacts = []
        self._last_contact_owner = []
        self._last_contact_pos = []
        self._last_contact_class = []
        self._own_contact = {}
        self._target_slots = []
        self._prepared_attack_tick = None

    def _discover_slots(self) -> list[Slot]:
        """Fixed roster: mobile friendly units, sorted for a stable slot order."""
        # Same constant the other three arms use (v2_agent.FIXED_DYNAMICS_MODEL):
        # a fixed facility cannot accept a navigation command and the engine
        # rejects the whole batch, so it must never enter a controllable slot.
        from v2_agent import FIXED_DYNAMICS_MODEL
        slots: list[Slot] = []
        for entity in self._session.world_view.entities_stable():
            if str(entity.faction_id) != self.defender_faction:
                continue
            definition = getattr(entity, "definition", None)
            bindings = getattr(definition, "resource_bindings", None) or {}
            dynamics = bindings.get("dynamics", ())
            if not dynamics or all(
                    getattr(b, "model_ref", "") == FIXED_DYNAMICS_MODEL
                    for b in dynamics):
                continue  # fixed facilities are not controllable
            klass, speed_max = _platform_profile(entity)
            if self.speed_source == "legacy_tags":
                speed_max = legacy_executor_speed(entity)
            weapon_ref, lo, hi, domains = _weapon_profile_for(entity)
            _wref, _lo, _hi, _dom, cooldown, flight_ticks = _weapon_profile_full(entity)
            slots.append(Slot(
                entity_id=str(entity.id),
                klass=klass,
                weapon_ref=weapon_ref or "",
                ammo_full=max(1, _ammo_total(entity)),
                min_range_m=lo,
                max_range_m=hi,
                target_domains=domains,
                speed_max_mps=float(speed_max),
                cooldown_ticks=cooldown,
                flight_ticks=flight_ticks,
            ))
        slots = sorted(slots, key=lambda s: s.entity_id)
        if self.slot_shuffle_seed is not None:
            # Same units, same features, different slot numbering.  Both the
            # observation rows and the action rows follow this order, so the
            # commands still reach the right units; only the policy's assumed
            # slot semantics change.
            rng = np.random.default_rng(int(self.slot_shuffle_seed))
            order = rng.permutation(len(slots))
            slots = [slots[int(i)] for i in order]
        return slots

    def close(self) -> None:
        if self._session is not None:
            try:
                self._session.stop()
            finally:
                self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # observation
    # ------------------------------------------------------------------
    def engagement_onsets(self) -> dict[str, int]:
        """Per-scenario onset ticks of the *whole* threat, not just the first unit.

        Two different numbers matter:

        * ``earliest`` -- when any raider can first be engaged.  Surface raiders
          often start inside the defenders' envelope (IE-03..08 return 0),
        * ``latest``   -- when the **last** raider becomes engageable.  This is
          the one a truncation must exceed: cutting earlier silently drops the
          air engagement entirely.  Measured with a uniform 300-tick cut, the
          air element of IE-04 (onset ~305) and IE-08 (~540) never appeared, so
          two of eight scenarios contributed nothing while still costing full
          simulation time.
        """
        session = self._session
        entity_view = session.world_view.entities_stable()
        speed = 43.0
        try:
            from attack_driver import load_attack_profile_data
            speed = float((load_attack_profile_data(self.public_id).get("attack")
                           or {}).get("speed_mps", 43.0))
        except Exception:  # noqa: BLE001
            pass
        weapon_units = []
        for entity in entity_view:
            if str(entity.faction_id) != self.defender_faction:
                continue
            tags = set(str(t) for t in (entity.tags or ()))
            if tags & {"uav", "usv"}:
                weapon_units.append(np.asarray(entity.state.position_m[:2],
                                               dtype=np.float64))
        onsets: list[int] = []
        spawn_by_id = self._spawn_ticks()
        for entity in entity_view:
            if str(entity.faction_id) != self.intruder_faction:
                continue
            if "decoy" in set(str(t) for t in (entity.tags or ())):
                continue
            pos = np.asarray(entity.state.position_m[:2], dtype=np.float64)
            dist = (min(float(np.linalg.norm(pos - unit)) for unit in weapon_units)
                    if weapon_units
                    else float(np.linalg.norm(pos - self._objective)))
            travel = int(max(0.0, dist - 8000.0) / max(speed, 1e-9))
            # Reinforcements spawn later; their engagement cannot precede the
            # spawn, so the spawn tick is a floor on the onset.  Without this a
            # wave-2 unit sitting far outside the map at t=0 would look
            # engageable far later than it actually is, and a scenario whose
            # raiders have not spawned yet at reset (IE-08 declares its whole
            # red force via spawn events) would report **zero** raiders and
            # silently pass the truncation guard.
            onsets.append(int(spawn_by_id.get(str(entity.id), 0)) + travel)
        if not onsets:
            # nothing has spawned yet -- fall back to the declared timeline
            for entity_id, spawn_tick in spawn_by_id.items():
                onsets.append(int(spawn_tick))
        if not onsets:
            return {"earliest": 0, "latest": 0, "raiders": 0}
        return {"earliest": min(onsets), "latest": max(onsets),
                "raiders": len(onsets)}

    def _target_of(self, contact: Mapping[str, Any], known) -> Optional[str]:
        """Resolve a contact to the **target entity id** it refers to."""
        try:
            from run_episode import _contact_suffix
        except Exception:  # pragma: no cover
            _contact_suffix = None
        contact_id = str(contact.get("contact_id") or "")
        target = (_contact_suffix(contact_id, known) if _contact_suffix
                  else contact_id.rsplit(".", 1)[-1])
        target = str(target or "")
        if not target or target not in set(map(str, known)):
            return None
        return target

    def _spawn_ticks(self) -> dict[str, int]:
        """entity_id -> spawn tick, from the scenario's spawn events."""
        try:
            from attack_driver import load_attack_profile_data  # noqa: F401
            from openmdbench.scenarios.formal_v2 import formal_scenario_registry_v2
            entry = formal_scenario_registry_v2()[self.public_id]
            import yaml
            payload = yaml.safe_load(
                (entry.package_root / "scenario.yaml").read_text(encoding="utf-8"))
            scenario = payload.get("scenario") or payload
        except Exception:  # noqa: BLE001
            return {}
        out: dict[str, int] = {}
        for event in scenario.get("events") or ():
            if not isinstance(event, dict) or event.get("event_type") != "spawn":
                continue
            blueprint = (event.get("payload") or {}).get("entity")
            if not isinstance(blueprint, dict) or not blueprint.get("id"):
                continue
            trigger = event.get("trigger") or {}
            out[str(blueprint["id"])] = int(trigger.get("tick", 0) or 0)
        return out

    def first_contact_tick(self) -> int:
        """Backwards-compatible alias for the earliest onset."""
        return self.engagement_onsets()["earliest"]

    def _pair_row(self, dist: float, bearing: float, owned: float,
                  confidence: float, unit_pos: np.ndarray, est: np.ndarray,
                  tvel: np.ndarray, unit_speed: float, slot: "Slot",
                  target_class: str) -> tuple[float, ...]:
        """One (unit, target) feature row -- 6 wide, or 8 with the lead bearing."""
        legal = 1.0 if (owned > 0.0
                        and confidence >= MIN_CONTACT_CONFIDENCE
                        and slot.min_range_m <= dist <= slot.max_range_m
                        and _domain_pairing_allowed(slot.target_domains,
                                                    target_class)) else 0.0
        row = (dist / POS_SCALE_M,
               math.sin(bearing), math.cos(bearing),
               # EXACTLY the condition the fire mask enforces -- own envelope, own
               # CONFIRMED contact, domain pairing -- so the feature the policy sees
               # and the legality the mask applies cannot disagree.  A unit whose
               # weapon cannot touch this target class reads 0 here and is masked
               # out there.
               legal,
               confidence,
               owned)
        if not self.lead_features:
            return row
        lead, _time_to_go = _intercept_point(unit_pos, est, tvel, unit_speed)
        aim = lead - unit_pos
        lead_bearing = math.atan2(aim[0], aim[1])
        return row + (math.sin(lead_bearing), math.cos(lead_bearing))

    def _observe(self) -> np.ndarray:
        session = self._session
        obs = session.world_view.observation(
            observer_faction_id=self.defender_faction)
        own = {str(item["entity_id"]): item for item in obs.own_entities}
        contacts = list(obs.contacts_by_faction.get(self.defender_faction, ()))
        known = tuple(item.id for item in session.world_view.entities_stable())

        # --- target-slot block (fixed K slots, one per distinct target) ----
        # KEYED BY TARGET, NOT BY (observer, target) CONTACT.  The engine emits a
        # contact per observer, so the raw list is O(observers x targets); keying
        # slots by target keeps them meaningful, and the per-unit mask then
        # decides which targets a given unit may shoot at.  Deliberately
        # **unranked and untruncated apart from the fixed cap**: ranking the
        # candidates by distance to the objective was the wrapper making a
        # targeting decision on the network's behalf.
        by_target: dict[str, dict[str, Any]] = {}
        for contact in contacts:
            target = self._target_of(contact, known)
            if target is None:
                continue
            existing = by_target.get(target)
            # keep the most confident observation as the representative
            if existing is None or float(contact.get("confidence", 0.0)) > float(
                    existing.get("confidence", 0.0)):
                by_target[target] = contact
        target_ids = sorted(by_target)[: self.max_contacts]
        contact_feat = np.zeros((self.max_contacts, 7), dtype=np.float32)
        contact_ids: list[str] = []
        contact_owner: list[str] = []
        contact_pos: list[tuple[float, float, float]] = []
        contact_class: list[str] = []
        for index, target in enumerate(target_ids):
            contact = by_target[target]
            est = np.asarray(contact["estimated_position_m"], dtype=np.float64)
            rel = est[:2] / POS_SCALE_M
            dist = float(np.linalg.norm(est[:2] - self._objective))
            contact_ids.append(target)
            contact_owner.append(str(contact.get("observer_entity_id", "")))
            contact_pos.append(tuple(float(v) for v in est))
            contact_class.append(_contact_domain_class(contact))
            contact_feat[index] = (
                rel[0], rel[1], dist / POS_SCALE_M,
                float(contact.get("confidence", 0.0)),
                min(float(contact.get("age_ticks", 0)) / 12.0, 2.0),
                1.0 if len(est) > 2 and float(est[2]) > 0.0 else 0.0,
                1.0 if dist <= 8000.0 else 0.0,
            )
        # unit -> target -> that unit's OWN contact:
        # (contact_id, est_x, est_y, confidence).
        # The engine accepts a shot only against a contact the firing unit holds
        # itself, and its envelope check uses *that* contact's estimate -- so the
        # mask must range-check the unit's own estimate too, not the faction-level
        # representative one.  With disagreeing observers the two differ, and a
        # mask that measures the wrong range either hides legal shots or offers
        # shots the engine rejects.  Confidence is carried for the same reason:
        # the engine also requires the contact to be CONFIRMED, and the rule
        # executor already guards this with
        # ``min_conf = min(0.30, contact_confidence)`` -- whose comment names the
        # failure exactly: "本地门槛不应高于引擎门槛 ... 避免'本地合格、引擎拒绝'的错配".
        # Without the same floor the RL arm offered unconfirmed shots and the engine
        # aborted the episode with
        # ``session.contact_invalid: opaque contact is not a current observation
        # owned by the firing entity`` (measured at seed 11, t48).
        own_contact: dict[tuple[str, str], tuple[str, float, float, float]] = {}
        # Faction-level ``contact_id -> target entity id`` table.
        #
        # The per-unit table below is the wrong key space for resolving a planner's
        # ``target_id``: the planner may name ANOTHER observer's contact for the same
        # raider, and a unit whose own sensor has not published that track has no
        # entry -- measured, the assignment mask then lit **1** flag for IE-01 and
        # IE-05 even with 4 and 9 units assigned, i.e. the new attention block was
        # almost always blank.  Resolution therefore goes through every contact the
        # faction can see, while the reward's distances stay on the unit's own track
        # (that is the honest estimate for "how far am I from my target").
        contact_to_target: dict[str, str] = {}
        for contact in contacts:
            target = self._target_of(contact, known)
            if target is None or target not in target_ids:
                continue
            owner = str(contact.get("observer_entity_id", ""))
            est = np.asarray(contact["estimated_position_m"], dtype=np.float64)
            own_contact[(owner, target)] = (str(contact["contact_id"]),
                                            float(est[0]), float(est[1]),
                                            float(contact.get("confidence", 0.0)))
            contact_to_target[str(contact["contact_id"])] = str(target)
        self._own_contact = own_contact
        self._contact_to_target_all = contact_to_target
        # Decode table for the fire head: choice j>0 means target_ids[j-1].
        self._target_slots = list(target_ids)

        # --- target velocity, estimated from successive observations --------
        # The engine publishes a contact's *position* only, so velocity has to be
        # differenced across decisions -- which is what any tracker does, and what
        # the rule arm's ``interception_graph`` already does (it derives
        # ``closing_speed`` from ``self._prev_distance``).  Without it the policy
        # cannot compute where a raider *will* be, which is the whole of
        # interception geometry.
        tick_now = int(obs.tick)
        previous = getattr(self, "_target_track", {})
        track: dict[str, tuple[float, float, float, float, int]] = {}
        for index, target in enumerate(target_ids):
            ex, ey = contact_pos[index][0], contact_pos[index][1]
            prior = previous.get(target)
            if prior is not None and tick_now > prior[4]:
                dt = float(tick_now - prior[4])
                vx, vy = (ex - prior[0]) / dt, (ey - prior[1]) / dt
            else:
                vx = vy = 0.0
            track[target] = (ex, ey, vx, vy, tick_now)
        self._target_track = track
        if len(by_target) > self.max_contacts:
            # Silent truncation would look like "the policy ignores the nearest
            # threat" when it is really the wrapper hiding targets from it.
            print(f"[ie_rl_env] {self.public_id}: {len(by_target)} distinct targets "
                  f"visible but MAX_CONTACTS={self.max_contacts}; "
                  f"{len(by_target) - self.max_contacts} dropped", flush=True)

        # --- own-unit block (padded to the fixed slot capacity) ---------
        unit_feat = np.zeros((MAX_UNITS, 10), dtype=np.float32)
        unit_pos = np.zeros((MAX_UNITS, 2), dtype=np.float64)
        for slot_index, slot in enumerate(self._slots):
            item = own.get(slot.entity_id)
            if item is None or item.get("lifecycle_state") not in ("active", "degraded"):
                continue                       # dead / spawned-out -> masked to zero
            pos = np.asarray(item["position_m"], dtype=np.float64)
            unit_pos[slot_index] = pos[:2]
            vel = np.asarray(item.get("velocity_mps", (0.0, 0.0, 0.0)),
                             dtype=np.float64)
            rel = (pos[:2] - self._objective) / POS_SCALE_M
            speed_max = slot.speed_max_mps
            entity = next((e for e in session.world_view.entities_stable()
                           if str(e.id) == slot.entity_id), None)
            ammo = _ammo_total(entity) if entity is not None else 0
            in_range = sum(
                1 for c in contacts
                if float(c.get("confidence", 0.0)) >= MIN_CONTACT_CONFIDENCE
                and slot.min_range_m <= float(np.linalg.norm(
                    np.asarray(c["estimated_position_m"][:2], dtype=np.float64)
                    - pos[:2])) <= slot.max_range_m
                and _domain_pairing_allowed(slot.target_domains,
                                            _contact_domain_class(c)))
            unit_feat[slot_index] = (
                1.0,                                        # alive mask
                1.0 if slot.klass == "air" else 0.0,
                rel[0], rel[1],
                float(vel[0]) / speed_max, float(vel[1]) / speed_max,
                math.radians(float(item.get("heading_deg", 0.0))) / math.pi,
                float(item.get("health", 1.0)),
                ammo / float(slot.ammo_full),
                min(in_range / float(self.max_contacts), 1.0),
            )

        # --- (unit, contact) pairing block ------------------------------
        # Feature 5 is **ownership**: the engine only accepts a fire action
        # against a contact the firing unit observes itself
        # (`session.contact_invalid` otherwise).  Without this flag the policy
        # cannot tell a legal shot from an illegal one and would waste most of
        # its fire attempts.
        # 8 features per (unit, target) pair: the last two are the LEAD-POINT
        # bearing, i.e. where the unit must fly to meet the target rather than
        # where the target is now.  This is input encoding, not a decision layer:
        # the network still emits its own heading/speed/fire directly and nothing
        # picks a target or a goal for it.  It exists because the rule arm solves
        # the intercept triangle in ``interception_graph`` while the network had to
        # learn ballistics from a position-only contact, and the measured symptom
        # was a ``depth`` layer of 0.15-0.44 against rule's 0.52 -- intercepting on
        # the doorstep instead of out front.
        pair = np.zeros((MAX_UNITS, self.max_contacts, self.pair_width),
                        dtype=np.float32)
        for i, slot in enumerate(self._slots):
            if unit_feat[i, 0] <= 0.0:
                continue
            unit_speed = float(
                np.linalg.norm(np.asarray(
                    own.get(slot.entity_id, {}).get("velocity_mps", (0.0, 0.0, 0.0)),
                    dtype=np.float64)))
            unit_speed = max(unit_speed, 0.5 * slot.speed_max_mps)
            for j, target in enumerate(target_ids):
                est = np.asarray(contact_pos[j][:2], dtype=np.float64)
                delta = est - unit_pos[i]
                dist = float(np.linalg.norm(delta))
                bearing = math.atan2(delta[0], delta[1])
                owned = 1.0 if (slot.entity_id, target) in own_contact else 0.0
                track = self._target_track.get(target)
                if track is not None:
                    tvel = np.asarray(track[2:4], dtype=np.float64)
                else:
                    tvel = np.zeros(2, dtype=np.float64)
                lead, time_to_go = _intercept_point(unit_pos[i], est, tvel,
                                                    unit_speed)
                aim = lead - unit_pos[i]
                lead_bearing = math.atan2(aim[0], aim[1])
                pair[i, j] = self._pair_row(
                    dist, bearing, owned, contact_feat[j][3], unit_pos[i], est,
                    tvel, unit_speed, slot, contact_class[j])

        # --- global block ----------------------------------------------
        facilities = [e for e in session.world_view.entities_stable()
                      if str(e.faction_id) == self.defender_faction
                      and "facility" in tuple(e.tags or ())]
        survival = (sum(float(e.state.health) for e in facilities) / len(facilities)
                    if facilities else 1.0)
        tick = int(obs.tick)
        global_feat = np.asarray([
            tick / max(1, self._scenario_duration_ticks),
            1.0 - tick / max(1, self._scenario_duration_ticks),
            float(survival),
            sum(1.0 for f in unit_feat if f[0] > 0) / max(1, self.real_units),
            len(contacts) / float(self.max_contacts),
            float(self.terminal_outcome is not None),
        ], dtype=np.float32)

        self._last_contacts = contact_ids
        self._last_contact_owner = contact_owner
        self._last_contact_pos = contact_pos
        self._last_contact_class = contact_class
        self._last_unit_pos = unit_pos

        # --- goal block (fifth arm only) ---------------------------------
        # The LLM's plan reaches the network here and nowhere else.  Target
        # positions are resolved from the faction-filtered contacts computed above,
        # NOT from entity truth: a goal may name a target, but the executor is only
        # allowed to know where that target *is* to the extent the observation
        # already does.
        goal_block = np.zeros((MAX_UNITS, GOAL_FEATURE_WIDTH), dtype=np.float32)
        if self.goal_features and self.goal_provider is not None:
            from ie_goal_features import encode_goals
            goals_by_unit = self.goal_provider() or {}
            # Index the contact positions under BOTH forms of the id.
            #
            # This was a silent information loss: a planner's ``target_id`` is a
            # *contact* id (``sensor.contact.defender.uav-03.intruder.uav-01``) while
            # the target slots are keyed by *entity* id (``intruder.uav-01``), so
            # ``target_id`` never resolved, intercept goals carry no ``position``
            # either, and the encoder left ``has_target`` at 0 -- the network could
            # not see where it had been told to intercept.  Measured on a real
            # episode: 0.13 of goal-carrying slots had a target instead of ~all
            # intercept goals.  Keying both forms makes the lookup insensitive to
            # which convention the planner used.
            contact_by_target = self._goal_target_positions(
                contacts, known, contact_ids, contact_pos)
            encoded = encode_goals(
                goals_by_unit,
                [s.entity_id for s in self._slots],
                {s.entity_id: unit_pos[i] for i, s in enumerate(self._slots)},
                objective=self._objective,
                speed_limits={s.entity_id: s.speed_max_mps for s in self._slots},
                target_positions=contact_by_target,
                tick=tick,
            )
            goal_block[:encoded.shape[0]] = encoded

        blocks = [
            global_feat,
            unit_feat.reshape(-1),
            contact_feat.reshape(-1),
            pair.reshape(-1),
        ]
        if self.goal_features:
            blocks.append(goal_block.reshape(-1))
            blocks.append(self._assignment_block().reshape(-1))
        return np.concatenate(blocks).astype(np.float32)

    def _assignment_block(self) -> np.ndarray:
        """(MAX_UNITS, MAX_CONTACTS) mask: "is this slot MY assigned target?".

        WHY A SEPARATE BLOCK.  The 24-dim goal row states the assigned target's
        bearing in 2 numbers, and measured against the pair block it loses badly:
        zeroing the whole goal block moved the commanded heading by 5-8 deg while
        zeroing the pair block moved it 18-30 deg, and raising the shaping weight
        8x (0.25 -> 2.0, r_goal 0.06 -> 0.47 against a return of ~6) did **not**
        change that.  The pair block carries the same bearing information 320 times
        over (every unit x every target row), so the policy reads it easily; the
        plan's version is two numbers per unit buried in 384 more.

        This block restates the assignment in the layout the policy already knows how
        to attend over: one flag per (unit, target) pair.  It adds no information the
        24-dim row did not already carry -- it is the same assignment, expressed where
        the modulation is cheap.  Built from the unit's OWN contacts only, so the
        information set is unchanged.
        """
        block = np.zeros((MAX_UNITS, self.max_contacts), dtype=np.float32)
        assigned = self._assigned_targets()
        if not assigned:
            return block
        targets = list(getattr(self, "_last_contacts", []))
        for index, slot in enumerate(self._slots[:MAX_UNITS]):
            mine = assigned.get(slot.entity_id)
            if mine is None:
                continue
            for j, target in enumerate(targets[:self.max_contacts]):
                if str(target) == mine:
                    block[index, j] = 1.0
        return block

    def _goal_target_positions(self, contacts, known, contact_ids, contact_pos):
        positions = {str(target): position
                     for target, position in zip(contact_ids, contact_pos)}
        visible_targets = set(contact_ids)
        for contact in contacts:
            target = self._target_of(contact, known)
            if target in visible_targets:
                positions[str(contact["contact_id"])] = contact["estimated_position_m"]
        return positions

    # ------------------------------------------------------------------
    # action
    # ------------------------------------------------------------------
    def slot_mask(self) -> np.ndarray:
        """(MAX_UNITS,) float32: 1.0 for slots backed by a live controllable unit.

        Padded / dead slots still produce turn and throttle outputs, and those
        log-probabilities used to be summed into the PPO loss.  Their actions
        have no effect on the world, so their contribution is pure noise in the
        policy gradient -- multiplied in, they vanish.
        """
        mask = np.zeros(MAX_UNITS, dtype=np.float32)
        entities = {str(e.id): e for e in self._session.world_view.entities_stable()}
        for i, slot in enumerate(self._slots):
            entity = entities.get(slot.entity_id)
            if entity is not None and str(entity.state.lifecycle) in ("active", "degraded"):
                mask[i] = 1.0
        return mask

    def fire_mask(self) -> np.ndarray:
        """(MAX_UNITS, num_fire_choices) mask of legal fire choices.

        Choice 0 is "hold fire"; choice j+1 targets slot ``j``, i.e. the j-th
        distinct target the faction can see.  A unit may fire only at a target it
        observes **itself** (the engine rejects anything else with
        ``session.contact_invalid``), only inside **its own** weapon envelope,
        and only at a compatible target domain -- the engine returns
        ``combat.target_domain_denied`` for an air-only interceptor aimed at a
        boat, which the rule/hybrid arms already guard against through
        ``interception_graph`` and the RL mask previously did not.

        This is action masking, not a control layer: the mask removes choices the
        engine would reject, it never picks one for the network.
        """
        mask = np.zeros((MAX_UNITS, self.num_fire_choices), dtype=bool)
        mask[:, 0] = True
        tick = int(self._session.world_view.tick)
        targets = getattr(self, "_last_contacts", [])
        own_contact = getattr(self, "_own_contact", {})
        target_class = getattr(self, "_last_contact_class", [])
        engine_cooldowns = getattr(getattr(self._session, "_world", None),
                                   "_combat_cooldowns", None)
        entities = {str(e.id): e for e in self._session.world_view.entities_stable()}
        for i, slot in enumerate(self._slots):
            entity = entities.get(slot.entity_id)
            if entity is None or str(entity.state.lifecycle) not in ("active", "degraded"):
                continue
            if _ammo_total(entity) <= 0 or not slot.weapon_ref:
                continue
            if slot.max_range_m <= slot.min_range_m:
                continue          # no usable envelope resolved -> cannot fire
            # Weapon cooldown, from the catalog.  Non-binding with the shipped
            # weapons (cooldown <= decision interval) but masked anyway so a
            # scenario with a longer cooldown cannot silently offer a shot the
            # engine will reject.
            last = getattr(self, "_last_fire_tick", {}).get(slot.entity_id)
            cooling = (engine_cooldowns.get(f"{slot.entity_id}|{slot.weapon_ref}", 0) > 0
                       if engine_cooldowns is not None else
                       last is not None and slot.cooldown_ticks > 0
                       and tick - last < slot.cooldown_ticks)
            if cooling:
                continue
            pos = np.asarray(entity.state.position_m[:2], dtype=np.float64)
            for j, target in enumerate(targets):
                entry = own_contact.get((slot.entity_id, str(target)))
                if entry is None:
                    continue
                if entry[3] < MIN_CONTACT_CONFIDENCE:
                    # Unconfirmed contact: the engine will reject the shot and may
                    # abort the session (see MIN_CONTACT_CONFIDENCE).
                    continue
                # range against THIS unit's own estimate of the target
                dist = float(np.hypot(entry[1] - pos[0], entry[2] - pos[1]))
                if not (slot.min_range_m <= dist <= slot.max_range_m):
                    continue
                if j < len(target_class) and not _domain_pairing_allowed(
                        slot.target_domains, target_class[j]):
                    continue
                mask[i, j + 1] = True
        return mask

    def attach(self, session, profile: Optional[dict] = None) -> None:
        """Bind to an **existing** session instead of creating one.

        Evaluation must reuse the harness' own scoring path
        (``run_episode.run_episode``) so the RL arm is scored by exactly the same
        code as the other three arms.  That means the RL policy has to act on a
        session the harness owns and steps itself, so this method wires the
        observation/action machinery to that session without ever calling
        ``session.step()``.
        """
        self._session = session
        if profile is None:
            from attack_driver import load_attack_profile_data
            profile = load_attack_profile_data(self.public_id)
        objective_raw = profile.get("objective_m") or (0.0, 0.0)
        self._objective = np.asarray([float(objective_raw[0]),
                                      float(objective_raw[1])], dtype=np.float64)
        self.steps_taken = 0
        self.terminal_outcome = None
        self._reset_episode_state()
        self._slots = self._discover_slots()
        self.slots_ready = True
        if not self._slots:
            raise RuntimeError(f"{self.public_id}: no mobile friendly units")
        self._scenario_duration_ticks = int(session.resolved.world.duration_ticks or 1800)
        self._max_ticks = self.max_ticks_override or self._scenario_duration_ticks
        self._prev = self._snapshot()

    def observe(self) -> np.ndarray:
        """Public observation entry point (used by the evaluation agent)."""
        return self._observe()

    def decode_unit_action(self, slot_index: int,
                           action: dict[str, np.ndarray]
                           ) -> tuple[float, float, Optional[str]]:
        """(heading_deg, speed_mps, contact_id|None) for one slot.

        Shared by the batch path (``submit_action``) and the fifth arm's executor so
        both decode *identically* -- a second copy of this arithmetic is exactly how
        the goal encoder, the speed table and the fire envelope each ended up with
        two disagreeing versions.
        """
        slot = self._slots[slot_index]
        heading_in = np.asarray(action["heading_xy"], dtype=np.float64).reshape(-1, 2)
        speed_in = np.asarray(action["speed"], dtype=np.float64).reshape(-1)
        heading = math.degrees(math.atan2(float(heading_in[slot_index, 0]),
                                          float(heading_in[slot_index, 1]))) % 360.0
        speed = float(np.clip(speed_in[slot_index], 0.0, 1.0)) * slot.speed_max_mps
        fire = np.asarray(action["fire"]).reshape(-1).astype(int)
        targets = getattr(self, "_last_contacts", [])
        own_contact = getattr(self, "_own_contact", {})
        choice = int(fire[slot_index]) if slot_index < fire.size else 0
        contact_id = None
        if 1 <= choice <= len(targets):
            entry = own_contact.get((slot.entity_id, str(targets[choice - 1])))
            contact_id = entry[0] if entry is not None else None
        return heading, speed, contact_id

    def submit_action(self, action: dict[str, np.ndarray]) -> tuple[list[dict], int]:
        """Submit one decision's commands.  Returns (fire records, submitted)."""
        from openmdbench.schemas.interface_v2 import (
            ActionBatchV2,
            DiscreteActionV2,
            PersistentCommandV2,
        )

        session = self._session
        tick = int(session.world_view.tick)
        tokens = {grant.entity_id: token
                  for token, grant in session.world_view.authority_tokens.items()}
        entities = {str(e.id): e for e in session.world_view.entities_stable()}
        submitted = 0
        fire_records: list[dict] = []
        for i, slot in enumerate(self._slots):
            token = tokens.get(slot.entity_id)
            if token is None:
                continue
            entity = entities.get(slot.entity_id)
            if entity is None or str(entity.state.lifecycle) not in ("active", "degraded"):
                continue
            pos = np.asarray(entity.state.position_m, dtype=np.float64)
            heading, speed, contact_id = self.decode_unit_action(i, action)
            commands = [PersistentCommandV2(
                schema_version="2.0",
                command_id=f"rl.nav.{slot.entity_id}.{tick}",
                command_type="navigation",
                entity_id=slot.entity_id,
                faction_id=self.defender_faction,
                based_on_tick=tick,
                valid_until_tick=tick + self.decision_interval,
                payload={"speed_mps": speed, "heading_deg": heading,
                         "altitude_m": float(pos[2])},
            )]
            discrete = []
            if contact_id is not None:
                action_id = f"rl.fire.{slot.entity_id}.{tick}"
                discrete.append(DiscreteActionV2(
                    schema_version="2.0",
                    action_id=action_id,
                    action_type="fire_weapon",
                    entity_id=slot.entity_id,
                    faction_id=self.defender_faction,
                    based_on_tick=tick,
                    valid_until_tick=tick,
                    payload={"weapon_ref": slot.weapon_ref,
                             "contact_id": contact_id},
                ))
                fire_records.append({
                    "tick": tick,
                    "entity_id": slot.entity_id,
                    "contact_id": contact_id,
                    "weapon_ref": slot.weapon_ref,
                    "action_id": action_id,
                })
            session.submit_actions(
                batch=ActionBatchV2(
                    schema_version="2.0",
                    session_id=session.session_id,
                    batch_id=f"rl.batch.{slot.entity_id}.{tick}",
                    idempotency_key=f"rl.idem.{slot.entity_id}.{tick}",
                    faction_id=self.defender_faction,
                    based_on_tick=tick,
                    valid_until_tick=tick + self.decision_interval,
                    persistent_commands=tuple(commands),
                    discrete_actions=tuple(discrete),
                ),
                authority_token=token,
                operation_id=f"rl.submit.{slot.entity_id}.{tick}",
                expected_tick=tick,
            )
            submitted += 1
        return fire_records, submitted

    def step(self, action: dict[str, np.ndarray]) -> tuple[
            np.ndarray, float, bool, bool, dict[str, Any]]:
        session = self._session
        if self.rollout_executor is None:
            fire_records, _submitted = self.submit_action(action)
        else:
            self.rollout_executor.prepare_action(self, action, int(session.world_view.tick))
            fire_records = []
        # One env decision == ``decision_interval`` engine ticks.  The submitted
        # persistent navigation command is valid for exactly that window, so the
        # units keep flying between decisions; this is the same cadence the
        # pure-LLM arm uses (``--plan-interval``) and it shortens the trajectory
        # by that factor, which matters a lot for PPO sample efficiency here.
        reward_total = 0.0
        # Aggregate the per-sub-tick counters: overwriting `info` each sub-tick
        # hides kills and shots that happened mid-window, which made the very
        # first self-check report "0 neutralised" next to a positive reward.
        info: dict[str, Any] = {"own_lost": 0, "raiders_lost": 0,
                                "facility_damage": 0.0, "fired": 0,
                                "depth_credit": 0.0, "terminal_reward": 0.0,
                                "goal_progress": 0.0, "goal_shot": 0.0,
                                "goal_assigned_hits": 0}
        terminal_result = None
        for _ in range(self.decision_interval):
            tick = int(session.world_view.tick)
            if self._prepared_attack_tick == tick:
                self._prepared_attack_tick = None
            else:
                self._attack(session)
            if self.pre_tick_hook is not None:
                # Drive the layer above (the LLM planner, in the fifth arm) on every
                # engine tick, exactly as the evaluation path does, so the goal
                # stream seen here matches the one seen at evaluation time.
                self.pre_tick_hook(int(session.world_view.tick))
            if self.rollout_executor is not None:
                execution = self.rollout_executor.act(session, tick)
                fire_records = execution.get("fires", [])
            receipt = session.step(operation_id=f"rl.step.{session.world_view.tick:08d}",
                                   expected_tick=int(session.world_view.tick))
            terminal_result = self._terminal_from(receipt)
            outcome = self._outcome_of(terminal_result)
            executed_now = self._executed_shots(
                receipt, tick=tick,
                fire_records=fire_records if self.rollout_executor is not None else None)
            step_reward, step_info = self._reward(
                receipt, fired=executed_now, terminated_outcome=outcome,
                assigned_hits=self._executed_assigned_shots(fire_records))
            reward_total += step_reward
            for key in ("own_lost", "raiders_lost", "fired"):
                info[key] += int(step_info.get(key, 0))
            for key in ("facility_damage", "depth_credit", "terminal_reward",
                        "goal_progress", "goal_shot"):
                info[key] += float(step_info.get(key, 0.0))
            info["goal_assigned_hits"] = (int(info.get("goal_assigned_hits", 0))
                                          + int(step_info.get("goal_assigned_hits", 0)))
            if terminal_result is not None:
                break
        self.steps_taken += 1
        for key in ("facility_damage", "depth_credit", "terminal_reward"):
            info[key] = round(info[key], 4)

        terminated = terminal_result is not None
        if terminated:
            self.terminal_outcome = self._outcome_of(terminal_result) \
                or str(terminal_result)
        truncated = (not terminated) and (
            int(session.world_view.tick) >= self._max_ticks)
        if truncated:
            snapshot = self._prev or {}
            count = max(1, int(snapshot.get("facility_count") or 1))
            survival = float(snapshot.get("facility_health", count)) / count
            imminent, live_raiders, raiders_total = self._imminent_threat()
            bonus = truncation_standing_bonus(
                survival, imminent,
                truncation_bonus=self.reward_cfg.truncation_bonus,
                imminent_penalty=self.reward_cfg.imminent_threat_penalty)
            info["truncation_standing_diagnostic"] = round(bonus, 4)
            info["truncation_bonus"] = 0.0
            info["facility_survival"] = round(survival, 4)
            info["imminent_threat"] = round(imminent, 4)
            info["live_raiders_at_cut"] = int(live_raiders)
            info["raiders_total"] = int(raiders_total)
            info["truncated"] = True
        if self.pre_tick_hook is not None and not terminated:
            tick = int(session.world_view.tick)
            self._attack(session)
            self._prepared_attack_tick = tick
            self.pre_tick_hook(tick)
        obs = self._observe()
        info["tick"] = int(session.world_view.tick)
        info["outcome"] = self.terminal_outcome
        info["terminated"] = bool(terminated)
        info["truncated"] = bool(truncated)
        # ``done`` must distinguish "the episode ended" from "we cut it short":
        # GAE has to keep bootstrapping through a truncation, otherwise the
        # value function is trained towards the return-so-far of an arbitrary
        # horizon end.  The trajectory therefore carries both flags.
        info["done"] = bool(terminated or truncated)
        return obs, float(reward_total), bool(terminated), bool(truncated), info

    # ------------------------------------------------------------------
    # reward / termination
    # ------------------------------------------------------------------
    def _snapshot(self) -> dict[str, Any]:
        session = self._session
        own: dict[str, str] = {}
        raiders: dict[str, str] = {}
        survival = 0.0
        seen = 0
        for entity in session.world_view.entities_stable():
            state = str(entity.state.lifecycle)
            if str(entity.faction_id) == self.defender_faction:
                tags = tuple(entity.tags or ())
                if "facility" in tags:
                    # Fixed facilities are scored by ``facility_damage`` alone.
                    # Counting them in ``own`` as well charged a destroyed
                    # facility twice (-0.5 own_loss *and* -4.0 per health unit).
                    survival += float(entity.state.health)
                    seen += 1
                else:
                    own[str(entity.id)] = state
            elif str(entity.faction_id) == self.intruder_faction:
                raiders[str(entity.id)] = state
        return {"own": own, "raiders": raiders,
                "facility_health": survival, "facility_count": seen}

    def _imminent_threat(self) -> tuple[float, int, int]:
        """(imminent share, live raiders, raiders total) at the truncation cut.

        Each live raider contributes ``threat_weight`` -- the fraction of **its
        own** weapon envelope it has already closed on the nearest protected
        facility -- and the total is divided by the number of raiders that ever
        existed, mirroring the scorecard's ``depth``/``leak`` denominators.  That
        denominator is what makes neutralising a raider early permanently reduce
        the standing threat instead of merely pausing it.
        """
        snapshot = self._snapshot()
        raiders = snapshot["raiders"]
        total = max(1, len(raiders))
        facilities: list[np.ndarray] = []
        live: list[Any] = []
        for entity in self._session.world_view.entities_stable():
            if str(entity.faction_id) == self.defender_faction:
                if "facility" in tuple(entity.tags or ()):
                    facilities.append(np.asarray(entity.state.position_m[:2],
                                                 dtype=np.float64))
            elif str(entity.faction_id) == self.intruder_faction:
                # same lifecycle set the terminal rule counts as "still a threat"
                if str(entity.state.lifecycle) in ("scheduled", "active", "degraded"):
                    live.append(entity)
        if not facilities or not live:
            return 0.0, len(live), total
        accumulated = 0.0
        for entity in live:
            pos = np.asarray(entity.state.position_m[:2], dtype=np.float64)
            nearest = min(float(np.linalg.norm(pos - f)) for f in facilities)
            _, lo, hi, _ = _weapon_profile_for(entity)
            accumulated += threat_weight(nearest, hi, lo)
        return min(1.0, accumulated / total), len(live), total

    def _weapon_kills(self, receipt) -> set[str]:
        """Attacker entities this tick actually destroyed with *defender weapons*.

        The naive version of this reward counted **any** lifecycle transition into
        a lost state as a defender kill, which is exactly the over-counting defect
        already fixed in the scorecard: a suicide boat that runs aground is not a
        defender achievement, yet it paid the same +1.0.  Training on that reward
        while evaluating on the corrected scorecard means optimising a different
        objective than the one being reported, so the attribution is shared with
        the scorecard's evidence channel (``DamageIntentV2.source_kind``).
        """
        try:
            from run_episode import _damage_intent_records
        except Exception:  # pragma: no cover
            return set()
        try:
            records = _damage_intent_records(receipt)
        except Exception:  # noqa: BLE001
            return set()
        if not records:
            return set()
        faction = {str(e.id): str(e.faction_id)
                   for e in self._session.world_view.entities_stable()}
        killed: set[str] = set()
        for record in records:
            if str(record.get("source_kind")) != "weapon":
                continue
            target = str(record.get("target_entity_id"))
            source = str(record.get("source_entity_id") or "")
            if source == target:            # self-inflicted detonation
                continue
            if faction.get(target) != self.intruder_faction:
                continue
            if faction.get(source) != self.defender_faction:
                continue
            killed.add(target)
        return killed

    # ------------------------------------------------------------------
    # goal-conditioned shaping (see RewardConfig.goal_progress_bonus)
    # ------------------------------------------------------------------
    def _assigned_targets(self) -> dict[str, str]:
        """{unit_entity_id: assigned target ENTITY id} from the live plan.

        Both id forms are accepted (a planner may name a *contact* id, which is what
        the LLM emits, or an entity id, which is what the rule planner emits) --
        resolving only one of them is the bug that once left ``has_target`` at 0 for
        every intercept goal.  Distances are only ever taken from the unit's own
        contact estimate, so nothing here reaches past the observation.
        """
        if not self.goal_features or self.goal_provider is None:
            return {}
        from ie_goal_features import _field
        goals_by_unit = self.goal_provider() or {}
        # Resolve through the FACTION-level contact table, not the unit's own: the
        # planner routinely names another observer's contact for the same raider (see
        # ``_observe``).  Distances are still taken from the unit's own track below.
        contact_to_target = getattr(self, "_contact_to_target_all", {}) or {}
        assigned: dict[str, str] = {}
        for unit_id, goals in goals_by_unit.items():
            best = None
            for goal in goals or ():
                if best is None or (_field(goal, "priority", 0.5)
                                    > _field(best, "priority", 0.5)):
                    best = goal
            if best is None:
                continue
            params = dict(_field(best, "parameters", {}) or {})
            target = params.get("target_id")
            if not target:
                continue
            target = str(target)
            assigned[str(unit_id)] = contact_to_target.get(target, target)
        return assigned

    def _goal_potential(self) -> float:
        """Diagnostic mean potential for the currently resolvable assignments."""
        distances = self._goal_distances()
        return -float(np.mean(list(distances.values()))) / POS_SCALE_M if distances else 0.0

    def _goal_distances(self):
        assigned = self._assigned_targets()
        if not assigned:
            return {}
        own = getattr(self, "_own_contact", {}) or {}
        positions = {str(e.id): np.asarray(e.state.position_m[:2], dtype=np.float64)
                     for e in self._session.world_view.entities_stable()}
        distances = {}
        for unit_id, target_id in assigned.items():
            entry = own.get((unit_id, target_id))
            where = positions.get(unit_id)
            if entry is None or where is None:
                continue
            distances[(unit_id, target_id)] = float(np.linalg.norm(
                np.asarray((entry[1], entry[2]), dtype=np.float64) - where))
        return distances

    def _goal_shaping_credit(self) -> float:
        """Reward closing only on assignments present in both observations."""
        cfg = self.reward_cfg
        if not self.goal_features or not cfg.goal_progress_bonus:
            return 0.0
        distances = self._goal_distances()
        previous = self._goal_prev_distances
        self._goal_prev_distances = distances
        common = distances.keys() & previous.keys()
        if not common:
            return 0.0
        progress = float(np.mean([previous[pair] - distances[pair] for pair in common]))
        credit = float(cfg.goal_progress_bonus) * progress / POS_SCALE_M
        remaining = max(0.0, float(cfg.goal_credit_cap) - self._goal_credit_total)
        credit = float(np.clip(credit, -remaining, remaining))
        self._goal_credit_total += credit
        return credit

    def _executed_shots(self, receipt, tick: int | None = None,
                        fire_records=None) -> int:
        """Count only shots the engine actually executed this tick.

        The reward used to charge ``shot_cost`` per *submitted* fire action.
        Measured on a real episode: 161 submitted vs 10 executed (the engine
        rejects the rest on cooldown / duplicate contact / envelope grounds), so
        the ammo penalty was overstated by ~16x and penalised the policy for
        actions that never happened.

        Also records, per unit, the tick of its last *executed* shot, which is what
        the fire mask needs to honour weapon cooldown.  The entity id is recovered
        by longest-match against the known slot ids rather than by splitting the
        child id: entity ids contain dots (``defender.uav-01``), so
        ``rl.fire.defender.uav-01.123`` does not split unambiguously.
        """
        children = getattr(receipt, "child_receipts", ()) or ()
        count = 0
        submitted_owners = {str(record["action_id"]): str(record["entity_id"])
                            for record in (fire_records or ())}
        mobile_units = {slot.entity_id for slot in self._slots}
        self._last_executed_fire_ids = set()
        for child in children:
            child_id = str(getattr(child, "child_id", "") or "")
            if fire_records is not None:
                owner = submitted_owners.get(child_id)
                if owner not in mobile_units:
                    continue
            elif not child_id.startswith("rl.fire."):
                continue
            if (getattr(child, "kind", None) == "discrete"
                    and getattr(child, "status", None) == "executed"):
                count += 1
                self._last_executed_fire_ids.add(child_id)
                if tick is not None:
                    if fire_records is None:
                        owner = max((s.entity_id for s in self._slots
                                     if child_id.startswith(f"rl.fire.{s.entity_id}.")),
                                    key=len, default=None)
                    if owner is not None:
                        self._last_fire_tick[owner] = int(tick)
        return count

    def _executed_assigned_shots(self, fire_records) -> int:
        """Executed shots at the assigned target, paid at most ``overkill_cap`` times.

        ``fire_records`` are this decision's submissions (their ``action_id`` is the
        engine's ``child_id``); the executed set was just collected by
        ``_executed_shots``.  Attribution goes through the same contact->target table
        the fire head is decoded with, so a shot at the plan's target is recognised
        even when two observers hold separate contacts for one raider.

        WHY NOT "ONCE PER TARGET".  The first version of this change paid the bonus
        once per (unit, target) per episode, to stop the reward encouraging volume.
        That was an over-correction, and it was caught by repeats: training v10 -> v11
        with nothing else behaviourally different produced a **tail on both cheap
        scenarios** (IE-01 seed 7: 0.9028 / 0.6633 / 0.9028, sd 0.138, against v9's
        0.9020/0.9024/0.9024 sd 0.0002; IE-02 showed the same 0.662 tail).  Under the
        doctrine's cap of two shots per target, paying for the second shot is not
        paying for spray -- it is paying for kill probability (one shot 0.5, two 0.75,
        since ``effect.surface-missile-hit``/``effect.loitering-hit`` kill on one hit
        at Pk 0.5-0.75).  Removing it made the second shot unrewarded while it still
        consumed a scarce round.

        So the payment is per shot but bounded by the same cap the doctrine uses: in
        the default (cap) path this is bit-identical to the pre-regression signal, and
        under the release doctrine it still cannot pay for a 14-round spray.
        """
        if not self.goal_features or not self.reward_cfg.goal_shot_bonus:
            return 0
        executed = getattr(self, "_last_executed_fire_ids", set())
        if not executed:
            return 0
        assigned = self._assigned_targets()
        if not assigned:
            return 0
        contact_to_target = {str(entry[0]): str(target)
                             for (_unit, target), entry in
                             (getattr(self, "_own_contact", {}) or {}).items()}
        credited = getattr(self, "_goal_shot_credited", None)
        if credited is None:
            credited = self._goal_shot_credited = {}
        budget = max(1, int(getattr(self, "_goal_shot_budget", 0) or 1))
        paid = 0
        for record in fire_records or ():
            if str(record.get("action_id")) not in executed:
                continue
            unit = str(record.get("entity_id"))
            target = contact_to_target.get(str(record.get("contact_id")))
            if target is None or assigned.get(unit) != target:
                continue
            key = (unit, target)
            if credited.get(key, 0) >= budget:
                continue
            credited[key] = credited.get(key, 0) + 1
            paid += 1
        return paid

    def _scale_goal_credit(self, credit: float) -> float:
        remaining = max(0.0, float(self.reward_cfg.goal_credit_cap)
                        - self._goal_credit_total)
        credit = float(np.clip(credit, 0.0, remaining))
        self._goal_credit_total += credit
        return credit

    def _reward(self, receipt, *, fired: int,
                terminated_outcome: Optional[str] = None,
                assigned_hits: int = 0) -> tuple[float, dict[str, Any]]:
        cfg = self.reward_cfg
        now = self._snapshot()
        prev = self._prev or now
        lost = {"disabled", "destroyed", "wreck", "despawned"}
        own_lost = sum(1 for k, v in now["own"].items()
                       if v in lost and prev["own"].get(k) not in lost)
        combat_kills = self._weapon_kills(receipt)
        # only attribute a kill once per entity (per episode -- see
        # ``_reset_episode_state``)
        seen = self._credited_kills
        new_kills = {k for k in combat_kills if k not in seen}
        seen |= new_kills
        raiders_lost_all = sum(1 for k, v in now["raiders"].items()
                               if v in lost and prev["raiders"].get(k) not in lost)
        damage = max(0.0, prev["facility_health"] - now["facility_health"])
        # Forward-interception incentive, aligned with the scorecard's depth
        # layer (0.20 of the overall score): a raider stopped far from what it
        # is attacking is worth more than one stopped on the doorstep.  Held
        # 2.0 was a dead parameter before this.
        depth_credit = 0.0
        if new_kills and cfg.depth_bonus:
            positions = {str(e.id): np.asarray(e.state.position_m[:2],
                                               dtype=np.float64)
                         for e in self._session.world_view.entities_stable()}
            for entity_id in new_kills:
                where = positions.get(entity_id)
                if where is None:
                    continue
                depth = float(np.linalg.norm(where - self._objective))
                depth_credit += cfg.depth_bonus * min(
                    1.0, depth / max(cfg.depth_reference_m, 1.0))
        terminal = 0.0
        if terminated_outcome == "defender_success":
            terminal = cfg.terminal_win
        elif terminated_outcome == "intruder_success":
            terminal = cfg.terminal_loss
        total = (cfg.raider_neutralised * len(new_kills)
                 + depth_credit
                 + terminal
                 + cfg.facility_damage * damage
                 + cfg.own_loss * own_lost
                 - cfg.shot_cost * fired
                 - cfg.time_penalty)
        # Goal-conditioned shaping (fifth arm).  Both terms are 0 on the pure-RL arm
        # (``goal_features`` off), so the two arms' mission reward stays identical --
        # only the arm that receives a plan is paid for acting on it.
        goal_progress = self._goal_shaping_credit()
        goal_shot = self._scale_goal_credit(
            float(cfg.goal_shot_bonus) * int(assigned_hits))
        total += goal_progress + goal_shot
        self._prev = now
        return total, {"own_lost": own_lost,
                       "raiders_lost": len(new_kills),
                       "raiders_lost_all_causes": raiders_lost_all,
                       "depth_credit": round(depth_credit, 4),
                       "terminal_reward": terminal,
                       "facility_damage": round(damage, 4), "fired": fired,
                       "goal_progress": round(goal_progress, 5),
                       "goal_shot": round(goal_shot, 5),
                       "goal_assigned_hits": int(assigned_hits)}

    def _terminal_from(self, receipt):
        try:
            from run_episode import _receipt_terminal
        except Exception:
            return None
        try:
            return _receipt_terminal(receipt)
        except Exception:
            return None

    @staticmethod
    def _outcome_of(terminal_result) -> Optional[str]:
        """Extract the bare outcome token from a terminal result.

        The engine's terminal type is a frozen dataclass that used to reach this
        point only as ``{"result": "<repr>"}`` (see ``run_episode._receipt_terminal``).
        Reading ``.outcome`` off that dict yields ``""``, so the reward's
        ``terminal_win`` / ``terminal_loss`` terms -- the largest in the whole
        reward, +-2.0 -- were **never applied**, and ``self.terminal_outcome``
        became an entire dict blob so the trainer's win/loss counters stayed at
        zero across every episode.  Both shapes are accepted here so a future
        regression in the harness cannot silently kill the terminal signal again.
        """
        if terminal_result is None:
            return None
        if isinstance(terminal_result, dict):
            for key in ("outcome", "result"):
                value = terminal_result.get(key)
                if isinstance(value, str) and value and "TerminalMissionResult" \
                        not in value:
                    return value
            return None
        value = getattr(terminal_result, "outcome", None)
        return str(value) if value else None
