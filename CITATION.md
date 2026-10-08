# Citation

If you use this release, please cite the paper rather than the repository alone.

## The paper

```bibtex
@inproceedings{openmdbench2027,
  title     = {OpenMDBench: Layering the {LLM} Only Where It Pays},
  booktitle = {Proceedings of the 26th International Conference on Autonomous Agents
               and Multiagent Systems (AAMAS 2027)},
  year      = {2027},
  address   = {Hanoi, Vietnam},
  note      = {Anonymous submission ID 817; author list withheld during review}
}
```

> The author list and final venue details are withheld while the submission is under
> anonymous review. **Update this file before publishing the repository publicly**, and
> replace the `note` field with the camera-ready bibliographic record.

## This release

```bibtex
@misc{openmdbench_release,
  title        = {{OpenMDBench} release: code, data and reproduction material for the
                  high-fidelity layering study},
  year         = {2026},
  howpublished = {\url{https://github.com/anony2026mous/OpenMDBench}},
  note         = {Anonymous review copy}
}
```

## What to cite for specific claims

| Claim in the paper | Cite | Evidence in this repository |
|---|---|---|
| Main suite table (`tab_hifi_main`) | the paper | `data/grid_withheld_5seeds/`, verified by `reproduce/verify_paper_table.py` |
| No-intelligence ablation (`tab_hifi_nointel`) | the paper | `data/grid_withheld_5seeds/` (`briefing` field per episode) |
| Grid goal-dose results | the paper | `data/EXTERNAL_DATA_MANIFEST.json` (raw traces not in git) |
| Fairness / determinism audits | the paper's appendix | `data/grid_withheld_5seeds/WITHHELD_BRIEFING_EVIDENCE.md` |
| Platform itself | the paper | `code/engine/` |

## Data licence

Experimental data and the manuscript are **CC BY 4.0**; see [`LICENSE.md`](LICENSE.md) for
the per-subtree breakdown, which also covers code and policy weights.
