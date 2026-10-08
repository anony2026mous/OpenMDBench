# g1-fault-dose — anchored critical-fault validation (appendix I.4)

The batch behind appendix I.4: known synthetic faults injected at defined boundaries of a
rule-planner + heuristic-GOAI-executor stack, with replay gates and boundary
localisation. 1,556 files, 94 MB.

The appendix describes this as "calibration, not blind natural-fault attribution", and
that is exactly what the structure shows: every injected run has a matched clean run on
the same seed, so the fault's cost is measurable by pairing.

## Layout

| Directory | Files | What it holds |
|---|---|---|
| `complex/` | 552 | 10 seeds × 3 conditions; injections at 5 dose levels each |
| `full/` | 554 | same design on a second (harder) configuration |
| `opps/` | 150 | dose sweep at 0.05/0.10/0.20/0.40/0.60 for seeds 561/563/565 |
| `probe/` | 60 | boundary-localisation probes: `c`/`e`/`m` × seed × dose 0.0/0.40/0.95 |
| `replaygate/` | 21 | the matched-prefix / integrity replay gate, injected vs replay pairs |
| `pilot/` | 143 | 2-seed pilot incl. a 12-episode `counterfactual` set |
| `smoke/` | 26 | sanity runs (`clean_s999`, `planner_d60_replay`, …) |
| `complex-baseline/` | 50 | the clean baseline for `complex` |

### The three conditions

| Condition | Meaning |
|---|---|
| `clean` | no injection — the paired reference |
| `planner_wrong_contact` | **planner-side** fault: the planner is given a wrong contact |
| `action_hold` | **executor-side** fault: the executor's action is held |

Injection strength is the `dose-N.NN` directory level (0.05 / 0.10 / 0.20 / 0.40 / 0.60).

### Provenance carried per episode

Each `episode.json` records `V`, `metrics`, `config`, `design`, `fault_injection`,
`source_hashes`, `instrumentation_sha256`, `trace_sha256`, `requests_sha256`,
`step_fingerprints`, `decisions`, and a `replay_check` with its `replay_source` — so an
injected run can be tied to the exact code and to the run it replays.

The batch manifest records the intended design explicitly:

```json
"design": {"planner": "rule", "executor": "heuristic", "difficulty": "..."}
"base_snapshot": "snapshots/20261002T194101Z-e5219dce/openmd"
```

That matches the paper's description of the base as "rule+heuristic-GOAI".

**Schema note:** this batch uses the *grid* schema (`V` + `metrics.blue_score` +
`metrics.mission_success`), **not** the high-fidelity `strategy_scorecard.defender_score`
used by `data/grid_withheld_5seeds/`. Reading the wrong key yields zero scores with no
error — a silent trap worth knowing before writing analysis against this tree.

## Verification status: partially reproduced — read this before using the numbers

`reproduce/verify_g1_fault.py` recomputes the injection cost at every dose level. The
result does **not** land on the figures appendix I.4 prints:

| I.4 states | Closest in this batch |
|---|---|
| planner-side injection costs **0.567** | max 0.110 (dose 0.40, `complex`) |
| executor-side injection costs **0.327** | 0.230 (dose 0.60, `complex`) |
| 0.7 / 0.4 success deltas, 0.7 / 0.4 extra breaches | per-dose success deltas are −0.20…+0.30 |
| "20/20 paired seeds" localisation | the batch has **10** seeds (561–570) |

What *does* hold:

* the seed range is exactly 561–570, as the appendix says;
* the clean baseline is identical in `complex/clean` and `complex-baseline/clean`
  (same `V` and same `trace_sha256` per seed), so the baseline is unambiguous;
* both injection types degrade the score at the strongest doses, and `action_hold` at
  dose 0.60 is the clearest single effect (success 0.30 → 0.00);
* `replaygate/` exists and carries injected/replay pairs, i.e. the matched-prefix gate is
  part of the batch.

So the experiment is the right one and is present in full, but the **published figures
are not reproducible from it as it stands**. The most likely explanations, in order:

1. I.4's numbers may be aggregated over dose in a way the appendix does not state (a
   single "planner-side injection" figure with five dose levels present in the data needs
   a stated pooling rule).
2. "20/20 paired seeds" does not match a 10-seed batch, so part of the appendix text may
   describe a larger run than this directory.
3. The specific success/breach deltas may come from a different metric key than the ones
   this script probes.

This is recorded rather than smoothed over: the data is now in the repository, so a
reader can re-derive whatever aggregation they prefer, and the discrepancy is stated here
so nobody assumes the file settles the question.
