"""Resolve the copied toolkit's project without changing engine contents."""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
_override = os.environ.get('ROLEC_OPENMD_ROOT')
_candidates = ([Path(_override)] if _override else
               [PROJECT / 'source-code' / 'openmd', PROJECT / 'openmd'])
_valid = [p.resolve() for p in _candidates
          if (p / 'code' / 'eval' / 'run_episode.py').is_file()
          and (p / 'source-code' / 'source_codes' / 'openmdbench').is_dir()]
if len(_valid) != 1:
    raise RuntimeError('Set ROLEC_OPENMD_ROOT to one unambiguous OpenMDBench tree: '
                       + ', '.join(str(p) for p in _candidates))
OPENMD = _valid[0]
ENGINE = OPENMD / 'source-code' / 'source_codes'
EVAL = OPENMD / 'code' / 'eval'
