"""Probe a replica without claiming full ablation or long-context equivalence."""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request


def cache_labels(text):
    rows = [line for line in text.splitlines() if line.startswith('vllm:cache_config_info{')]
    if len(rows) != 1:
        raise ValueError('Expected exactly one cache configuration metric')
    quote = chr(34)
    return dict(re.findall('([a-z_]+)=' + quote + '([^' + quote + ']*)' + quote, rows[0]))


def compare_cache(actual, expected):
    # An explicit allocation cap replaces automatic allocation on larger GPUs.
    # Compare its effective block count/capacity, not the mechanism selecting it.
    keys = [key for key in expected if key != 'num_gpu_blocks_override']
    differences = {}
    for key in keys:
        value = 'None' if expected[key] is None else str(expected[key])
        if actual.get(key) != value:
            differences[key] = {'reference': value, 'actual': actual.get(key)}
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wait-seconds', type=int, default=0)
    parser.add_argument('--state-file', type=Path)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    if not base.endswith('/v1'):
        parser.error('base-url must end in /v1')
    root = base[:-3]
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    reference = baseline['reference_observed']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def read(url, timeout=10):
        with opener.open(url, timeout=timeout) as response:
            return response.read().decode('utf-8')

    state = json.loads(args.state_file.read_text()) if args.state_file else None
    if state and urllib.parse.urlsplit(base).port != state['port']:
        parser.error('State file does not match the selected service port')
    deadline = time.monotonic() + max(0, args.wait_seconds)
    last_progress = 0.0
    while True:
        if state:
            process = Path('/proc') / str(state['pid'])
            if not process.exists():
                raise RuntimeError('Recorded service exited; inspect ' + state['log'])
            status = (process / 'status').read_text()
            if any(line.startswith('State:') and 'Z (zombie)' in line for line in status.splitlines()):
                raise RuntimeError('Recorded service is a zombie; inspect ' + state['log'])
        try:
            read(root + '/health', timeout=3)
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError('Service not ready within bounded wait; check process before retrying')
            if time.monotonic() - last_progress >= 30:
                print('WAITING_FOR_HEALTH', base, flush=True)
                last_progress = time.monotonic()
            time.sleep(5)

    models = json.loads(read(base + '/models'))['data']
    model = next(m for m in models if m['id'] == reference['served_model_name'])
    version = json.loads(read(root + '/version'))['version']
    labels = cache_labels(read(root + '/metrics'))
    payload = {'model': reference['served_model_name'],
               'messages': [{'role': 'user', 'content': 'Reply with exactly OK.'}],
               'max_tokens': 32, 'temperature': 0.1,
               'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request(base + '/chat/completions',
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    reply = json.loads(read(request, timeout=90))
    message = reply['choices'][0]['message']
    content = message.get('content') or ''
    inference_ok = bool(content.strip()) and '<think>' not in content.lower()
    inference_ok = inference_ok and not message.get('reasoning_content') and not message.get('reasoning')
    differences = compare_cache(labels, reference['cache'])
    context_ok = model.get('max_model_len') == reference['max_model_len']
    version_ok = version.split('+')[0] == reference['vllm_version']
    report = {'base_url': base, 'runtime_version': version, 'model': model['id'],
              'max_model_len': model.get('max_model_len'),
              'short_inference_passed': bool(inference_ok), 'content': content,
              'usage': reply.get('usage'), 'finish_reason': reply['choices'][0].get('finish_reason'),
              'context_matches_reference': context_ok, 'version_matches_reference': version_ok,
              'cache_labels': labels, 'cache_differences': differences,
              'observed_settings_match': bool(context_ok and version_ok and not differences),
              'long_context_load_tested': False, 'full_reference_identity_verified': False,
              'unknown_reference_fields': baseline['unknown_reference_fields']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if inference_ok and report['observed_settings_match'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
