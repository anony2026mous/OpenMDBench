"""Unit tests for the pure parts of hifi_record_campaign (no engine, no model)."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest

import hifi_record_campaign as h

RULE = {'min_effect': 0.05, 'tie_margin': 0.05}


@pytest.mark.parametrize('dp,de,di,label', [
    (0.30, 0.02, 0.00, 'planning'),
    (0.01, 0.40, 0.05, 'execution'),
    (0.02, 0.03, -0.30, 'interface'),
    (0.20, 0.18, 0.00, 'balanced'),
    (0.02, -0.10, 0.01, 'undetermined'),
])
def test_label_rule(dp, de, di, label):
    assert h.label_attribution(RULE, dp, de, di) == label


def test_failure_rule_only_for_registered_planner():
    plan = {'failure_rule': {'planners': ['llm-rl'], 'score_below': 0.6}}
    assert h.is_failure(plan, {'planner': 'llm-rl'}, {'defender_score': 0.59})
    assert not h.is_failure(plan, {'planner': 'llm-rl'}, {'defender_score': 0.6})
    assert not h.is_failure(plan, {'planner': 'rule'}, {'defender_score': 0.1})
    assert not h.is_failure({}, {'planner': 'llm-rl'}, {'defender_score': 0.1})


def test_pick_endpoint_balances_and_caps():
    plan = {'endpoints': [{'name': 'a', 'url': 'A'}, {'name': 'b', 'url': 'B'}],
            'max_inflight_per_endpoint': 2}
    assert h.pick_endpoint(plan, {}) == 'A'
    assert h.pick_endpoint(plan, {'A': 1}) == 'B'
    assert h.pick_endpoint(plan, {'A': 2, 'B': 1}) == 'B'
    assert h.pick_endpoint(plan, {'A': 2, 'B': 2}) is None


def test_next_cases_seed_major_and_stop_seeds():
    cases = [{'id': f'c{s}{x}', 'seed': s} for s in (1, 2, 3) for x in 'ab']
    plan = {'cases': cases}
    assert [c['id'] for c in h.next_cases(plan, {'c1a'}, {'c1b'}, None)] == ['c2a', 'c2b', 'c3a', 'c3b']
    assert [c['id'] for c in h.next_cases(plan, set(), set(), [1])] == ['c1a', 'c1b']


def _write(folder, trajectory, decisions, report):
    folder.mkdir()
    (folder / 'trajectory.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in trajectory))
    if decisions is not None:
        (folder / 'decisions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in decisions))
    (folder / 'report.json').write_text(json.dumps(report))


def test_compare_runs_ignores_wallclock_and_finds_divergence(tmp_path):
    report = {'ticks_run': 1, 'terminal_result': {'outcome': 'x'}, 'strategy_scorecard': {'s': 1},
              'total_fires': 0, 'damage_by_kind': {}}
    traj = [{'tick': 0, 'entities': [1], 'recorded_at_utc': 'a'}, {'tick': 1, 'entities': [2], 'recorded_at_utc': 'b'}]
    _write(tmp_path / 'o', traj, [{'tick': 0}], report)
    _write(tmp_path / 'r', [dict(r, recorded_at_utc='z') for r in traj], [{'tick': 0}], report)
    assert h.compare_runs(tmp_path / 'o', tmp_path / 'r')['exact_match']
    _write(tmp_path / 'd', [traj[0], {'tick': 1, 'entities': [3]}], [{'tick': 0}], report)
    result = h.compare_runs(tmp_path / 'o', tmp_path / 'd')
    assert not result['exact_match'] and result['trajectory.jsonl']['first_divergent_tick'] == 1


def test_compare_runs_legacy_without_decisions(tmp_path):
    report = {'ticks_run': 0}
    _write(tmp_path / 'o', [{'tick': 0}], None, report)
    _write(tmp_path / 'r', [{'tick': 0}], [{'tick': 0}], report)
    result = h.compare_runs(tmp_path / 'o', tmp_path / 'r')
    assert result['exact_match'] and result['decisions_not_in_legacy_original']


def test_legacy_calls_get_derived_ticks(tmp_path):
    rows = []
    for i in range(3):
        rows += [{'kind': 'request', 'call_index': i, 'system_prompt': 's', 'user_message': str(i)},
                 {'kind': 'response', 'call_index': i, 'response': 'r' + str(i)}]
    (tmp_path / 'requests.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    calls = h.load_recorded_calls(tmp_path)
    assert [c['tick'] for c in calls] == [0, 10, 20] and all(c['tick_derived'] for c in calls)


def test_recorded_errors_are_not_replayable(tmp_path):
    rows = [{'kind': 'request', 'call_index': 0}, {'kind': 'error', 'call_index': 0}]
    (tmp_path / 'requests.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    with pytest.raises(h.ReplayDivergence):
        h.load_recorded_calls(tmp_path)


def test_plain_handles_dataclasses_and_nonfinite():
    from dataclasses import dataclass

    @dataclass
    class Goal:
        task_id: str
        parameters: dict

    assert h.plain([Goal('t', {'x': float('nan')})]) == [{'task_id': 't', 'parameters': {'x': 'nan'}}]


def test_episode_folder_prefers_certified_prior(tmp_path, monkeypatch):
    prior, current = tmp_path / 'prior', tmp_path / 'cur'
    monkeypatch.setattr(h, 'certified', lambda folder: folder == prior / 'episodes' / 'x')
    plan = {'prior_campaigns': [str(prior)]}
    assert h.episode_folder(plan, current, 'x') == prior / 'episodes' / 'x'
    assert h.episode_folder(plan, current, 'y') == current / 'episodes' / 'y'
    assert h.episode_folder({}, current, 'x') == current / 'episodes' / 'x'


def test_prior_attribution_complete(tmp_path):
    folder = tmp_path / 'prior' / 'attribution' / 'x'
    folder.mkdir(parents=True)
    (folder / 'attribution.json').write_text(json.dumps({'status': 'complete'}))
    plan = {'prior_campaigns': [str(tmp_path / 'prior')]}
    assert h.prior_attribution_complete(plan, 'x')
    (folder / 'attribution.json').write_text(json.dumps({'status': 'counterfactual_incomplete'}))
    assert not h.prior_attribution_complete(plan, 'x')
    assert not h.prior_attribution_complete(plan, 'y')


def test_kappa():
    import e5_annotation as e
    assert e.kappa([('a', 'a'), ('b', 'b')]) == 1.0
    assert e.kappa([('a', 'b'), ('b', 'a')]) == -1.0
    assert abs(e.kappa([('a', 'a'), ('a', 'b'), ('b', 'b'), ('b', 'b')]) - 0.5) < 1e-9


def test_reusable_run_only_complete(tmp_path):
    base = tmp_path / 'p' / 'attribution' / 'c'
    for name, status in (('self_replay', 'complete'), ('reference_executor', 'ineligible')):
        (base / name).mkdir(parents=True)
        (base / name / 'manifest.json').write_text(json.dumps({'status': status, 'replay_divergence': []}))
    plan = {'prior_campaigns': [str(tmp_path / 'p')]}
    assert h.reusable_run(plan, 'c', 'self_replay') == base / 'self_replay'
    assert h.reusable_run(plan, 'c', 'reference_executor') is None
    assert h.reusable_run(plan, 'c', 'reference_full') is None
