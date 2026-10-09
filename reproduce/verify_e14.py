"""Verify the E14 baseline-strength diagnostic (appendix "Baseline-strength diagnostic").

The paper's claim, in full:

  Because the complex tier's pure-MAPPO success rate is 0%, we ran a frozen-scenario
  diagnostic re-training audit (12 configurations x 3 training seeds, continuous mode,
  8 envs, 4096 steps/rollout, goal-injection probability 0.5; inference by the
  deterministic actor without goals; seed-bootstrap 95% CIs, 3 independent training
  seeds, 20k resamples): doubled training length (10M steps), medium-weight curriculum
  (weight init only, optimizer/reset-normalizer reinitialized), and two hyperparameter
  sweeps (halved LR; doubled LR with doubled entropy). All best and final confirmation
  success rates remain 0% across all 12 configurations. Critically, a frozen medium-tier
  checkpoint transfers directly to complex at 50% pre-check success (5/10) yet collapses
  to 0% after on-complex fine-tuning.

Every element is checked against
`data/collaborator_runs/E14_Grid_complex-baseline_p01_20261003/`.

Note this is an experiment that WAS executed -- it is easy to assume otherwise because
its results are all 0%.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E14 = ROOT / "data" / "collaborator_runs" / "E14_Grid_complex-baseline_p01_20261003"

print("=" * 96)
print("appendix E14 (baseline-strength diagnostic)  vs  the E14 batch")
print("=" * 96)
if not E14.is_dir():
    print(f"  batch not present: {E14}")
    raise SystemExit(0)

bad = 0
def chk(label, got, want, tol=None):
    global bad
    if tol is None:
        ok = got == want
    else:
        ok = abs(got - want) <= tol
    bad += not ok
    print(f"  {'OK ' if ok else 'BAD'}  {label:<46} batch {str(got):<16} paper {want}")
    return ok


# ---- protocol
proto = json.loads((E14 / "manifest" / "protocol.json").read_text(encoding="utf-8"))
cfgs = proto.get("configurations") or {}
seeds = proto.get("training_seeds") or []
print(f"\n  --- manifest/protocol.json ---")
chk("configurations x training seeds = 12",
    len(cfgs) * len(seeds), 12)
chk("training seeds", len(seeds), 3)
chk("doubled-length config steps (10M)",
    cfgs.get("default_extended", {}).get("total_steps"), 10000000)
chk("other configs stay at 5M",
    sorted({v.get("total_steps") for k, v in cfgs.items() if k != "default_extended"}),
    [5000000])

# ---- the run table
csvp = E14 / "analysis" / "a01" / "diagnostic_runs_v1.csv"
rows = list(csv.DictReader(csvp.open(encoding="utf-8-sig")))
print(f"\n  --- analysis/a01/diagnostic_runs_v1.csv ({len(rows)} rows) ---")
chk("run rows", len(rows), 12)
chk("distinct configurations", len({r["configuration"] for r in rows}), 4)
allzero = all(float(r["final_confirmation_SR"]) == 0.0 for r in rows)
best = {float(r["best_confirmation_SR"]) for r in rows}
chk("every final confirmation SR is 0", allzero, True)
chk("every best confirmation SR is 0", best == {0.0}, True)

# ---- summary.json agrees and carries the bootstrap CI
summ = json.loads((E14 / "analysis" / "a01" / "summary.json").read_text(encoding="utf-8"))
cs = summ.get("configurations") or []
print(f"\n  --- analysis/a01/summary.json ---")
chk("configuration blocks", len(cs), 4)
chk("mean_confirm_SR all 0", {c.get("mean_confirm_SR") for c in cs}, {0.0})
chk("bootstrap ci95 all [0,0]",
    {tuple(c.get("training_seed_bootstrap_ci95") or []) for c in cs}, {(0.0, 0.0)})

# ---- the report, and the three claims that live only in prose
rep = (E14 / "reports" / "r01" / "E14最终诊断报告_v1.md").read_text(encoding="utf-8")
print(f"\n  --- reports/r01/E14最终诊断报告_v1.md ---")
for label, pat, want in (
        ("8 envs", r"8\s*环境|8 envs", True),
        ("4096 steps/rollout", r"4096\s*步|4096 steps", True),
        ("goal-injection probability 0.5", r"概率\s*0\.5|probability 0\.5", True),
        ("medium transfer 50% (5/10)", r"50%[（(]\s*5\s*/\s*10\s*[）)]", True),
        ("medium checkpoint is a checkpoint (not a new run)",
         r"medium checkpoint|medium.{0,6}checkpoint", True),
        ("not task-unsolvability caveat", r"不是任务不可学习|not.{0,12}unlearnab", True)):
    ok = bool(re.search(pat, rep, re.I))
    bad += not ok
    print(f"  {'OK ' if ok else 'BAD'}  {label:<46} {'present' if ok else 'ABSENT'}")
print(f"  {'OK ' if '20,000' in rep or '20000' in rep else 'BAD'}  "
      f"{'20000-draw bootstrap':<46} "
      f"{'present' if ('20,000' in rep or '20000' in rep) else 'ABSENT'}")

# ---- the structural intervention must NOT have run
sc = str(proto.get("scenario_change", ""))
ok = "none" in sc.lower() and "defer" in sc.lower()
bad += not ok
print(f"  {'OK ' if ok else 'BAD'}  {'structural intervention deferred':<46} {sc[:52]}")

# ---- the un-shipped artefact
for rel in ("analysis/a00/medium_transfer_seed_uncertainty_v1.json", "raw/preflight"):
    present = (E14 / rel).exists()
    print(f"  {'--  ':<4} {rel:<46} {'present' if present else 'NOT SHIPPED'}"
          f"{'' if present else '   (the 50% claim ships only as prose)'}")

print(f"\n  E14 cells mismatching the paper: {bad}")
raise SystemExit(1 if bad else 0)
