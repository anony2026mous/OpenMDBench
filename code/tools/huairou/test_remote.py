import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import remote


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads(remote.DEFAULT_CONFIG.read_text())
        self.config['include'] = ['code']
        self.config['include_files'] = []
        (self.root / 'code').mkdir()

    def write(self, name, text='print(1)'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_exclusions_and_uncommitted_sources(self):
        self.write('code/new.py')
        self.write('code/env/geo_coordinate.py')
        for name in ('code/.env', 'code/private.pem', 'code/.git/config',
                     'code/.venv/lib.py', 'code/reports/result.json', 'code/model.pt'):
            self.write(name)
        files, skipped = remote.discover(self.root, self.config)
        self.assertEqual(
            [name for name, _ in files],
            ['code/env/geo_coordinate.py', 'code/new.py'],
        )
        self.assertTrue(skipped)

    def test_path_escape_rejected(self):
        for name in ('../outside', '/root', 'C:/outside', 'a/../../b', 'a' + chr(92) + 'b'):
            with self.assertRaises(ValueError):
                remote.safe_relative(name)

    def test_explicit_checkpoint_does_not_include_run_outputs(self):
        self.write('code/_w1_runs/rl/selected.npz')
        self.write('code/_w1_runs/rl/unselected.npz')
        self.write('code/_w1_runs/report.json')
        self.config['include_files'] = ['code/_w1_runs/rl/selected.npz']
        files, _ = remote.discover(self.root, self.config)
        self.assertEqual([name for name, _ in files], ['code/_w1_runs/rl/selected.npz'])

    def test_explicit_file_cannot_allow_credentials(self):
        self.write('code/private.pem')
        self.config['include_files'] = ['code/private.pem']
        with self.assertRaises(ValueError):
            remote.discover(self.root, self.config)

    def test_explicit_checkpoint_still_obeys_size_cap(self):
        self.write('code/_w1_runs/selected.npz')
        self.config['include_files'] = ['code/_w1_runs/selected.npz']
        self.config['max_file_mib'] = 0
        with self.assertRaises(ValueError):
            remote.discover(self.root, self.config)

    def test_credentials_fail_without_printing_value(self):
        secret = 'sk-' + 'Q' * 40
        path = self.write('code/api.py', 'key=' + repr(secret))
        with self.assertRaises(ValueError) as exc:
            remote.source_bytes(path)
        self.assertNotIn(secret, str(exc.exception))

    def test_oversized_source_requires_review(self):
        self.config['max_file_mib'] = 0
        self.write('code/main.py')
        with self.assertRaises(ValueError):
            remote.discover(self.root, self.config)

    def test_archive_preserves_source_and_has_hash_manifest(self):
        self.write('code/main.py', 'print(42)')
        files, _ = remote.discover(self.root, self.config)
        archive = self.root / 'source.tar.gz'
        manifest = remote.package(files, archive)
        with tarfile.open(archive) as bundle:
            self.assertEqual(bundle.extractfile('code/main.py').read(), b'print(42)')
            self.assertEqual(json.load(bundle.extractfile('.huairou-manifest.json')), manifest)
        self.assertEqual(len(manifest['files'][0]['sha256']), 64)

    def test_project_python_gate_precedes_pytest(self):
        command = remote.command_for(self.config, '/tmp/snapshot', 'test', 'engine', ['--', '-q', 'tests/test_example.py'], None)
        self.assertIn('sys.exit(0 if ok else 86)', command)
        self.assertLess(command.index('sys.exit'), command.index('-m pytest'))
        self.assertIn('cd /tmp/snapshot/source_codes', command)
        self.assertIn('-m pytest -q tests/test_example.py', command)
        self.assertIn(chr(10), command)

    def test_default_test_only_collects(self):
        command = remote.command_for(self.config, '/tmp/snapshot', 'test', 'openmd', [], None)
        self.assertIn('--collect-only -q', command)
        self.assertIn('/tmp/snapshot/openmd/source-code/source_codes', command)

    def test_custom_command_and_profile(self):
        command = remote.command_for(self.config, '/tmp/snapshot', 'run', 'eval', [], 'python3 experiment.py --device cpu')
        self.assertTrue(command.endswith('python3 experiment.py --device cpu'))
        self.assertIn('cd /tmp/snapshot/openmd/code/eval', command)

    def test_embedded_remote_scripts_compile(self):
        for source in (remote.DEPLOY, remote.PROBE, remote.VERSION_CHECK):
            compile(source, '<remote>', 'exec')

    def test_incremental_archive_and_local_deletion(self):
        first = self.write('code/first.py', 'print(1)')
        second = self.write('code/second.py', 'print(2)')
        files, _ = remote.discover(self.root, self.config)
        before = remote.package(files, self.root / 'first.tar.gz')
        first.write_text('print(3)')
        second.unlink()
        self.write('code/third.py', 'print(4)')
        files, _ = remote.discover(self.root, self.config)
        archive = self.root / 'second.tar.gz'
        after = remote.package(files, archive, before)
        with tarfile.open(archive) as bundle:
            self.assertEqual(bundle.getnames(), ['code/first.py', 'code/third.py', '.huairou-manifest.json'])
        self.assertNotIn('code/second.py', [item['path'] for item in after['files']])

    def test_unchanged_sources_only_upload_manifest(self):
        self.write('code/main.py')
        files, _ = remote.discover(self.root, self.config)
        before = remote.package(files, self.root / 'first.tar.gz')
        archive = self.root / 'second.tar.gz'
        remote.package(files, archive, before)
        with tarfile.open(archive) as bundle:
            self.assertEqual(bundle.getnames(), ['.huairou-manifest.json'])

    def test_ssh_host_is_not_an_option(self):
        config = copy.deepcopy(self.config)
        config['host'] = '-oProxyCommand=bad'
        with self.assertRaises(ValueError):
            remote.ssh_args(config, 'true')


if __name__ == '__main__':
    unittest.main()
