# Where the paper's data comes from

Mined from the manuscript sources themselves (`main.tex`, `appendix.tex`), not inferred.
This answers "where does this number come from" with a citation to the paper's own words,
and it clears up a numbering collision that caused real confusion.

## 1. The paper uses two different numbering systems

This is the single most important thing to know before hunting for data:

| Notation | Means | Example |
|---|---|---|
| **P1 / P2 / P3** | the layering law's **three testable predictions** (§3.2), *not* batches | "P1--P2 on the grid's boundary regime, P3 on the gate-admitted high-fidelity suite" (main.tex 217) |
| **E1, E5, E14, P0-1** | **experiment codes**, written either as a section title or `\paragraph{... (Ex)}` | "High-Fidelity Headroom Calibration and Conditional Gains (E1)" (appendix K) |

So "P1" in the paper means *prediction 1*, while `P1__six_arm__s501-510` in the data is a
**batch name**. They are unrelated. Reading one as the other sends the search to the wrong
place.

There is also a third family: **DF / D2 / D3** are the pre-registered *gates*
(decision-form match, headroom, deployment deficit), not experiments.

## 2. The only batch the paper names outright

```
\texttt{P0\_GRID\_COMPLEX\_LAYERED\_20261006\_p01}   (appendix.tex 158)
```

with "20 completed formal episodes, protocol SHA256 `25115d36…0e4f4`". That batch is in
this repository and `tab:complexlayered` reproduces from it exactly (0/3 mismatch).

The only other filenames named in the text are `e1_2x2_option1.json` and
`e1_2x2_option2.json` — both shipped in `data/e5/`.

## 3. Provenance by table

Each row cites how the paper identifies its own source.

| Table / block | Paper's designation | Source as the paper states it | In this repo |
|---|---|---|---|
| `tab_hifi_main` | — (main §6) | "14 scenarios, five stacks … unified no-intelligence regime, five seeds per LLM stack" | `data/grid_withheld_5seeds/` — 70/70 |
| `tab:sixarm` | — (main §6) | "six-arm accounting batch (medium tier, 10 paired seeds)" | `e2-delivery-20261003/raw/P1__six_arm__s501-510__main__v1` — 0/6 |
| `tab_p1_seedgrid` | appendix I.1 | "(seeds 501--510)" | same batch — 0/60 cells |
| `tab_p2_seedgrid` + `tab:dosegain` + `figA3` | appendix I.2 | "Goal-dose batch (seeds 512--521) … four paired interface conditions (strong / mask1 / mask2 / hold)" | `e2-delivery-20261003/raw/P2__goal_dose__*` — 0/8 |
| `tab:complexlayered` | **P0-1** | "a frozen five-seed paired batch (seeds 63101--63105) … frozen scenario parameters" | `P0_GRID_COMPLEX_LAYERED_20261006_p01` — 0/3 |
| `tab:frequency` + `figA2` | appendix H | "Exploratory sweep on grid medium … 3 seeds/condition; new batch, not pooled with Appendix I" | `campaigns/paper-e5-e7-priority/E7-frequency-stage1` — 0/3 |
| `tab:e5pilot` + `figA4` | appendix I.5 | "first 9 high-fidelity failures from IE-03/IE-08 LLM+RL runs, seeds 5101--5112; first 3 grid failures … seeds 5201--5212" | `data/e5-attribution/` — 9/12 exact |
| `tab:nointel` | appendix G | "no-intelligence vs. legacy wave-by-wave opponent intelligence" | withheld arm in-tree; legacy arm in `~/<private-archive>/declared_briefing_snapshot_20260927_1417` |
| `tab:modelinvariance` + `figA1` | (appendix, "Model-invariance scan") | "two dense (Qwen3.8-27B, Qwen3-8B; local vLLM) and two MoE (MiniMax-M3, MiniMax-M2.7-highspeed; third-party API)" | `campaigns/e6-model-invariance` — 2 of 4 models |
| E1 calibration / gates / confirmation | **E1** | "IE-05 at four frozen quantities (17/18/19/27 units). Calibration (960 episodes, seeds 4101--4110), gate checks (4151--4160), confirmation (4201--4210)" | `E1_*` batches — seeds present |
| appendix I.4 critical-fault | — | "planner-side injection costs 0.567 … (10 seeds)" | `data/g1-fault-dose/` — does not reproduce |
| appendix I.3 real-stream | — | "(seeds 601--610) … authentic LLM Goal stream vs. legal all-hold" | **absent** |
| `tab:interface` | (appendix, "Interface modality comparison") | "Natural-language vs. JSON state rendering for the same scenarios" | **not located** |

## 4. A batch name the paper does *not* use, but which identifies a whole family

`E5` is the paper's **case-ID prefix** for the natural-failure pilot (`E5-01`…`E5-12`),
and it is also the prefix of every campaign directory that fed it
(`e5-hifi-attribution-r3b`, `e5-grid-natural-failures`, `e5-annotation-final`). The paper
never writes "E5" as an experiment code, but the correspondence is unambiguous.

Likewise `E14` appears once as a code — "Baseline-strength diagnostic (E14)"
(appendix.tex 162) — and `E14_Grid_complex-baseline_p01_20261003` is in the repo.

## 5. Collateral find: a co-author note that states the mapping

`data/collaborator_runs/e11-cross-scene-20261003/code/paper_table_reference.json` records,
in the co-author's own words, that the high-fidelity main table is **Table 5 on page 8 of
`openmd0930.pdf`**, and warns that a checklist calls it Table 4 — "use scenario ID not
invented HE IDs". It carries two scenarios' values (IE-06, IE-11) with the precision
target "checked against original source reconstruction within 0.00051".

The companion `E11实验设计与执行说明_v1.md` adds three operational rules worth knowing:

* E11 reuses "E10 p02, two scenarios × 400 events (200 real, 200 decoy), 800 total";
* it reads the three LLM architectures' seeds "7/11/13/17/19" from the main batch and
  applies "`_w1_common.py` original rules" — i.e. the same口径 as this release;
* planning uses "the normalised `defender_score`, not divided by applicable weight again",
  and the reconstruction "must match every three-decimal cell of the 0930 paper's page-8
  high-fidelity main table".

That is an independent confirmation of the metric convention this release enforces.

## 6. Reproducing the search

```bash
python reproduce/extract_paper_refs.py     # tables/figures/paths referenced by the sources
```
