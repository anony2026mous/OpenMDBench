"""Read-only descriptions of existing candidate tracking/report state.

These are referee supplements, not replacement score formulas or checkpoints.
"""
from copy import deepcopy
import math

SCHEMA = "referee-tracking-raw-metrics@1.0"


def _base(state, dt):
    if type(dt) not in (int, float) or not math.isfinite(dt) or dt <= 0:
        raise ValueError("positive finite native tick duration required")
    p, n = state["parameters"], state["samples"]
    return {"schema_version": SCHEMA, "audience": "referee_only",
        "metric_id": p["metric_id"], "kind": p["kind"], "sample_count": n,
        "window_start_tick": p["start_tick"], "window_end_tick_exclusive": p["end_tick"],
        "last_evaluated_tick": state["last_tick"],
        "last_sampled_tick": min(state["last_tick"], p["end_tick"] - 1) if n else None,
        "native_candidate_score_value": state["last_value"],
        "scoring_window_data_status": "sampled" if n else "not_yet_sampled", "physics_dt_seconds": dt}


def tracking_statistics(state, dt):
    result = _base(state, dt); p, n = state["parameters"], state["samples"]
    targets = {}
    for target, h in state["targets"].items():
        seen = h["seen_ticks"]
        targets[target] = {
            "fresh_contact_sample_ticks": seen if n else None,
            "fresh_contact_sample_seconds": seen * dt if n else None,
            "fresh_contact_fraction": seen / n if n else None,
            "gap_at_last_sample_ticks": h["gap_ticks"] if n else None,
            "longest_contact_gap_ticks": h["longest_gap_ticks"] if n else None,
            "longest_contact_gap_seconds": h["longest_gap_ticks"] * dt if n else None,
            "last_fresh_contact_scoring_tick": h["last_contact_tick"],
            "remembered_observer_group": h["owner_group"],
            "fresh_contact_minimum_observer_age_sum_ticks": h["age_total"] if n else None,
            "fresh_contact_mean_minimum_observer_age_ticks": h["age_total"] / seen if seen else None,
            "credited_group_change_count": sum(h["handover_counts"].values()) if n else None,
            "credited_group_changes_by_edge": dict(h["handover_counts"]) if n else None,
            "credited_group_change_gap_ticks": list(h["handover_gaps"]) if n else None,
            "maximum_credited_group_change_gap_ticks": max(h["handover_gaps"]) if h["handover_gaps"] else None}
    windows = {}
    for spec in p["reacquisition_events"]:
        event_id = spec["event_id"]; window = state["event_windows"].get(event_id)
        first = window["start_tick"] if window is not None else None
        rows = {}
        for target in state["targets"]:
            delay = window["reacquired"].get(target) if window is not None else None
            if first is None: status = "event_not_observed_in_scoring_window"
            elif delay is not None: status = "qualifying_contact_within_deadline"
            elif result["last_sampled_tick"] >= first + spec["deadline_ticks"]: status = "deadline_missed"
            elif state["last_tick"] >= p["end_tick"]: status = "censored_by_scoring_window"
            else: status = "awaiting_qualifying_contact"
            rows[target] = {"data_status": status, "event_to_qualifying_contact_ticks": delay,
                            "event_to_qualifying_contact_seconds": delay * dt if delay is not None else None}
        windows[event_id] = {"first_scoring_tick_observing_event": first, "deadline_ticks": spec["deadline_ticks"], "targets": rows}
    result.update(targets=targets, event_windows=windows, observer_groups=deepcopy(p["observer_groups"]),
        declared_handover_edges=deepcopy(p["handover_edges"]), definitions={
            "contact": "Model-eligible fresh contact at a scoring sample; may be a still-valid cached measurement, not necessarily a newly acquired physical measurement",
            "gap": "Consecutive scoring samples without any eligible fresh owner; includes leading and trailing gaps inside this metric's own window",
            "age": "Minimum eligible observer measurement age, averaged only over target samples with fresh contact; not every observer or all target-time samples",
            "handover": "Existing model's credited observer-group changes; not explicit communication handshakes or proof of physically calibrated transfer",
            "remembered_group": "Last credited group, possibly historical during a gap or after the scoring window",
            "reacquisition": "Event-to-first qualifying fresh contact within deadline; a zero or positive credit does not itself establish prior contact loss"})
    return result


def report_statistics(state, dt):
    result = _base(state, dt); p, n = state["parameters"], state["samples"]
    ingested = state["last_tick"] >= 0
    counters = {k: state[k] if ingested else None for k in
                ("total_reports", "correct_reports", "attributed_reports", "switches", "comparisons")}
    result.update(report_ingestion_observed=ingested,
        last_ingestion_tick=min(state["last_tick"], p["end_tick"] - 1) if ingested else None,
        model_report_counters=counters,
        attributed_identity_switch_fraction=state["switches"] / state["comparisons"] if state["comparisons"] else None,
        processed_report_correct_fraction=state["correct_reports"] / state["total_reports"] if state["total_reports"] else None,
        tracks={track: {"covered_sample_ticks": h["covered_ticks"] if n else None,
                        "covered_sample_seconds": h["covered_ticks"] * dt if n else None,
                        "covered_fraction": h["covered_ticks"] / n if n else None,
                        "native_normalized_freshness_sum": h["freshness_sum"] if n else None,
                        "last_attributed_report": deepcopy(h["latest"]),
                        "last_identity_target_referee_only": h["identity_target"],
                        "last_identity_order": deepcopy(h["identity_tick"])} for track, h in state["tracks"].items()},
        definitions={
            "counter_scope": "Existing model ingestion before end_tick, including history before scoring start; counters are not limited to coverage-window samples",
            "total_reports": "Original model counter: malformed bodies count delivered attempts; well-formed physical samples use the model's deduplication, not a raw network packet count",
            "switches": "Original global identity-switch counter and actual comparison denominator; endpoint identity alone cannot reveal multiple switches within one tick",
            "switch_fraction": "Undefined without comparisons even when native score uses max(1, comparisons) to produce zero",
            "age": "Covered-sample measurement ages are reconstructed from complete state history, not inverted from rounded normalized freshness"})
    return result


def temporal_statistics(states, family, dt):
    if not states or [s["last_tick"] for s in states] != [-1, *range(1, states[-1]["last_tick"] + 1)]:
        raise ValueError("complete initial and contiguous native state history required")
    p = states[0]["parameters"]; _base(states[-1], dt)
    if any(s["parameters"] != p for s in states):
        raise ValueError("metric parameters changed")
    if family == "tracking":
        changes, credits = [], []
        gaps = {t: [] for t in states[0]["targets"]}; open_gap = {}
    elif family == "reports":
        ages = {t: {"count": 0, "age_sum": 0, "maximum_age": None, "freshness_sum": 0.} for t in states[0]["tracks"]}
    else:
        raise ValueError("unknown tracking metric family")
    for previous, current in zip(states, states[1:]):
        tick = current["last_tick"]; sampled = p["start_tick"] <= tick < p["end_tick"]
        if current["samples"] - previous["samples"] != int(sampled):
            raise ValueError("native sample progression differs from declared window")
        if family == "tracking" and sampled:
            for target, now in current["targets"].items():
                old = previous["targets"][target]
                if now["gap_ticks"]:
                    if not old["gap_ticks"]: open_gap[target] = tick
                elif old["gap_ticks"]:
                    gaps[target].append({"start_tick": open_gap.pop(target), "end_tick_inclusive": tick - 1,
                        "gap_ticks": old["gap_ticks"], "gap_seconds": old["gap_ticks"] * dt,
                        "qualifying_contact_return_tick": tick, "censored_at_last_sample": False})
                delta = {edge: now["handover_counts"].get(edge, 0) - old["handover_counts"].get(edge, 0)
                         for edge in set(now["handover_counts"]) | set(old["handover_counts"])}
                if any(v < 0 for v in delta.values()) or sum(delta.values()) not in (0, 1):
                    raise ValueError("observer-group transition counter is inconsistent")
                if len(now["handover_gaps"]) - len(old["handover_gaps"]) != sum(delta.values()):
                    raise ValueError("group-change gaps and counts differ")
                if sum(delta.values()):
                    changes.append({"target_referee_id": target, "scoring_tick": tick,
                        "from_group": old["owner_group"], "to_group": now["owner_group"],
                        "gap_ticks": now["handover_gaps"][-1], "gap_seconds": now["handover_gaps"][-1] * dt})
            for event, window in current["event_windows"].items():
                prior = previous["event_windows"].get(event, {}).get("reacquired", {})
                for target, delay in window["reacquired"].items():
                    if target not in prior:
                        if window["start_tick"] + delay != tick:
                            raise ValueError("event-contact credit clock differs")
                        gap = previous["targets"][target]["gap_ticks"] if previous["samples"] else None
                        credits.append({"event_id": event, "target_referee_id": target, "scoring_tick": tick,
                            "event_to_qualifying_contact_ticks": delay, "gap_samples_immediately_before_credit": gap,
                            "prior_gap_observed": gap > 0 if gap is not None else None})
        elif family == "reports":
            for track, now in current["tracks"].items():
                old = previous["tracks"][track]; increment = now["covered_ticks"] - old["covered_ticks"]
                if increment not in (0, 1) or (increment and not sampled):
                    raise ValueError("delivered coverage progression is inconsistent")
                row = ages[track]
                if increment:
                    age = tick - now["latest"]["observed_tick"]
                    if not 0 <= age <= p["maximum_age_ticks"]:
                        raise ValueError("covered measurement age is outside the native limit")
                    row["count"] += 1; row["age_sum"] += age
                    row["maximum_age"] = age if row["maximum_age"] is None else max(row["maximum_age"], age)
                    row["freshness_sum"] += 1. - age / (p["maximum_age_ticks"] + 1)
                if row["count"] != now["covered_ticks"] or row["freshness_sum"] != now["freshness_sum"]:
                    raise ValueError("raw covered ages do not reproduce native freshness accumulation")
    last = states[-1]
    if family == "reports":
        return {"covered_sample_measurement_age": {track: {"sample_count": v["count"],
            "age_sum_ticks": v["age_sum"] if v["count"] else None,
            "mean_age_ticks": v["age_sum"] / v["count"] if v["count"] else None,
            "mean_age_seconds": v["age_sum"] * dt / v["count"] if v["count"] else None,
            "maximum_age_ticks": v["maximum_age"]} for track, v in ages.items()},
            "all_native_coverage_and_freshness_accumulators_reproduced": True}
    for target, start in open_gap.items():
        h = last["targets"][target]
        gaps[target].append({"start_tick": start, "end_tick_inclusive": min(last["last_tick"], p["end_tick"] - 1),
            "gap_ticks": h["gap_ticks"], "gap_seconds": h["gap_ticks"] * dt,
            "qualifying_contact_return_tick": None, "censored_at_last_sample": True})
    for target, episodes in gaps.items():
        h = last["targets"][target]
        if sum(e["gap_ticks"] for e in episodes) != last["samples"] - h["seen_ticks"] or max((e["gap_ticks"] for e in episodes), default=0) != h["longest_gap_ticks"]:
            raise ValueError("gap episodes do not reproduce native gap counters")
    return {"gap_episodes": gaps, "credited_observer_group_changes": changes,
            "event_contact_credits": credits, "all_native_gap_counters_reproduced": True}
