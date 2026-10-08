"""Native-message tracking identity metrics; no alternate world or perception.

Public contact IDs are matched as opaque evidence IDs, never parsed. Position
error is deliberately absent: MissionEvaluationSnapshotV2 does not contain
measurement positions or truth positions. These metrics cannot certify it.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import math

MODEL_ID = "models.competition-track-report-metrics"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"
PROTOCOL = "track-report@1.0"
KINDS = {"delivered_coverage", "identity_accuracy", "identity_switch_rate", "delivered_freshness"}
BODY_FIELDS = {"schema_version", "track_id", "contact_id", "observed_tick", "reported_tick"}


def _plain(value):
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(_plain(value), sort_keys=True, allow_nan=False).encode()).hexdigest()


def valid_body(body):
    return (isinstance(body, dict) and set(body) == BODY_FIELDS
            and body.get("schema_version") == PROTOCOL
            and all(isinstance(body.get(k), str) and 0 < len(body[k]) <= 256 for k in ("track_id", "contact_id"))
            and all(type(body.get(k)) is int and body[k] >= 0 for k in ("observed_tick", "reported_tick")))


class TrackReportMetricV1:
    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        p = deepcopy(parameters)
        if isinstance(p.get("tracks"), (tuple, list)):
            p["tracks"] = [dict(r["values"]) if isinstance(r, dict) and set(r) == {"values"} else dict(r) for r in p["tracks"]]
        p["reporter_ids"] = list(p.get("reporter_ids", ()))
        fields = {"metric_id", "kind", "tracks", "reporter_ids", "recipient_entity_id",
                  "recipient_controller_slot", "start_tick", "end_tick", "maximum_age_ticks", "unit"}
        if set(p) != fields or p["kind"] not in KINDS or p["unit"] != "1":
            raise ValueError("explicit dimensionless track-report metric parameters required")
        for key in ("metric_id", "recipient_entity_id", "recipient_controller_slot"):
            if not isinstance(p[key], str) or not p[key]:
                raise ValueError("named metric and actual recipient endpoint required")
        if (not p["reporter_ids"] or any(not isinstance(i, str) or not i for i in p["reporter_ids"])
                or len(set(p["reporter_ids"])) != len(p["reporter_ids"])
                or p["recipient_entity_id"] in p["reporter_ids"]):
            raise ValueError("unique reporter identities separate from the recipient required")
        if not isinstance(p["tracks"], list) or not p["tracks"]:
            raise ValueError("declared public tracks and private referee bindings required")
        for t in p["tracks"]:
            if set(t) != {"track_id", "target_entity_id"} or any(not isinstance(v, str) or not v for v in t.values()):
                raise ValueError("invalid track binding")
        for key in ("track_id", "target_entity_id"):
            if len({t[key] for t in p["tracks"]}) != len(p["tracks"]):
                raise ValueError("track and target bindings must be one-to-one")
        if (any(type(p[k]) is not int or p[k] < 0 for k in ("start_tick", "end_tick", "maximum_age_ticks"))
                or p["start_tick"] < 1 or p["start_tick"] >= p["end_tick"] or p["maximum_age_ticks"] < 1):
            raise ValueError("valid score window and positive information-age bound required")
        self.parameters = p
        self.last_tick, self.last_input_hash, self.last_value = -1, None, None
        self.samples = self.total_reports = self.correct_reports = self.attributed_reports = 0
        self.switches = self.comparisons = 0
        self.fact_history, self.seen_messages, self.seen_reports = {}, {}, {}
        self.tracks = {t["track_id"]: {"covered_ticks": 0, "freshness_sum": 0., "latest": None,
                    "identity_tick": -1, "identity_target": None} for t in p["tracks"]}

    def _input(self, snapshot):
        facts = []
        for fact in snapshot.contact_facts:
            if fact.owner_entity_id in self.parameters["reporter_ids"]:
                facts.append({k: getattr(fact, k) for k in ("evidence_id", "owner_entity_id", "target_entity_id",
                    "observed_tick", "max_age_ticks", "confidence", "minimum_confidence")})
        messages = [_plain(m) for m in snapshot.communications
                    if m.get("sender_entity_id") in self.parameters["reporter_ids"]
                    and m.get("recipient_entity_id") == self.parameters["recipient_entity_id"]]
        return {"tick": snapshot.tick, "facts": sorted(facts, key=digest),
                "messages": sorted(messages, key=digest),
                "recipient_lifecycle": snapshot.entity_states.get(self.parameters["recipient_entity_id"], {}).get("lifecycle")}

    def _ingest_facts(self, facts, tick):
        for fact in facts:
            observed = fact["observed_tick"]
            if (type(observed) is not int or not 0 <= tick-observed <= fact["max_age_ticks"]
                    or fact["confidence"] < fact["minimum_confidence"]):
                continue
            key = json.dumps([fact["evidence_id"], fact["owner_entity_id"], observed])
            old = self.fact_history.get(key)
            if old is not None and old["target_entity_id"] != fact["target_entity_id"]:
                raise ValueError("conflicting authoritative contact identity")
            self.fact_history.setdefault(key, {"target_entity_id": fact["target_entity_id"],
                "observed_tick": observed, "first_available_tick": tick})

    def _deliveries(self, messages, tick):
        p = self.parameters
        deliveries = []
        for raw in messages:
            if (raw.get("transport_status") != "delivered"
                    or p["recipient_controller_slot"] not in raw.get("recipient_controller_slots", ())):
                continue
            generated, delivered, expiry = [raw.get(k) for k in ("generated_tick", "delivered_tick", "expiry_tick")]
            if (any(type(t) is not int for t in (generated, delivered, expiry))
                    or not 0 <= generated <= delivered <= min(expiry, tick)):
                continue
            try:
                body = json.loads(raw.get("payload", ""))
            except (ValueError, TypeError):
                continue
            if not isinstance(body, dict) or body.get("schema_version") != PROTOCOL:
                continue
            identifier = raw.get("message_id")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("native delivered report has no message identity")
            fingerprint = digest(raw)
            if identifier in self.seen_messages:
                if self.seen_messages[identifier] != fingerprint:
                    raise ValueError("conflicting native delivered message identity")
                continue
            self.seen_messages[identifier] = fingerprint
            deliveries.append((delivered, generated, raw["sender_entity_id"], identifier, body))
        return sorted(deliveries, key=lambda row: row[:4])

    def _accept_report(self, delivered, generated, sender, message_id, body):
        p = self.parameters
        if not valid_body(body):
            self.total_reports += 1
            return
        # Retrying the same physical sample cannot inflate accuracy or extend
        # its age. A new native message ID is not a new target measurement.
        key = json.dumps([sender, body["track_id"], body["contact_id"], body["observed_tick"]])
        if key in self.seen_reports:
            return
        self.seen_reports[key] = True
        self.total_reports += 1
        observed = body["observed_tick"]
        if (body["track_id"] not in self.tracks or body["reported_tick"] != generated
                or not 0 <= observed <= generated or delivered-observed > p["maximum_age_ticks"]):
            return
        evidence = self.fact_history.get(json.dumps([body["contact_id"], sender, observed]))
        if evidence is None or evidence["first_available_tick"] > generated:
            return
        target = evidence["target_entity_id"]
        expected = next(t["target_entity_id"] for t in p["tracks"] if t["track_id"] == body["track_id"])
        self.attributed_reports += 1
        self.correct_reports += int(target == expected)
        history = self.tracks[body["track_id"]]
        if observed >= history["identity_tick"]:
            if history["identity_target"] is not None:
                self.comparisons += 1
                self.switches += int(history["identity_target"] != target)
            history["identity_tick"], history["identity_target"] = observed, target
            history["latest"] = {"target_entity_id": target, "observed_tick": observed,
                "delivered_tick": delivered, "sender_entity_id": sender, "message_id": message_id}

    def evaluate(self, snapshot):
        p, tick = self.parameters, snapshot.tick
        if type(tick) is not int or tick < 0:
            raise ValueError("nonnegative integer authoritative tick required")
        data = self._input(snapshot)
        fingerprint = digest(data)
        if tick < self.last_tick:
            raise ValueError("track-report scoring cannot move backwards without restore")
        if tick == self.last_tick:
            if fingerprint != self.last_input_hash:
                raise ValueError("conflicting track-report evidence at the same tick")
            return {p["metric_id"]: self.last_value}
        if tick != self.last_tick+1 and not (self.last_tick == -1 and tick == 1):
            raise ValueError("every authoritative tick is required for report provenance")
        if tick < p["end_tick"]:
            self._ingest_facts(data["facts"], tick)
            for delivery in self._deliveries(data["messages"], tick):
                self._accept_report(*delivery)
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            for binding in p["tracks"]:
                history = self.tracks[binding["track_id"]]
                report = history["latest"]
                if (data["recipient_lifecycle"] in {"active", "degraded"} and report is not None
                        and report["target_entity_id"] == binding["target_entity_id"]
                        and 0 <= tick-report["observed_tick"] <= p["maximum_age_ticks"]):
                    history["covered_ticks"] += 1
                    history["freshness_sum"] += 1.-(tick-report["observed_tick"])/(p["maximum_age_ticks"]+1)
            if p["kind"] == "delivered_coverage":
                self.last_value = min(t["covered_ticks"] for t in self.tracks.values())/self.samples
            elif p["kind"] == "delivered_freshness":
                self.last_value = min(t["freshness_sum"] for t in self.tracks.values())/self.samples
            elif p["kind"] == "identity_accuracy":
                self.last_value = self.correct_reports/self.total_reports if self.total_reports else None
            else:
                self.last_value = self.switches/max(1, self.comparisons) if self.attributed_reports else None
        self.fact_history = {k: v for k, v in self.fact_history.items()
                             if tick-v["observed_tick"] <= p["maximum_age_ticks"]}
        self.last_tick, self.last_input_hash = tick, fingerprint
        return {p["metric_id"]: self.last_value}

    def snapshot(self):
        names = ("parameters", "last_tick", "last_input_hash", "last_value", "samples",
                 "total_reports", "correct_reports", "attributed_reports", "switches", "comparisons",
                 "fact_history", "seen_messages", "seen_reports", "tracks")
        return {"schema_version": "track-report-state@1.0", **deepcopy({k: getattr(self, k) for k in names})}

    def restore(self, state):
        if (not isinstance(state, dict) or set(state) != set(self.snapshot())
                or state["schema_version"] != "track-report-state@1.0" or state["parameters"] != self.parameters):
            raise ValueError("track-report checkpoint schema or parameters differ")
        digest(state)
        tick = state["last_tick"]
        if type(tick) is not int or tick < -1:
            raise ValueError("invalid checkpoint tick")
        expected = max(0, min(tick, self.parameters["end_tick"]-1)-self.parameters["start_tick"]+1)
        if type(state["samples"]) is not int or state["samples"] != expected:
            raise ValueError("checkpoint sample count differs from its score window")
        counts = ("total_reports", "correct_reports", "attributed_reports", "switches", "comparisons")
        if any(type(state[k]) is not int or state[k] < 0 for k in counts):
            raise ValueError("nonnegative integer report counters required")
        if not 0 <= state["correct_reports"] <= state["attributed_reports"] <= state["total_reports"] or not 0 <= state["switches"] <= state["comparisons"] <= state["attributed_reports"]:
            raise ValueError("inconsistent report counters")
        if set(state["tracks"]) != set(self.tracks):
            raise ValueError("checkpoint changes public track identities")
        for item in state["tracks"].values():
            if set(item) != {"covered_ticks", "freshness_sum", "latest", "identity_tick", "identity_target"}:
                raise ValueError("invalid track checkpoint schema")
            if (type(item["covered_ticks"]) is not int or not 0 <= item["covered_ticks"] <= expected
                    or not isinstance(item["freshness_sum"], (int, float))
                    or not 0 <= item["freshness_sum"] <= item["covered_ticks"]+1e-9):
                raise ValueError("invalid delivered-coverage history")
            latest = item["latest"]
            if latest is None:
                if item["identity_tick"] != -1 or item["identity_target"] is not None:
                    raise ValueError("identity state lacks a delivered report")
            elif (not isinstance(latest, dict) or set(latest) != {"target_entity_id", "observed_tick",
                    "delivered_tick", "sender_entity_id", "message_id"}
                    or latest["sender_entity_id"] not in self.parameters["reporter_ids"]
                    or any(type(latest[k]) is not int for k in ("observed_tick", "delivered_tick"))
                    or not 0 <= latest["observed_tick"] <= latest["delivered_tick"] <= tick
                    or item["identity_tick"] != latest["observed_tick"]
                    or item["identity_target"] != latest["target_entity_id"]):
                raise ValueError("invalid delivered identity state")
        for key, fact in state["fact_history"].items():
            identity = json.loads(key)
            if (not isinstance(identity, list) or len(identity) != 3
                    or identity[1] not in self.parameters["reporter_ids"]
                    or set(fact) != {"target_entity_id", "observed_tick", "first_available_tick"}
                    or type(fact["observed_tick"]) is not int or type(fact["first_available_tick"]) is not int
                    or identity[2] != fact["observed_tick"]
                    or not 0 <= fact["observed_tick"] <= fact["first_available_tick"] <= tick
                    or tick-fact["observed_tick"] > self.parameters["maximum_age_ticks"]):
                raise ValueError("invalid authoritative contact history")
        if state["last_value"] is not None and (type(state["last_value"]) not in (int, float) or not math.isfinite(state["last_value"]) or not 0 <= state["last_value"] <= 1):
            raise ValueError("invalid normalized checkpoint value")
        for key, value in state.items():
            if key != "schema_version":
                setattr(self, key, deepcopy(value))

    def close(self):
        pass
