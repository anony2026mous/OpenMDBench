"""Candidate control: reconcile launch reservations with own execution receipts.

Queued is not executed. Rejected/cancelled requests do not consume ammunition
or create an in-flight assessment wait. This adapter passes only statuses for
IDs actually submitted by that controller, never opponent or missile state.
"""
from copy import deepcopy

from .approach_screen_policy import ApproachScreenPolicy
from .salvo_guard_policy import SalvoGuardPolicy


FEEDBACK_PROTOCOL = "own-fire-execution-status@1.0"


def own_fire_feedback(native_receipts, submitted_ids):
    allowed = frozenset(submitted_ids)
    fields = ("request_id", "status", "tick", "error_code")
    return [{key: row.get(key) for key in fields} for row in native_receipts
            if row.get("kind") == "discrete" and row.get("child_id") in allowed
            and row.get("request_id") == row["child_id"]
            and row.get("status") in {"executed", "rejected", "cancelled"}]


class ReceiptAwareSalvoPolicy(SalvoGuardPolicy):
    def __init__(self, brief, defender_id):
        super().__init__(brief, defender_id)
        self.reservation = None
        self.settled_receipts = {}
        self.feedback = []

    def action(self, observation):
        if self.reservation is not None:
            return None  # An absent result is not permission to refund or fire again.
        before = {"attempts": self.attempts, "last_attempt_tick": self.last_attempt_tick,
                  "pending_until": deepcopy(self.pending_until)}
        result = super().action(observation)
        if result is not None:
            self.reservation = {"before": before, "request_id": None,
                                "tick": observation["tick"], "contact_id": result["contact_id"]}
        return result

    def bind_fire_request(self, request_id):
        if (self.reservation is None or self.reservation["request_id"] is not None
                or not isinstance(request_id, str) or not request_id or request_id in self.settled_receipts):
            raise ValueError("fire request must bind exactly one new reservation")
        self.reservation["request_id"] = request_id

    def process_fire_feedback(self, receipt):
        if set(receipt) != {"request_id", "status", "tick", "error_code"}:
            raise ValueError("only own execution-status fields are admissible")
        request_id = receipt["request_id"]
        if request_id in self.settled_receipts:
            if receipt != self.settled_receipts[request_id]:
                raise ValueError("conflicting execution receipt")
            return False
        if self.reservation is None or request_id != self.reservation["request_id"]:
            return False
        if (receipt["status"] not in {"executed", "rejected", "cancelled"}
                or type(receipt["tick"]) is not int or receipt["tick"] < self.reservation["tick"]):
            raise ValueError("invalid own execution status or tick")
        refunded = receipt["status"] in {"rejected", "cancelled"}
        if refunded:
            before = self.reservation["before"]
            self.attempts, self.last_attempt_tick = before["attempts"], before["last_attempt_tick"]
            self.pending_until = before["pending_until"]
        self.settled_receipts[request_id] = deepcopy(receipt)
        self.feedback.append({**deepcopy(receipt), "contact_id": self.reservation["contact_id"],
                              "reservation_released": refunded, "counted_launches": self.attempts})
        self.reservation = None
        return True


class ReceiptAwareScreenPolicy(ApproachScreenPolicy):
    def __init__(self, brief, defender_id, mode="receipt-aware-salvo"):
        if mode != "receipt-aware-salvo":
            raise ValueError("receipt-aware control requires its declared mode")
        super().__init__(brief, defender_id)
        self.weapon = ReceiptAwareSalvoPolicy(brief, defender_id)

    def bind_fire_request(self, request_id):
        self.weapon.bind_fire_request(request_id)

    def process_fire_feedback(self, receipt):
        return self.weapon.process_fire_feedback(receipt)

    @property
    def decisions(self):
        return {**super().decisions, "own_fire_feedback": self.weapon.feedback}
