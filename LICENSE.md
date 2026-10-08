# Licensing of this release

This repository aggregates material with **different terms**. No single licence covers all
of it, so each part is stated below rather than collapsed into one SPDX identifier.

## 1. Manuscript (`paper/`)

`main.tex`, `main.pdf`, `appendix.tex`, `appendix.pdf`, `figures/`, `tables/` and
`refs.bib` are released under the **Creative Commons Attribution 4.0 International
(CC BY 4.0)** licence, as declared in the manuscript's own AAMAS copyright block:
<https://creativecommons.org/licenses/by/4.0/>

The conference class file `aamas.cls` and `ACM-Reference-Format.bst` are third-party
style assets from the AAMAS/ACM template distribution and remain under their own terms.

## 2. Simulation platform (`code/engine/`)

Declared in `code/engine/pyproject.toml` as:

```
license = { text = "Research use; see repository terms" }
```

It is the authors' own platform. Contact the authors for terms beyond research use.

## 3. Evaluation harness and analysis (`code/analysis/`, `reproduce/`)

Authors' own code, released for the purpose of reproducing the manuscript's results.
The analysis scripts are the provenance of every number in the paper, so you are
encouraged to run and quote them.

## 4. Attribution toolchain (`code/role_c_toolkit/`) and remote helper (`code/tools/`)

Authors' own code, same terms as §3. `code/role_c_toolkit/` contains policy checkpoint
assets (`assets/*.pt`) produced by the authors; they are included so the reported
comparisons can be reproduced and are **not** licensed for redistribution as standalone
model artefacts.

## 5. Policy weights (`code/analysis/_w1_runs/rl/*.npz`)

Reward / policy checkpoints trained by the authors. Included solely to make the reported
results reproducible. Same terms as §4.

## 6. Experimental data (`data/`)

Per-episode traces, consolidated tables and campaign records are the authors' own
measurements, released under **CC BY 4.0** to match the manuscript. Attribution should
cite the paper rather than this repository alone.

## 7. Third-party components

Any vendored third-party code, model weights or scenario catalogues keep their original
licences, which take precedence over the statements above. Where a file carries its own
header, that header governs.

---

If you need a single permissive licence for a specific subtree (for example to reuse only
the simulation platform under MIT/Apache-2.0), contact the authors — the split above is a
statement of current fact, not a refusal to license.
