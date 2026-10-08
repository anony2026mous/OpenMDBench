# Phase 0 baseline report

- Date: 2026-08-05
- Status: PASS
- Runtime: Ubuntu-compatible CPU baseline, Python 3.11.15

## Delivered tasks

- T0.1: Ubuntu package scaffold, optional dependency groups, Make targets, CI matrix.
- T0.2: explicit MMG and kinematic action contracts, centralized heading conversions, RVO
  heading controller.
- T0.3: one controlled USV per environment with explicit batch/entity/action axes.
- T0.4: Gymnasium contract, separate termination/truncation, terminal-state freeze, and legacy
  obstacle/potential/mask/target-direction fixes.
- T0.5: session RNG, seed/config metadata, and 1000-tick replay determinism.
- T0.6: bounded repeat-safe Buffer and legacy actor/critic/BEV/persistence fixes.

## Verification

```text
make lint                                                    PASS
make typecheck                                               PASS
make test                                                    PASS (33 tests)
pytest tests/unit tests/integration/test_surface_smoke.py     PASS (21 tests)
python -m openmdbench.cli run --scenario surface-smoke \
  --seed 7 --ticks 1000                                      PASS
```

The CLI completed exactly 1000 ticks, returned `terminated=false`, `truncated=true`, and
recorded seed 7 plus a SHA-256 configuration hash. The Taichi batch smoke ran two environments
with one active USV each for 1000 ticks without non-finite position or velocity values.

## Known warnings

- Taichi 1.7.4 uses a Python locale API deprecated for Python 3.15; supported Python 3.11/3.12
  are unaffected.
- Gymnasium recommends normalized Box actions; Phase 0 intentionally keeps the documented
  physical `[speed_mps, heading_deg]` action contract.
- Python 3.12 is covered by CI but was not installed on this host.
