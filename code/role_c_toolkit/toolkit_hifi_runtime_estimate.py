"""Estimate runtime from valid local episodes, without claiming equal conditions."""
import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from toolkit_paths import EVAL

SCENES = ('IE-04-COMBINED-ARMS', 'IE-10-DUAL-AXIS-PINCER', 'IE-11-DECOY-SCREEN')
ARMS = ('llm', 'llm-rl', 'pure-llm')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    groups = defaultdict(list)
    for path in (EVAL / '_w1_runs').glob('*_n3*.json'):
        r = json.loads(path.read_text(encoding='utf-8'))
        if r.get('scenario') not in SCENES or r.get('planner') not in ARMS:
            continue
        defender = r.get('defender') or {}
        briefing = defender.get('briefing') or (defender.get('planner') or {}).get('briefing')
        if r.get('aborted') is not None or r.get('terminal_result') is None or briefing != 'withheld':
            continue
        groups[(r['scenario'], r['planner'])].append((path.name, float(r['elapsed_seconds'])))
    rows = []
    for scene in SCENES:
        for arm in ARMS:
            values = groups[(scene, arm)]
            if not values:
                raise RuntimeError(f'Missing timing sample: {scene}/{arm}')
            secs = [v for _, v in values]
            rows.append({'scenario': scene, 'arm': arm, 'n': len(secs),
                         'mean_minutes': statistics.mean(secs)/60,
                         'min_minutes': min(secs)/60, 'max_minutes': max(secs)/60,
                         'source_files': [name for name, _ in values]})
    minutes_per_paired_seed = sum(r['mean_minutes'] for r in rows)
    summary = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'assumptions': ['Sequential single shared LLM endpoint',
                        'Historical mean is a reference, not a promise or an identical frozen batch',
                        'Rule/RL episodes, gate checks, retries, audit and analysis are additional',
                        'No speedup assumed from parallelism without measurement'],
        'historical_rows': rows,
        'pilot': {'total_episodes': 54, 'llm_episodes': 27,
                  'historical_llm_hours': minutes_per_paired_seed*3/60,
                  'conservative_llm_hours': [20.25, 27]},
        'main_20seed': {'total_episodes': 360, 'llm_episodes': 180,
                        'historical_llm_hours': minutes_per_paired_seed*20/60,
                        'conservative_llm_hours': [135, 180]},
        'full_core_plan': {'llm_episodes': 380, 'non_llm_episodes_at_least': 260,
                           'conservative_llm_hours': [285, 380],
                           'additional_rule_rl_replay_machine_hours': [15, 35],
                           'machine_hours_sum_not_calendar_guarantee': [300, 415],
                           'calendar_guidance_weeks': [2, 4],
                           'implementation_blockers': ['High-fidelity fault injection needs full natural-terminal validation',
                                'Independent oracle and formal causal mutual information are not implemented/accepted']},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / 'runtime_estimate.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k,v in summary.items() if k != 'historical_rows'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
