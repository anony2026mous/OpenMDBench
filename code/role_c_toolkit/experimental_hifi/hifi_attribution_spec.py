"""Pre-registered injected-bottleneck arms from OpenMDBench0830 Table 3."""

PAPER_ATTRIBUTION_ARMS = (
    {"case": "planner_wrong_contact", "dose": 0.54,
     "expected_label": "planning", "component": "planner"},
    {"case": "executor_degradation", "dose": 0.10,
     "expected_label": "execution", "component": "executor"},
    {"case": "executor_degradation", "dose": 0.30,
     "expected_label": "execution", "component": "executor"},
    {"case": "executor_degradation", "dose": 0.50,
     "expected_label": "execution", "component": "executor"},
    {"case": "balanced_mild", "dose": 0.10,
     "expected_label": "balanced", "component": "planner+executor"},
)

PAPER_FAULT_CASES = ("planner_wrong_contact", "executor_degradation", "balanced_mild")
EXECUTOR_FAULT_CASES = ("action_hold", "executor_degradation", "balanced_mild")


def selected(seed: int, tick: int, unit: str, case: str, dose: float,
             component: str = "") -> bool:
    """Stable nested Bernoulli mask; component names decorrelate balanced arms."""
    import hashlib

    if not 0.0 <= dose <= 1.0:
        raise ValueError("Fault dose must be in [0,1]")
    suffix = f":{component}" if component else ""
    key = f"role-c-hifi-fault@1:{seed}:{tick}:{unit}:{case}{suffix}".encode("utf-8")
    threshold = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / 2 ** 64
    return threshold < dose
