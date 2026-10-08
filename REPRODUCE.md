# REPRODUCE.md — rebuilding every number in the paper

Two classes of claim appear in the paper, and they reproduce differently:

* **The high-fidelity suite table** (`tab_hifi_main`, 14 scenarios × 5 stacks) is fully
  recomputable **from this repository**, because the per-episode reports are committed.
  Verified: 70/70 cells exact.
* **The grid tables** (appendix `tab_p1_seedgrid`, `tab_p2_seedgrid`, `tab_p3a_seedgrid`)
  come from a separate campaign whose raw traces are listed in
  `data/EXTERNAL_DATA_MANIFEST.json`.

---

## 0. Environment

```bash
python --version        # 3.11
pip install numpy PyYAML
```

```bash
export PYTHONPATH="$PWD/code/analysis:$PWD/code/engine"
# PowerShell: $env:PYTHONPATH = "$PWD\code\analysis;$PWD\code\engine"
```

---

## 1. The main table (fully reproducible here)

```bash
python reproduce/verify_paper_table.py
```

Expected output ends with:

```
  scenarios matched : 14
  exact 70   rounding 0   DIFFERS 0   of 70 cells
```

The script prints its own verdict, shown above. It locates the episodes and the baselines
through `reproduce/_w1_common.py`, which resolves paths relative to the repository, so it
works from any checkout location.

### The four traps it encodes

Each of these produced a real wrong answer during preparation, so they are documented
rather than hidden:

1. **Public metric convention.** `defender_score` is *already* normalised over
   applicable layers. Dividing it by `scored_weight` again inflates it (0.90 renders as
   1.00). Use the column as-is and cross-check against `layer_*` × `applicable_*`.
2. **Seed scope differs by arm.** The LLM arms are the five campaign seeds (7/11/13/17/
   19). The baselines are **not** seed-restricted — they come from the frozen archive and
   the caption says so. Restricting `rule-rule` to the campaign seeds gives IE-01 = 0.686,
   whereas the paper prints 0.691, which is the mean over all 42 archived rule episodes.
   Getting this backwards is a silent 0.005 error on every baseline cell.
3. **A partial sixth seed is on disk.** Seed 23 has only 3 finished cells. Including them
   moves `IE-04 / LLM+Rule` from 0.710 to 0.741 — a 0.031 error on a cell the paper
   reports to three decimals. `PAPER_SEEDS` exists to prevent exactly that.
4. **Row labels are spelled inconsistently.** Some rows read `IE-05 multi-axis`, others
   `IE-01 single target`, and the last row is abbreviated to `IE-14 saturation` for
   `IE-14-SATURATION-THREE-WAVE`. Labels are normalised and one alias is declared.

### The `Overall` row uses scenario means, not pooled episodes

The `Overall` row is **the mean and sample SD over the 14 scenario means**. Pooling all
episodes gives a visibly different SD:

| Arm | scenario-mean convention (paper) | pooled-episode convention |
|---|---|---|
| Rule | 0.723 ± 0.098 | 0.704 ± 0.219 |
| RL | 0.632 ± 0.203 | 0.655 ± 0.214 |

```bash
python - <<'PY'
import statistics as st
import _w1_common as c
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)
for arm in ("rule-rule", "rl"):
    per = [st.mean(c.vals(base, sc, arm)) for sc in c.IE if c.vals(base, sc, arm)]
    print(arm, f"{st.mean(per):.3f} +/- {st.stdev(per):.3f}", "n_scen=", len(per))
PY
```

---

## 2. The consolidated dataset

```bash
python reproduce/build_dataset.py     # writes DATASET_5SEEDS.{csv,json,md}
```

This one rewrites the committed copies, so run it only if you intend to regenerate them;
it reads the authoring checkout's episode directory rather than the release copy. Rows are
admitted only if the report is a real episode: `ticks_run > 0`, a decided terminal
outcome, not `aborted`, and a scorecard that reproduces from its own layer breakdown.
Rejected runs are counted and reported, never silently dropped.

---

## 3. The no-intelligence ablation table (`tab_hifi_nointel`)

This contrasts the same three LLM stacks under two口径:

| Regime | Flag | Meaning |
|---|---|---|
| no intelligence (main) | `--llm-briefing withheld` | prompt carries **no** enemy information |
| legacy intelligence | `--llm-briefing declared` | per-wave `spawn_tick / count / axis / behavior`, including future ground truth |

```bash
cd code/analysis
python _w1_declared_vs_withheld.py
```

The口径 of any episode is recorded **in the report**, and it lives in two different places
depending on the arm — reading only one silently reports "no provenance" for correctly
tagged episodes:

| Arm | Field |
|---|---|
| `pure-llm` | `defender.briefing` |
| `llm-rule`, `llm-rl` | `defender.planner.briefing` |

---

## 4. Running new simulations

The engine is declarative: scenarios are packages under `code/engine/scenarios/formal/`,
compiled by `ScenarioCompiler`; adding one needs no kernel Python changes.

```bash
cd code/analysis

# one episode
python run_episode.py \
  --scenario IE-01-SINGLE-TARGET --planner llm --seed 7 \
  --max-ticks 1800 --llm-briefing withheld \
  --output /tmp/ep.json --log /tmp/ep.jsonl

# the whole 3-arm x 14-scenario grid at one seed
python _w1_grid_driver.py --tag n3 --seeds 7 --jobs 6
```

**Watch the proxy.** If `ALL_PROXY` / `HTTP_PROXY` / `HTTPS_PROXY` are set and the LLM
endpoint is not in `NO_PROXY`, every episode dies at tick 0 with `ProxyError`. This
silently wasted a whole 84-episode batch during the campaign; clear them first:

```powershell
foreach ($v in 'ALL_PROXY','HTTP_PROXY','HTTPS_PROXY','all_proxy','http_proxy','https_proxy') {
    Remove-Item "env:$v" -ErrorAction SilentlyContinue
}
```

Operational notes worth knowing before launching a batch:

* **Concurrency ceiling is 6** against one LLM endpoint. Nine concurrent episodes tripped
  `step_timeout` and produced aborted, worthless episodes.
* **`--resume` does not restore the planner.** It restores engine world state only, so a
  resumed episode is a *different trajectory*, not a continuation. The campaign re-ran
  rather than resumed, and this release contains no resumed episodes.
* **Wall time is dominated by LLM wait**: measured 15–45 min per episode for LLM arms
  versus seconds for rule-only arms.

---

## 5. Fairness and boundary audits

These are the checks that make the comparison defensible; each is a script.

| Question | Script | What it proves |
|---|---|---|
| Does the withheld prompt leak scenario-declared intelligence? | `_w1_p0_fairness_accept.py` | withheld: 0 sensitive-string hits; declared: reproduces the old reading |
| Did the shared-code edits move the baseline? | `_w1_determinism_gate.py <SCEN> rule 7 --ab` | pre-change code vs live code, 22 fields, 0 differences, 6 scenarios |
| Is the metric what we think it is? | `_w1_scoring_convention_audit.py` | recomputes every score from layers × weights × applicability |
| Can an arm end its own measurement early? | `_w1_terminal_structure.py` | success needs total neutralisation or the declared tick; the intruder-side rule counts `scheduled` waves, so it cannot fire before the last wave spawns |
| Is the baseline one policy or a mixture? | `_w1_baseline_partition.py` | the archived `rl` set mixes five checkpoints; the analysis pins one |

`data/grid_withheld_5seeds/WITHHELD_BRIEFING_EVIDENCE.md` collects the results into one
auditable ledger.

---

## 6. Rebuilding this bundle

The build copies the source trees, applies a deny-list (credentials, caches, `artifacts/`,
checkpoints, stray run logs), rewrites co-author-absolute paths, emits `README.md`,
`REPRODUCE.md` and `data/PENDING.md` from `release_assets/`, prints a copy summary
listing every exclusion, and records pinned hashes in `PROVENANCE.json`.

```bash
python reproduce/build_release.py --dest /path/to/OpenMDBench-Release
python reproduce/scan_for_secrets.py      # then confirm the scan is clean
```

Note: the scan reports two permanent false positives — an `AKIA` byte sequence inside a
base64 PNG embedded in `fig1_narrative_zhang.svg`, and the OpenSSH key header that
`scan_for_secrets.py` itself contains as a detection pattern.
