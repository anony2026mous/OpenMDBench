"""Local configuration tests: no network access or model inference."""
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QwenConfigurationTests(unittest.TestCase):
    def load_smoke(self, overrides):
        clean = {k: v for k, v in os.environ.items()
                 if k not in ('ROLEC_LLM_BASE_URL', 'ROLEC_LLM_MODEL')}
        clean.update(overrides)
        with patch.dict(os.environ, clean, clear=True), patch.object(
                sys, 'path', [str(ROOT / 'role_c_toolkit'), *sys.path]):
            return runpy.run_path(str(ROOT / 'role_c_toolkit/p0_6_smoke.py'))

    def test_existing_reference_defaults_are_unchanged(self):
        values = self.load_smoke({})
        self.assertEqual(values['BASE_URL'], 'http://172.18.116.170:8000/v1')
        self.assertEqual(values['MODEL'], 'Qwen3.8-27B')

    def test_new_service_can_be_selected_without_source_rewrite(self):
        values = self.load_smoke({'ROLEC_LLM_BASE_URL': 'http://127.0.0.1:8001/v1/',
                                  'ROLEC_LLM_MODEL': 'Qwen3.8-27B'})
        self.assertEqual(values['BASE_URL'], 'http://127.0.0.1:8001/v1')
        self.assertEqual(values['MODEL'], 'Qwen3.8-27B')

    def test_replicas_share_files_not_ports_or_gpus(self):
        launcher = load_tool('qwen_launcher', 'tools/huairou/start_qwen_service.py')
        a, b = launcher.command(8001, 'a'), launcher.command(8002, 'b')
        self.assertEqual(a[a.index('--model') + 1], b[b.index('--model') + 1])
        self.assertNotEqual(a[a.index('--port') + 1], b[b.index('--port') + 1])
        self.assertEqual(launcher.REPLICAS, {'a': ('0,1', 8001), 'b': ('2,3', 8002),
                                             'c': ('2,3', 8003)})
        env = launcher.service_environment('0,1', 'a')
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(launcher.PYTHON.parent))
        self.assertEqual(env['VIRTUAL_ENV'], str(launcher.PYTHON.parent.parent))
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'], '0,1')
        self.assertEqual(env['CUDA_HOME'], str(launcher.CUDA_HOME))
        self.assertEqual(env['FLASHINFER_NVCC'], str(launcher.CUDA_HOME / 'bin/nvcc'))
        self.assertIn(str(launcher.CUDA_HOME / 'bin'), env['PATH'].split(os.pathsep))
        self.assertIn(str(launcher.CURAND_INCLUDE), env['CPATH'].split(os.pathsep))
        for command in (a, b):
            for flag, value in {'--dtype': 'bfloat16', '--kv-cache-dtype': 'fp8',
                                '--max-model-len': '131072',
                                '--tensor-parallel-size': '2',
                                '--num-gpu-blocks-override': '296',
                                '--host': '127.0.0.1'}.items():
                self.assertEqual(command[command.index(flag) + 1], value)
            self.assertIn('--no-enable-prefix-caching', command)

    def test_second_model_replica_keeps_its_own_identity_and_layout(self):
        launcher = load_tool('qwen_launcher_c', 'tools/huairou/start_qwen_service.py')
        c = launcher.command(8003, 'c')
        a = launcher.command(8001, 'a')
        self.assertEqual(c[c.index('--model') + 1], str(launcher.EIGHT_B_MODEL))
        self.assertEqual(c[c.index('--served-model-name') + 1], 'Qwen3-8B')
        self.assertNotEqual(c[c.index('--served-model-name') + 1],
                            a[a.index('--served-model-name') + 1])
        self.assertEqual(c[c.index('--port') + 1], '8003')
        self.assertEqual(c[c.index('--tensor-parallel-size') + 1], '2')
        self.assertEqual(c[c.index('--dtype') + 1], 'bfloat16')
        self.assertEqual(c[c.index('--max-model-len') + 1], '40960')
        self.assertEqual(launcher.max_model_len('c'), 40960)
        self.assertEqual(launcher.max_model_len('a'), 131072)
        self.assertEqual(c[c.index('--kv-cache-dtype') + 1], 'fp8')
        # The 27B reference block count belongs to the 27B KV layout.
        self.assertNotEqual(c[c.index('--num-gpu-blocks-override') + 1], '296')
        self.assertEqual(launcher.kv_blocks('c'), 16 * 1024 ** 3 // (16 * 36 * 8 * 128 * 2))
        self.assertEqual(launcher.kv_blocks('c'), 14563)
        self.assertEqual(launcher.kv_blocks('a'), launcher.REFERENCE_KV_BLOCKS)
        # A block must be the measured 16-token grid, not an invented one.
        self.assertEqual(launcher.EIGHT_B_BLOCK_BYTES, 1179648)
        self.assertEqual(launcher.kv_blocks('c') * 16, 233008)

    def test_downloader_requires_review_before_another_repository(self):
        downloader = load_tool('qwen_downloader', 'tools/huairou/download_qwen_weights.py')
        manifest = {'repository': 'Qwen/Qwen3-8B', 'files': [
            {'Path': 'config.json', 'Size': 10, 'Sha256': '0' * 64, 'Revision': 'a' * 40}]}
        with self.assertRaises(ValueError):
            downloader.reviewed_repository(manifest, False)
        self.assertEqual(downloader.reviewed_repository(manifest, True), 'Qwen/Qwen3-8B')
        self.assertEqual(downloader.reviewed_repository(
            {'repository': 'Qwen/Qwen3.8-27B'}, False), 'Qwen/Qwen3.8-27B')
        with self.assertRaises(ValueError):
            downloader.reviewed_repository({'files': []}, True)

    def test_downloader_writes_a_receipt_naming_the_repository(self):
        # fcntl and flock only exist on the Linux server, so exercise the receipt
        # contract on the server-side path without calling main() locally.
        downloader = load_tool('qwen_downloader_receipt', 'tools/huairou/download_qwen_weights.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = {'repository': 'Qwen/Qwen3-8B', 'files': [
                {'Path': 'config.json', 'Size': 10, 'Sha256': '0' * 64, 'Revision': 'a' * 40}]}
            (root / 'source-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            receipt = {'status': 'all_files_sha256_verified', 'repository': 'Qwen/Qwen3-8B',
                       'files': 1, 'manifest_sha256': downloader.digest(root / 'source-manifest.json'),
                       'reference_host_hashes_compared': False}
            (root / 'download-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
            launcher = load_tool('qwen_launcher_receipt', 'tools/huairou/start_qwen_service.py')
            self.assertEqual(launcher.model_dir('c'), launcher.EIGHT_B_MODEL)
            self.assertEqual(launcher.model_dir('a'), launcher.MODEL)

    def test_manifest_pinning_rejects_unpinned_or_truncated_hashes(self):
        fetcher = load_tool('qwen_manifest', 'tools/huairou/fetch_modelscope_manifest.py')
        payload = {'Data': {'Files': [
            {'Path': 'config.json', 'Size': 10, 'Sha256': 'a' * 64, 'Revision': 'b' * 40},
            {'Path': 'model-00001-of-00005.safetensors', 'Size': 20, 'Sha256': 'c' * 64,
             'Revision': 'b' * 40}]}}
        rows = fetcher.entries(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(fetcher.resolve_revision(rows, 'master'), ['b' * 40])
        two_commits = [{'Path': 'a', 'Revision': 'b' * 40}, {'Path': 'b', 'Revision': 'c' * 40}]
        self.assertEqual(fetcher.resolve_revision(two_commits, 'master'), ['b' * 40, 'c' * 40])
        with self.assertRaises(ValueError):
            fetcher.entries({'Data': {'Files': [
                {'Path': 'config.json', 'Size': 10, 'Sha256': 'abc', 'Revision': 'b' * 40}]}})
        with self.assertRaises(ValueError):
            fetcher.resolve_revision([{'Path': 'a', 'Revision': None}], 'master')

    def test_smoke_accepts_explicit_main_experiment_goal_tier(self):
        values = self.load_smoke({})
        capture = Mock()
        with tempfile.TemporaryDirectory() as folder:
            argv = ['p0_6_smoke.py', '--output-dir', folder, '--arm', 'rule',
                    '--goal-granularity', 'strong']
            with patch.object(sys, 'argv', argv), patch.dict(values['main'].__globals__, {'smoke': capture}):
                values['main']()
        capture.assert_called_once()
        self.assertEqual(capture.call_args.args[0].goal_granularity, 'strong')

    def test_goal_tier_scope_matches_formal_main_entrypoint(self):
        values = self.load_smoke({})
        for arm in values['ARMS']:
            expected = ['--goal-granularity', 'strong'] if arm in ('rule-rl', 'llm-rl') else []
            self.assertEqual(values['goal_cli_args'](arm, 'strong'), expected)
            self.assertEqual(values['goal_cli_args'](arm, None), [])


if __name__ == '__main__':
    unittest.main()
