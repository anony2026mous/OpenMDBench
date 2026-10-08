"""Read-only referee attribution of native protected-target hull health loss.

Never passed to agents, registered as an engine model, or used to change a
native score/terminal. Simultaneous mixed-source damage has bounds, not invented
per-attacker health shares. Component-only harm and classification errors are
outside this metric; a damage intent alone does not prove actual hull damage.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

from openmdbench.combat.damage_v2 import DamageApplyReceiptV2

CONTRACT = "protected-hull-harm-attribution@1.0"


def _cohort(values, name, *, allow_empty=False):
    if isinstance(values, str):
        raise ValueError(f"invalid {name} cohort")
    values = tuple(values)
    if (not allow_empty and not values) or any(not isinstance(x, str) or not x for x in values):
        raise ValueError(f"invalid {name} cohort")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {name} cohort")
    return frozenset(values)


class ProtectedHarmAudit:
    def __init__(self, defender_ids, protected_ids):
        self.defenders = _cohort(defender_ids, "defender")
        self.protected = _cohort(protected_ids, "protected", allow_empty=True)
        if self.defenders & self.protected:
            raise ValueError("defender and protected cohorts overlap")
        self.next_tick = 0
        self.intent_ids = set()
        self.rows = []
        self.receipt_chain_sha256 = hashlib.sha256(b"").hexdigest()
        self.evidence_basis = "supplied_damage_receipts_only"
        self.ledger_sha256 = None

    @classmethod
    def from_package(cls, package, defender_ids):
        cohorts = [m["plugin_parameters"]["protected_entities"]
                   for m in package["scenario"]["scoring"]["metrics"]
                   if "protected_entities" in m.get("plugin_parameters", {})]
        if not cohorts or any(c != cohorts[0] for c in cohorts[1:]):
            raise ValueError("missing or inconsistent native protected cohorts")
        return cls(defender_ids, [v["entity_id"] for v in cohorts[0]])

    def consume(self, start_tick, receipts):
        """Consume every native damage receipt for one completed single-tick step."""
        if type(start_tick) is not int or start_tick != self.next_tick:
            raise ValueError("damage audit requires contiguous ticks from zero")
        receipts = tuple(receipts)
        if not receipts:
            raise ValueError("missing native damage receipt, not evidence of zero harm")
        staged_rows, staged_ids, raw_receipts = [], set(), []
        for raw in receipts:
            value = raw.model_dump(mode="json") if hasattr(raw, "model_dump") else raw
            receipt = DamageApplyReceiptV2.model_validate(value)
            if receipt.tick != start_tick:
                raise ValueError("damage receipt clock differs from step")
            intents = {}
            for intent in receipt.applied_intents:
                if intent.tick != start_tick:
                    raise ValueError("damage intent clock differs from receipt")
                if intent.intent_id in self.intent_ids | staged_ids:
                    raise ValueError("duplicate native damage intent")
                staged_ids.add(intent.intent_id)
                intents[intent.intent_id] = intent
            used_ids, result_targets = set(), set()
            for result in receipt.results:
                if result.tick != start_tick or result.target_entity_id in result_targets:
                    raise ValueError("duplicate target result or wrong result clock")
                result_targets.add(result.target_entity_id)
                ids = result.applied_intent_ids
                if len(set(ids)) != len(ids) or set(ids) & used_ids or not set(ids) <= intents.keys():
                    raise ValueError("damage result has missing or duplicate intent evidence")
                linked = [intents[i] for i in ids]
                if any(i.target_entity_id != result.target_entity_id for i in linked):
                    raise ValueError("damage intent and result target differ")
                used_ids.update(ids)
                if result.health_after > result.health_before:
                    raise ValueError("damage result cannot be interpreted as healing")
                if result.target_entity_id not in self.protected:
                    continue
                kinds = {"defender_weapon" if i.source_kind == "weapon" and i.source_entity_id in self.defenders
                         else i.source_kind or "unknown" for i in linked}
                loss = result.health_before - result.health_after
                if not loss:
                    attribution = "no_hull_loss"
                elif kinds == {"defender_weapon"}:
                    attribution = "defender_weapon_exclusive"
                elif "defender_weapon" in kinds:
                    attribution = "mixed_with_defender_weapon"
                elif "unknown" in kinds:
                    attribution = "unknown_source_kind"
                else:
                    attribution = "other_known_source"
                staged_rows.append({"tick": start_tick, "target_id": result.target_entity_id,
                    "intent_ids": list(ids), "sources": [{"entity_id": i.source_entity_id,
                        "kind": i.source_kind} for i in linked],
                    "health_before": result.health_before, "health_after": result.health_after,
                    "actual_hull_health_loss": loss, "attribution": attribution})
            if used_ids != intents.keys():
                raise ValueError("applied damage intents lack native result evidence")
            raw_receipts.append(receipt.model_dump(mode="json"))
        evidence = json.dumps({"previous": self.receipt_chain_sha256, "tick": start_tick,
                               "receipts": raw_receipts}, sort_keys=True, allow_nan=False)
        self.receipt_chain_sha256 = hashlib.sha256(evidence.encode()).hexdigest()
        self.rows.extend(staged_rows)
        self.intent_ids.update(staged_ids)
        self.next_tick += 1
        return raw_receipts

    def consume_checkpoint_ledger(self, ledger, completed_steps):
        """Read complete damage transactions, including immediate weapon damage.

        WorldTickReceipt.damage_receipts alone omits the transaction applied
        inside CombatSystemV2.execute_batch. The existing public World checkpoint
        preserves those actual receipts; no engine interception is needed.
        """
        if self.next_tick or type(completed_steps) is not int or completed_steps < 0:
            raise ValueError("complete ledger requires a fresh audit and valid step count")
        groups = {tick: [] for tick in range(completed_steps)}
        operations = set()
        for item in ledger:
            operation = item["operation_id"]
            if not isinstance(operation, str) or not operation or operation in operations:
                raise ValueError("missing or duplicate damage transaction operation")
            if not isinstance(item.get("fingerprint"), str) or not item["fingerprint"]:
                raise ValueError("missing native transaction fingerprint")
            operations.add(operation)
            receipt = DamageApplyReceiptV2.model_validate(item["receipt"])
            if receipt.tick not in groups:
                raise ValueError("damage ledger receipt outside completed steps")
            groups[receipt.tick].append((operation, receipt))
        staged = ProtectedHarmAudit(self.defenders, self.protected)
        for tick, rows in groups.items():
            staged.consume(tick, [receipt for _, receipt in sorted(rows)])
        staged.evidence_basis = "readonly_world_checkpoint_complete_combat_ledger"
        staged.ledger_sha256 = hashlib.sha256(json.dumps(ledger, sort_keys=True, allow_nan=False).encode()).hexdigest()
        self.__dict__.update(staged.__dict__)

    def summary(self):
        certain = [r for r in self.rows if r["attribution"] == "defender_weapon_exclusive"]
        ambiguous = [r for r in self.rows if r["attribution"] in
                     {"mixed_with_defender_weapon", "unknown_source_kind"}]
        lower_ids = {r["target_id"] for r in certain}
        upper_ids = lower_ids | {r["target_id"] for r in ambiguous}
        harmed_ids = {r["target_id"] for r in self.rows if r["actual_hull_health_loss"] > 0}
        lower_loss = sum(r["actual_hull_health_loss"] for r in certain)
        upper_loss = lower_loss + sum(r["actual_hull_health_loss"] for r in ambiguous)
        count = len(self.protected)
        lower_rate = len(lower_ids) / count if count and self.next_tick else None
        upper_rate = len(upper_ids) / count if count and self.next_tick else None
        return {"contract": CONTRACT, "scope": "referee_only_supplement_not_native_score",
            "evidence_basis": self.evidence_basis, "ledger_sha256": self.ledger_sha256,
            "data_status": "observed_prefix" if self.next_tick else "not_observed",
            "checked_steps": self.next_tick, "protected_population": count,
            "defender_ids": sorted(self.defenders), "protected_ids": sorted(self.protected),
            "all_cause_harmed_ids": sorted(harmed_ids),
            "defender_weapon_harmed_ids_lower": sorted(lower_ids),
            "defender_weapon_harmed_ids_upper": sorted(upper_ids),
            "defender_weapon_harm_rate": lower_rate if lower_rate == upper_rate else None,
            "defender_weapon_harm_rate_bounds": [lower_rate, upper_rate],
            "all_cause_hull_health_loss": sum(r["actual_hull_health_loss"] for r in self.rows),
            "defender_weapon_hull_health_loss": lower_loss if lower_loss == upper_loss else None,
            "defender_weapon_hull_health_loss_bounds": [lower_loss, upper_loss],
            "attribution_counts": dict(sorted(Counter(r["attribution"] for r in self.rows).items())),
            "component_only_harm_covered": False, "classification_error_covered": False,
            "native_score_or_terminal_modified": False,
            "receipt_chain_sha256": self.receipt_chain_sha256, "evidence": list(self.rows)}

    def consume_verified_noncombat_tail(self, start_tick, receipts, combat_receipts):
        """Extend a complete checkpoint by one step with no immediate execution.

        Executed weapon batches can apply unreported instantaneous damage, so
        even one such batch makes this evidence path inadmissible. Delayed
        impacts and event damage are in the native step damage receipt.
        """
        if self.evidence_basis != "readonly_world_checkpoint_complete_combat_ledger":
            raise ValueError("tail requires a complete native checkpoint prefix")
        for item in combat_receipts:
            status = item.get("status") if isinstance(item, dict) else item.status
            execution = item.get("execution") if isinstance(item, dict) else item.execution
            if status != "rejected" or execution is not None:
                raise ValueError("tail has possible immediate combat damage without complete ledger")
        self.consume(start_tick, receipts)
        self.evidence_basis = "complete_checkpoint_prefix_plus_verified_noncombat_tail"
