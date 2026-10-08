"""Audit the requested bounded validation; never claim a complete ablation run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import urllib.request

from probe_qwen_service import cache_labels, compare_cache

BASE = Path('/mnt/QTJC/chenyi-codex')
SCENES = {'IE-04-COMBINED-ARMS', 'IE-10-DUAL-AXIS-PINCER', 'IE-11-DECOY-SCREEN'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_batch(folder, scenes, arms, ticks, endpoint=None):
    manifests = [load(p) for p in sorted(folder.glob('*_manifest.json'))]
    expected = {(scene, arm) for scene in scenes for arm in arms}
    check(len(manifests) == len(expected), f'Incomplete case count: {folder}')
    check({(m['scenario'], m['arm']) for m in manifests} == expected, 'Case coverage differs')
    rows = []
    for m in manifests:
        name = m['run_id']
        check(m['interface_ok'] and m['ticks_run'] == ticks and m['seed'] == 9901, name + ': interface/seed/ticks')
        check(m['aborted'] is None, name + ': aborted')
        for suffix, key in [('.json', 'report_sha256'), ('.jsonl', 'log_sha256'),
                            ('_requests.json', 'requests_sha256')]:
            check(digest(folder / (name + suffix)) == m[key], name + ': output hash mismatch')
        report = load(folder / (name + '.json'))
        check(report['error'] in (None, '') and report['traceback'] in (None, ''), name + ': runtime error')
        calls = load(folder / (name + '_requests.json'))
        row = {'run_id': name, 'scenario': m['scenario'], 'arm': m['arm'],
               'ticks': ticks, 'llm_calls': len(calls), 'report_sha256': m['report_sha256']}
        if endpoint is None:
            check(len(calls) == 0 and m['llm_calls_captured'] == 0, name + ': unexpected LLM call')
        else:
            check(len(calls) == 1 and m['llm_calls_captured'] == 1, name + ': wrong LLM call count')
            for call in calls:
                check(call['base_url'] == endpoint and call['model'] == 'Qwen3.8-27B', name + ': wrong service/model')
                check(call['backend'] == 'vllm' and call['enable_thinking'] is False, name + ': backend/thinking')
                check(call['effective_max_tokens'] == 1024 and call['temperature'] == 0.1, name + ': sampling budget')
            cli = m['cli_argv']
            if m['arm'] == 'llm-rl':
                check('--goal-granularity' in cli and cli[cli.index('--goal-granularity') + 1] == 'strong', name + ': Goal tier')
            else:
                check('--goal-granularity' not in cli, name + ': unexpected Goal override')
            defender = report['defender']
            if m['arm'] == 'pure-llm':
                check(defender['llm_calls'] == 1 and defender['fallback_count'] == 0, name + ': pure LLM fallback')
                row['masked_actions'] = defender['masked_count']
            else:
                planner = defender['planner']
                check(planner['plan_calls'] == 1 and planner['fallback_count'] == 0, name + ': planner fallback')
                check(planner['parse_failures'] == 0, name + ': LLM parse failure')
            row['fallback_count'] = 0
        rows.append(row)
    return {'output_directory': str(folder), 'cases_passed': len(rows), 'ticks_per_case': ticks,
            'formal_ablation_results': False, 'runs': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    model = BASE / 'models/Qwen3.8-27B-BF16'
    receipt = load(model / 'download-complete.json')
    check(receipt['status'] == 'all_files_sha256_verified', 'Download verification missing')
    check(digest(model / 'source-manifest.json') == receipt['manifest_sha256'], 'Model manifest changed')
    manifest = load(model / 'source-manifest.json')
    dtypes = set()
    shards = []
    for item in manifest['files']:
        path = model / item['Path']
        check(path.is_file() and path.stat().st_size == int(item['Size']), 'Model file size differs: ' + item['Path'])
        if path.suffix == '.safetensors':
            shards.append(path)
            with path.open('rb') as f:
                length = struct.unpack('<Q', f.read(8))[0]
                check(0 < length < 16 * 1024 * 1024, 'Unexpected safetensors header')
                header = json.loads(f.read(length))
            dtypes.update(v['dtype'] for k, v in header.items() if k != '__metadata__')
    check(len(shards) == 18 and dtypes == {'BF16'}, 'Unexpected weight shards or storage precision')
    services = BASE / 'services/qwen'
    baseline = load(services / 'qwen_reference_baseline.json')
    reference = baseline['reference_observed']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    replicas = []
    for name, devices, port in [('a', '0,1', 8001), ('b', '2,3', 8002)]:
        state = load(services / f'replica-{name}.json')
        check(state['gpu_devices'] == devices and state['port'] == port, 'Replica isolation differs')
        process = Path('/proc') / str(state['pid'])
        check(process.exists(), 'Service process exited')
        command = (process / 'cmdline').read_bytes().split(bytes([0]))
        check(b'vllm.entrypoints.openai.api_server' in command and str(port).encode() in command, 'Wrong process identity')
        check(state['model_manifest_sha256'] == receipt['manifest_sha256'], 'Replica weight identity differs')
        root = f'http://127.0.0.1:{port}'
        with opener.open(root + '/health', timeout=5) as response:
            check(response.status == 200, 'Service is not healthy')
        with opener.open(root + '/metrics', timeout=5) as response:
            cache = cache_labels(response.read().decode())
        check(not compare_cache(cache, reference['cache']), 'Reference cache settings differ')
        validated = load(services / f'replica-{name}-validated-capped.json')
        check(validated['short_inference_passed'] and validated['observed_settings_match'], 'Short inference check missing')
        replicas.append({'replica': name, 'pid': state['pid'], 'gpus': devices,
                         'endpoint': root + '/v1', 'known_cache_settings_match': True})
    check(replicas[0]['pid'] != replicas[1]['pid'], 'Replicas must be independent processes')
    validation = BASE / 'validation'
    cpu = audit_batch(validation / 'cpu-main-smoke-20260930-a', SCENES, {'rule', 'rule-rl', 'rl'}, 12)
    arms = {'llm', 'llm-rl', 'pure-llm'}
    a = audit_batch(validation / 'llm-main-smoke-20260930-a-strong-v2', SCENES, arms, 6, 'http://127.0.0.1:8001/v1')
    b = audit_batch(validation / 'llm-main-smoke-20260930-b-strong-v2', {'IE-10-DUAL-AXIS-PINCER'}, arms, 6, 'http://127.0.0.1:8002/v1')
    result = {'status': 'bounded_readiness_checks_passed',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'weights': {'path': str(model), 'shards': len(shards), 'storage_dtypes': sorted(dtypes),
                          'bytes': sum(p.stat().st_size for p in shards),
                          'sha256_verified_at_download': True, 'current_sizes_and_manifest_checked': True},
              'replicas': replicas, 'cpu_validation': cpu, 'llm_validation': [a, b],
              'limitations': ['Not a complete natural-terminal or full-seed experiment.',
                              'No training was requested or performed by these validation runs.',
                              '131072 context setting verified, but no full-length saturation test.',
                              'Original host weight/tokenizer hashes and unspecified serving settings not fully compared.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'cpu_cases': cpu['cases_passed'],
                      'llm_cases': a['cases_passed'] + b['cases_passed'],
                      'replicas': replicas, 'output': str(args.output)}), flush=True)


if __name__ == '__main__':
    main()
