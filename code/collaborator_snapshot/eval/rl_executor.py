"""Fifth arm: the LLM's plan executed by a learned policy instead of by rules.

The ablation question is "what changes if the layer that turns a goal into engine
commands is learned rather than hand-coded?", so **only** that layer may differ.
Everything else is inherited: this class subclasses ``GOAIExecutorV2`` and overrides
exactly one method, ``_execute_goal``, which is the point in ``act()`` where a goal
becomes a (navigation command, fire action) pair.

That choice matters more than it looks.  ``act()`` is not just geometry -- it also

  * activates pending goals and feasibility-screens them,
  * posts ``StatusReport``s back to the broker,
  * enters/leaves safe mode when goals stop arriving,
  * stops units that hold no goal,
  * runs shore-defence CIWS,
  * prunes terminal goals.

The LLM planner *consumes* those reports as part of its input, so an executor that
skipped the bookkeeping would give its planner a different observation and the
comparison would no longer isolate the executor.  Inheriting keeps all of it
byte-identical to the hybrid arm; only the goal->command arithmetic is replaced.

Action space is deliberately identical to the rule executor's: absolute heading and
absolute speed via ``self._navigation`` and a single ``fire_weapon`` via
``self._fire_action``, both of which are the base class's own builders, so the engine
sees the same message shapes from both arms.

Target adherence is measured, not enforced (see ARM5_LLM_RL_EXECUTOR_DESIGN.md §7.1):
the reward contains no goal term, so a policy that ignored the plan entirely would
drift towards the pure-RL arm, and the way to detect that is to count how often the
target actually engaged was the one the plan named.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from ie_goal_features import active_by_unit
from ie_rl_env import IERlEnv
from ie_rl_policy import load_theta, numpy_sample, read_meta
from rl_agent import _resolve_speed_source
from v2_executor import (ACTIVE_LIFECYCLES, GOAIExecutorV2, _dist3,
                         contact_entity_suffix)
from goai_protocol import (PRIORITY_EPSILON, StatusReport, T_DECISION_MAX,
                           T_STATUS_PERIOD)


class RLExecutorV2(GOAIExecutorV2):
    """Goal-conditioned policy standing in for the rule-based executor."""

    def __init__(self, *args: Any, theta_path: str | Path,
                 scenario_id: str = "",
                 decision_interval: int = 5, deterministic: bool = False,
                 speed_source: str | None = None, seed: int = 7,
                 overkill_cap: int = 2, assess_window_ticks: int = 12,
                 overkill_release: bool = False,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.theta_path = Path(theta_path)
        self._theta = load_theta(self.theta_path)
        # Passed in rather than introspected: the session does not expose a
        # scenario id under any of the names I guessed, and a silently empty id
        # surfaced as "unknown formal V2 scenario: ''" from deep inside the attack
        # profile loader -- an abort at tick 0 that looks nothing like its cause.
        # run_episode already knows the id, so it hands it over.
        self.scenario_id = str(scenario_id)
        self.decision_interval = max(1, int(decision_interval))
        self.deterministic = bool(deterministic)
        self._rng = np.random.default_rng(seed)
        # The ablation is against the RECORDED hybrid arm, whose executor commands
        # 40 m/s for air and 8 for surface.  Defaulting to that convention here is
        # what makes the head-to-head a like-for-like comparison of executors
        # rather than of two different speed tables -- but a default is not a
        # pin: the checkpoint's own provenance wins over it when present, and the
        # resolution is recorded so a silently-flipped convention is visible
        # (see ARM5_LLM_RL_EXECUTOR_DESIGN.md §14.18).
        self.speed_source, self.speed_source_provenance = _resolve_speed_source(
            speed_source, read_meta(self._theta), "legacy_tags")

        self._env: Optional[IERlEnv] = None
        self._decision_tick: Optional[int] = None
        self._pending: Dict[str, tuple[Any, Optional[dict]]] = {}
        # Units that have already fired in the CURRENT decision window.  Without
        # this the same discrete fire action was re-submitted on every tick of the
        # window -- ``act()`` runs each tick and ``_execute_goal`` re-issued the
        # cached action each time.  Two consequences, both measured:
        #   * shot accounting was inflated 5x (the engine accepts the first and
        #     rejects the rest on cooldown/duplicate grounds -- the same effect that
        #     showed up earlier as "161 submitted vs 10 executed");
        #   * it could ABORT the episode: `session.contact_invalid: opaque contact is
        #     not a current observation owned by the firing entity` (measured at
        #     t99) when the cached contact was no longer current a few ticks later.
        # Discrete actions are documented to execute at most once, so once per
        # window is also the correct semantics.
        self._fire_issued: set[str] = set()
        # Goals already reported terminal, so a report is posted once per goal.
        self._reported_terminal: set[str] = set()
        # Fire doctrine, mirrored from the rule executor so the ablation compares
        # CONTROL, not the presence or absence of doctrine.
        #
        # First reading of the fifth arm made the cost of omitting it plain:
        # 60 shots in 169 ticks against the hybrid arm's 12-13 shots in 899 ticks,
        # with the ammo layer at 0.333.  The rule executor carries
        # ``fire_doctrine="assess"`` (wait ``assess_window_ticks`` before re-engaging
        # the same target) plus ``deconflict_fire`` and ``overkill_cap=2`` (stop
        # feeding a target that already has enough); none of that existed here, so
        # the learned executor was being compared against a hand-written doctrine as
        # well as against a hand-written controller.
        #
        # Applied HERE rather than in ``IERlEnv.fire_mask``: the mask removes choices
        # the ENGINE rejects, while an overkill cap is doctrine the engine would
        # happily accept.  Putting doctrine in the mask would silently change the
        # pure-RL arm too, which must keep learning its own discipline.
        self.overkill_cap = max(1, int(overkill_cap))
        self.assess_window_ticks = max(0, int(assess_window_ticks))
        # Whether a salvo that has been assessed as FAILED releases its overkill
        # credit.  OFF by default on purpose: the frozen rule executor keeps a
        # permanent per-target cap, and the ablation is only apples-to-apples while
        # both executors share that doctrine.  Measured reason this exists at all --
        # IE-03 fields 7 armed USVs x 2 surface missiles = 14 rounds against 3 suicide
        # boats, yet every arm fires exactly 6 = 3 x overkill_cap, and
        # `effect.surface-missile-hit` is kinetic-terminal (one hit kills) while the
        # cap of 2 was calibrated for the AIR round (kinetic-partial 0.6, two hits).
        # So two misses permanently disarm a live boat: seed 19 spent its salvo at
        # tick~5, hit nothing, was suppressed 1440 times with 8 missiles still aboard,
        # and lost to `rule.assets-lost`.  See _w1_test_overkill_release.py and
        # LLMRL_CURRENT_AUDIT.md.
        self.overkill_release = bool(overkill_release)
        self._shots_on_target: Dict[str, int] = {}
        self._last_shot_tick: Dict[str, int] = {}
        self.doctrine = {"suppressed_overkill": 0, "suppressed_assess": 0,
                         "suppressed_unresolvable": 0}
        # Goal adherence bookkeeping (see the module docstring).
        self.adherence = {"shots": 0, "on_assigned_target": 0,
                          "with_goal": 0, "with_target_goal": 0}
        self.stats.update({"rl_decisions": 0, "rl_forward_ticks": 0})

    # ------------------------------------------------------------------
    def _ensure_env(self, session) -> IERlEnv:
        if self._env is None:
            scenario = self.scenario_id or self._scenario_id(session)
            if not scenario:
                raise ValueError(
                    "RLExecutorV2 has no scenario id: pass scenario_id=… (the "
                    "session does not reliably expose one).")
            env = IERlEnv(
                scenario, seed=self._rng.integers(1 << 30),
                decision_interval=self.decision_interval,
                goal_features=True, speed_source=self.speed_source,
            )
            # Fail loudly and early on a layout mismatch.  Without this the mistake
            # surfaces as a matmul shape error deep inside numpy_sample, at which
            # point the obvious-but-wrong conclusion is "the executor is broken"
            # rather than "this checkpoint was not trained with goal features".
            # The same trap already cost time twice: the pair block grew 6 -> 8 and
            # the goal block 0 -> 24.
            expected = int(self._theta["trunk0.w"].shape[0])
            actual = env.observation_size
            if expected != actual:
                raise ValueError(
                    f"RL executor checkpoint expects obs_dim={expected} but the "
                    f"goal-conditioned environment produces {actual}. Train the "
                    f"fifth arm with goal_features=True (or pass a checkpoint that "
                    f"was): theta={self.theta_path}")
            env.attach(session)
            # Read the broker every time, not once: goals are preempted between
            # decisions, and the rule executor reads the broker every tick.
            env.goal_provider = lambda: active_by_unit(self.broker.active)
            self._env = env
        return self._env

    @staticmethod
    def _scenario_id(session) -> str:
        for attr in ("scenario_id", "public_id"):
            value = getattr(session, attr, None)
            if value:
                return str(value)
        resolved = getattr(session, "resolved", None) or getattr(session, "scenario", None)
        return str(getattr(resolved, "public_id", "") or "")

    # ------------------------------------------------------------------
    def _run_policy_once(self, session, tick: int) -> None:
        """One forward pass per decision window; results cached per unit."""
        if self._decision_tick is not None \
                and tick - self._decision_tick < self.decision_interval \
                and self._pending:
            return
        env = self._ensure_env(session)
        obs = env.observe()
        mask = env.fire_mask()
        action, _logprob, _value, _out = numpy_sample(
            self._theta, obs, mask, self._rng, env.num_fire_choices,
            deterministic=self.deterministic)
        self.prepare_action(env, action, tick)

    def prepare_action(self, env, action, tick: int) -> None:
        """Cache a sampled action using the same decoding as policy inference."""
        # Precompute each unit's decoded command once; ``_execute_goal`` is called
        # per unit and must not re-run the network.
        self._pending = {}
        for index, slot in enumerate(env._slots):
            heading, speed, contact_id = env.decode_unit_action(index, action)
            self._pending[slot.entity_id] = ((heading, speed), contact_id, action)
        self._decision_tick = tick
        self._fire_issued = set()          # new window -> each unit may fire once
        self.stats["rl_decisions"] += 1
        self.stats["rl_forward_ticks"] = tick
        # Release targets that have left the contact picture (destroyed or lost), the
        # same way the rule executor prunes ``_engaged_targets``/``_shots_on_target``
        # -- otherwise a target that is later re-acquired would be treated as already
        # saturated and never engaged again.
        live = {str(t) for t in getattr(env, "_last_contacts", [])}
        # Canonical contact_id -> TARGET ENTITY map, taken from the same table the
        # environment uses to decode a fire action.  Deriving the target from the
        # contact id by string surgery instead would key the doctrine per
        # (observer, target) contact -- two observers seeing one raider would look
        # like two different targets and the cap would never bind, which is exactly
        # the over-counting the rule executor's per-target cap exists to prevent.
        self._contact_to_target = {
            str(entry[0]): str(target)
            for (unit_id, target), entry in getattr(env, "_own_contact", {}).items()
        }
        self._prune_shot_ledger(live)

    def _prune_shot_ledger(self, live_targets: set[str]) -> None:
        for target in list(self._shots_on_target):
            if target not in live_targets:
                self._shots_on_target.pop(target, None)
                self._last_shot_tick.pop(target, None)

    # ------------------------------------------------------------------
    def _target_of_contact(self, contact_id: str) -> str:
        mapped = getattr(self, "_contact_to_target", {}).get(str(contact_id))
        if mapped:
            return mapped
        for target in set(getattr(self, "_contact_to_target", {}).values()):
            if contact_id == target or contact_id.endswith("." + target):
                return target
        return contact_entity_suffix({"contact_id": contact_id})

    def _assess_window_for(self, unit_id: str) -> int:
        """Assess window for this unit, never shorter than its round's flight time.

        A guided round's outcome is unknown until it arrives: every weapon in this
        bundle is ``delivery_model: guided_missile`` and the engine flies it
        (`MissileFlightV2`), while ``hit_probability`` is only rolled at detonation.
        The catalog speeds differ by an order of magnitude -- the air rounds cruise at
        250-320 m/s (25-32 ticks to 8000 m), the surface missile at 15 m/s (200 ticks
        to 3000 m) -- so the flat 12-tick window is 16x too short on the surface
        round.  Measured on IE-03 with a 12-tick release: 8 extra missiles were fired
        into boats whose first salvo was still in the air, taking the ammo layer from
        1.0 to 0.429 and the score from 1.0 to 0.9592.

        Only consulted by the release path; the default path keeps the flat window so
        the comparison with the frozen rule executor stays like-for-like.
        """
        base = self.assess_window_ticks
        env = self._env
        if env is None:
            return base
        for slot in getattr(env, "_slots", ()):
            if slot.entity_id == unit_id:
                return max(base, int(getattr(slot, "flight_ticks", 0) or 0))
        return base

    def _doctrine_blocks(self, contact_id: str, tick: int,
                         unit_id: str | None = None) -> Optional[str]:
        """Which doctrine rule suppresses this shot, or None to allow it.

        Order matters and is preserved from the original: the cap is consulted BEFORE
        the assess window, so with cap=2 / window=12 the effective rule is "at most one
        shot per target per 12 ticks, and two shots in total".  The optional release
        (``overkill_release``, default off) only touches the *total*: once a whole
        assess window has passed and the target is still in the contact picture, those
        shots cannot have destroyed it, so their credit is returned.
        """
        target = self._target_of_contact(contact_id)
        window = (self._assess_window_for(unit_id) if self.overkill_release
                  else self.assess_window_ticks)
        if self.overkill_release:
            last_seen = self._last_shot_tick.get(target)
            if (last_seen is not None
                    and tick - last_seen >= window
                    and self._shots_on_target.get(target, 0) > 0):
                # The salvo resolved and the target survived -- it is still visible,
                # because a destroyed target leaves the contact list (and
                # ``_prune_shot_ledger`` drops it).  Return the credit, otherwise a
                # single unlucky salvo makes a live target unengageable for the rest
                # of the episode even with rounds in the magazine.
                self._shots_on_target[target] = 0
                self.doctrine["released_overkill"] = (
                    self.doctrine.get("released_overkill", 0) + 1)
        if self._shots_on_target.get(target, 0) >= self.overkill_cap:
            self.doctrine["suppressed_overkill"] += 1
            return "overkill"
        last = self._last_shot_tick.get(target)
        if last is not None and tick - last < window:
            self.doctrine["suppressed_assess"] += 1
            return "assess"
        return None

    # ------------------------------------------------------------------
    def _report_goal_state(self, state, entity_state, tick: int, contacts) -> None:
        """Mirror the rule executor's *reporting*, without mirroring its control.

        ``act()`` (shared, unmodified) files the pending/feasibility reports, but the
        rule executor ALSO reports a goal terminal from inside ``_execute_goal``:
        ``timeout`` when the deadline passes and ``completed``/``target_lost`` when
        the named target leaves the contact picture.  The learned executor reported
        none of these, and that is not a cosmetic difference -- the LLM planner
        *consumes* ``StatusReport``s, so the two arms were feeding their (identical)
        planner different pictures of progress:

        ==================  ==============  =============  ==========
        arm                 goals_completed goals_accepted  seed/scenario
        ==================  ==============  =============  ==========
        ``llm`` (hybrid)    **3**           35             IE-01/7
        ``llm-rl`` (5th)    **0**           50             IE-01/7
        ``rule``            9 (22 rejected) 48             IE-01/7
        ``rule-rl``         **0**           33             IE-01/7
        ==================  ==============  =============  ==========

        A fifth arm whose planner never learns that a goal finished is not the same
        experiment as one whose planner does.  Reporting is bookkeeping (the same
        class of work ``act()`` already does for both arms), so it is mirrored here;
        the *decision* is not -- the policy's heading/speed command stands even after
        a terminal report, unlike the rule executor which stops the unit.  Which of
        those two reactions is better is exactly what the ablation is asking.
        """
        cmd = getattr(state, "command", None)
        if cmd is None:
            return
        task_id = getattr(cmd, "task_id", None)
        if task_id is not None and task_id in self._reported_terminal:
            return
        params = getattr(cmd, "parameters", None) or {}
        deadline = getattr(cmd, "deadline", None)
        if deadline is not None and (tick - int(cmd.issued_at)) > deadline:
            if task_id is not None:
                self._reported_terminal.add(task_id)
            self._post(state, "timeout", tick, progress=state.last_progress,
                       detail=f"deadline {deadline} exceeded")
            return
        if getattr(cmd, "goal_type", "") in ("intercept", "ambush", "track"):
            target = params.get("target_id")
            # ``contacts`` is keyed by contact id (``_contacts_by_id``), which is the
            # same form the planner writes into ``target_id``; the rule executor tests
            # membership exactly this way, so this is the same condition, not a
            # look-alike.
            if target and str(target) not in contacts:
                if task_id is not None:
                    self._reported_terminal.add(task_id)
                self._post(state, "completed", tick, progress=1.0,
                           anomaly="target_lost", detail=f"target {target} gone")
                return
        # Arrival completion.  The rule executor posts it for exactly two goal types
        # (`waypoint`, `return`); `patrol`/`loiter` deliberately do NOT, they start a
        # sector sweep.  The aim point comes from the base class's own
        # `_goal_position`, not a copy -- re-deriving goal geometry here is how the
        # speed table, the fire envelope and the goal encoder each ended up with two
        # disagreeing versions.
        if getattr(cmd, "goal_type", "") in ("waypoint", "return"):
            aim = self._goal_position(cmd, entity_state, contacts)
            if aim is not None:
                own_pos = tuple(float(v) for v in entity_state["position_m"])
                if _dist3(own_pos, aim) <= self.config.arrive_radius_m:
                    if task_id is not None:
                        self._reported_terminal.add(task_id)
                    self._post(state, "completed", tick, progress=1.0)

    def _goal_position(self, cmd, own, contacts):
        if cmd.goal_type != "return":
            position = (cmd.parameters or {}).get("position")
            if position is not None:
                try:
                    if len(position) >= 3:
                        return tuple(float(value) for value in position[:3])
                except (TypeError, ValueError):
                    return None
        return super()._goal_position(cmd, own, contacts)

    def report_goals_only(self, session, tick: int) -> None:
        """Advance broker status during rollout without submitting control actions."""
        observation = session.world_view.observation(
            observer_faction_id=self.config.faction_id)
        own = self._own_by_id(observation)
        contacts = self._contacts_by_id(observation)
        # Keep planner-facing bookkeeping aligned with GOAIExecutorV2.act.
        # Training deliberately does not submit a second control action, but it
        # must still expose safe-mode transitions and periodic progress reports;
        # otherwise the LLM receives a different report stream during PPO
        # rollouts than during evaluation.
        has_fresh = any(not state.terminal and state.status == "pending"
                        for state in self.broker.active.values())
        if has_fresh:
            self.last_goal_tick = tick
            self.safe_mode = False
        elif not self.safe_mode and (tick - self.last_goal_tick) >= T_DECISION_MAX:
            self.safe_mode = True
            self.broker.post_report(StatusReport(
                task_id="safe_mode", unit_id=None, status="executing",
                progress=0.0, anomaly="comm_loss", reported_at=tick,
                anomaly_detail=(f"no new goal for {tick - self.last_goal_tick} "
                                "ticks")))
        if self.safe_mode:
            self.stats["safe_mode_ticks"] = (
                self.stats.get("safe_mode_ticks", 0) + 1)
        for state in list(self.broker.active.values()):
            if state.terminal:
                continue
            command = state.command
            unit = own.get(command.unit_id) if command.unit_id else None
            if unit is None or unit.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                self._post(state, "failed", tick, anomaly="platform_damaged",
                           detail=f"unit {command.unit_id} destroyed/disabled")
                continue
            if state.status == "pending":
                infeasible = self._check_feasibility(command, contacts)
                if infeasible is not None:
                    anomaly, detail = infeasible
                    self._post(state, "infeasible", tick, anomaly=anomaly,
                               detail=detail)
                    continue
                state.status = "executing"
                state.start_tick = tick
                target = self._goal_position(command, own, contacts)
                if target is not None:
                    position = tuple(float(v) for v in unit["position_m"])
                    state.initial_dist = _dist3(position, target)
        selected = {}
        for state in self.broker.active.values():
            if state.terminal or state.command.unit_id not in own:
                continue
            unit_id = state.command.unit_id
            current = selected.get(unit_id)
            if (current is None or state.command.priority
                    > current.command.priority + PRIORITY_EPSILON):
                selected[unit_id] = state
        for unit_id, state in selected.items():
            self._report_goal_state(state, own[unit_id], tick, contacts)
        if tick - self.last_periodic_report >= T_STATUS_PERIOD:
            self.last_periodic_report = tick
            for state in self.broker.active.values():
                if state.status == "executing" and not state.terminal:
                    self.broker.reports.append(StatusReport(
                        task_id=state.command.task_id,
                        unit_id=state.command.unit_id,
                        status="executing",
                        progress=state.last_progress,
                        reported_at=tick))
        self.broker.prune_terminal()

    # ------------------------------------------------------------------
    def _execute_goal(self, session, uid, entity_state, tags, state, tick,
                      contacts, meta_entity):
        """Replaces the rule geometry: the network's own heading/speed/fire."""
        self._run_policy_once(session, tick)
        self._report_goal_state(state, entity_state, tick, contacts)
        entry = self._pending.get(uid)
        if entry is None:
            # The unit is controllable but the env does not know it (should not
            # happen); fall back to the base behaviour rather than freezing it.
            return super()._execute_goal(session, uid, entity_state, tags, state,
                                         tick, contacts, meta_entity)
        (heading, speed), contact_id, _action = entry
        command = self._navigation(uid, tick, own=entity_state,
                                   speed_mps=speed, heading_deg=heading)
        if contact_id is None:
            return command, None

        # One discrete fire action per unit per decision window (see __init__).
        if uid in self._fire_issued:
            return command, None
        policy = self._policy_for(tags)
        if policy is None:
            return command, None

        # Validate against the ENGINE'S OWN gate before submitting.
        #
        # ``lifecycle_v2._engagement_request`` resolves the contact through
        # ``contact_store.resolve_owned_observation(evidence_id, owner, current_tick)``
        # and raises ``session.contact_invalid`` when it returns None -- which ABORTS
        # the whole episode.  The store holds exactly one record per evidence_id
        # (``install`` raises otherwise) and is rebuilt during ``step()``, so a
        # contact that was published when the decision was taken can be gone by the
        # time the action is applied: the sensor's ``update_ticks`` cadence may not
        # republish it, or the target may have left range.  Asking the same resolver
        # first turns "abort the episode" into "hold fire", which is also the honest
        # reading -- if the engine will not accept the shot, the choice was never
        # really available.
        if not self._contact_is_resolvable(session, uid, contact_id, tick):
            self.doctrine["suppressed_unresolvable"] += 1
            return command, None

        # Fire doctrine (see __init__): mirror the rule executor's assess window and
        # overkill cap so the comparison is about control rather than doctrine.
        target = self._target_of_contact(contact_id)
        if self._doctrine_blocks(contact_id, tick, uid) is not None:
            return command, None
        self._shots_on_target[target] = self._shots_on_target.get(target, 0) + 1
        self._last_shot_tick[target] = tick
        self._fire_issued.add(uid)

        fire_action = self._fire_action(uid, tick, policy=policy,
                                        contact_id=contact_id)

        # Adherence: was the target we fired at the one this unit's own goal named?
        assigned = None
        if state is not None and getattr(state, "command", None) is not None:
            assigned = (state.command.parameters or {}).get("target_id")
        self.adherence["shots"] += 1
        if assigned:
            self.adherence["with_target_goal"] += 1
            if self._target_of_contact(str(assigned)) == target:
                self.adherence["on_assigned_target"] += 1
        if state is not None and getattr(state, "command", None) is not None:
            self.adherence["with_goal"] += 1
        return command, fire_action

    # ------------------------------------------------------------------
    def _contact_is_resolvable(self, session, uid: str, contact_id: str,
                               tick: int) -> bool:
        """True when the engine's own contact resolver would accept this shot.

        Fail-open on introspection errors (missing private attribute, changed
        engine internals): suppressing every shot because a guard could not be read
        would be a worse failure than the one it guards against, and the abort it
        prevents is visible in the report.
        """
        store = getattr(getattr(session, "_world", None), "contact_store", None)
        if store is None or not hasattr(store, "resolve_owned_observation"):
            self.doctrine["resolver_unavailable"] = (
                self.doctrine.get("resolver_unavailable", 0) + 1)
            return True
        try:
            return store.resolve_owned_observation(
                evidence_id=contact_id, owner_entity_id=uid,
                current_tick=int(tick)) is not None
        except Exception:  # noqa: BLE001
            self.doctrine["resolver_unavailable"] = (
                self.doctrine.get("resolver_unavailable", 0) + 1)
            return True

    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self.stats)
        shots = self.adherence["shots"]
        stats["adherence"] = {
            **self.adherence,
            "on_assigned_ratio": (round(self.adherence["on_assigned_target"] / shots, 4)
                                  if shots else None),
            "with_goal_ratio": (round(self.adherence["with_goal"] / shots, 4)
                                if shots else None),
            "with_target_goal_ratio": (
                round(self.adherence["with_target_goal"] / shots, 4)
                if shots else None),
            "on_assigned_given_target": (
                round(self.adherence["on_assigned_target"]
                      / self.adherence["with_target_goal"], 4)
                if self.adherence["with_target_goal"] else None),
        }
        stats["doctrine"] = dict(self.doctrine)
        stats["overkill_cap"] = self.overkill_cap
        stats["assess_window_ticks"] = self.assess_window_ticks
        stats["overkill_release"] = self.overkill_release
        stats["theta"] = str(self.theta_path)
        stats["speed_source"] = self.speed_source
        stats["speed_source_provenance"] = self.speed_source_provenance
        stats["checkpoint_meta"] = read_meta(self._theta)
        return stats
