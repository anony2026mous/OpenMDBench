# Figure and Table Regeneration (paper revision 2026-09-29)

Mapping from every data-backed figure/table in `main.tex` and `appendix.tex`
to its generation script and frozen data. All scripts run from this directory
with system `python3`; no network access required (set
`MPLCONFIGDIR` to a writable dir for matplotlib caching).

## Script-generated items

| Paper item | Script | Data | Command |
|---|---|---|---|
| Fig.~3 (coupling scatter, grid) | `draw_coupling_figure.py` | `data/grid/coupling_experiment_medium.json`, `data/grid/coupling_dryrun_medium_rule.json` | `python3 draw_coupling_figure.py` |
| Fig.~4 (end-to-end gap, hifi) | `draw_hifi_gap_figure.py` (loads via `hifi_stats.py`) | `data/hifi_withheld/DATASET_5SEEDS.json` | `python3 draw_hifi_gap_figure.py` |
| Table 4 (hifi main results) | `build_hifi_tables.py` | `data/hifi_withheld/DATASET_5SEEDS.json` | `python3 build_hifi_tables.py` |
| Table 5 (intelligence-regime ablation) | `build_hifi_tables.py` | same as Table 4 | same run |
| App.~A Table 1 (admitted scenario parameters) | `build_scenario_table.py` | `data/hifi_withheld/scenario_packs/ie_*/{scenario,agents}.yaml` (14 packs) | `python3 build_scenario_table.py` |
| App.~A headroom Spearman numbers | `headroom_spearman.py` | `data/hifi_withheld/DATASET_5SEEDS.json` | `python3 headroom_spearman.py` |

Outputs land in `../figures/` (PDF) and `../tables/` (LaTeX), which `main.tex`
/ `appendix.tex` `\input` directly. Edit scripts, never the generated files.

## Hand-written tables backed by frozen data (verification copies only)

| Paper item | Backing data | Note |
|---|---|---|
| Table 2 (attribution injected-bottleneck) | `data/grid/attribution_a10.json` | case-level means only; per-seed detail still owed (A1 in the alignment memo) |
| Table 3 (intervention study) | `data/grid/grid_info_experiment.json` | 4 systems x 20 paired episodes |
| App.~H interface-modality table | `data/grid/ablation_nl_json_medium45.json`, `data/grid/ablation_nl_json_complex45.json` | simple-tier row from the same family |
| Sec.~6.2 Elo numbers (text) | `data/tournament/elo_ratings.json`, `data/tournament/tournament_results.json` | 75 matches round-robin |
| Sec.~6.2 2x2 factorial numbers (text) | `data/grid/criterion2_decision_c.json` | sr_list only (A2 in the memo) |

## Provenance of copied data

- `data/grid/*`: byte-identical copies of `code/results/` on the `main`
  branch of the openmd repository (grid-side experiment outputs).
- `data/tournament/*`: copies of `code/tournament_output/` (exists only on
  the `main` branch).
- `data/hifi_withheld/*`: collaborator snapshot branch
  `workspace-snapshot-20260928-214905`; see `data/hifi_withheld/README.md`
  for hygiene notes (withheld-only filtering, score normalization, seed
  semantics) and the regeneration commands.

## Items without regeneration data

- Table 1 (benchmark comparison): literature-based, hand-written.
- Fig.~1: hand-drawn in draw.io (SVG+PDF); source file `fig1_narrative_zhang.svg`/
  `fig1_narrative_zhang.pdf` (2026-10-08 collaborator revision, replaces the
  earlier `fig_narrative_overview.pdf`). Numbers are backed by the frozen data
  cited in the main text and Appendix~\ref{app:F}--\ref{app:I}.
- Fig.~2: reserved placeholder frame; artwork pending (C5 in the alignment memo).

## Compile (authoritative PDFs live in this paper directory only)

```
XDG_CACHE_HOME=<cache> tectonic --outdir . main.tex      # -> ./main.pdf
XDG_CACHE_HOME=<cache> tectonic --outdir . appendix.tex  # -> ./appendix.pdf
```

`main.pdf` and `appendix.pdf` in `doc/aamas2027/` are the single source of
truth; no other build copies are kept.
