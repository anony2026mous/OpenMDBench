from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import zipfile
import repair_export as r


class Tests(unittest.TestCase):
    def test_dependency_inventory_without_pip(self):
        rows = r.packages([SimpleNamespace(metadata={'Name': 'PyYAML'}, version='6.0.3'),
                           SimpleNamespace(metadata={'Name': 'numpy'}, version='2.2.6')])
        self.assertEqual([x['name'] for x in rows], ['numpy', 'PyYAML'])

    def test_conflicting_versions_rejected(self):
        with self.assertRaises(ValueError):
            r.packages([SimpleNamespace(metadata={'Name': 'a'}, version='1'),
                        SimpleNamespace(metadata={'Name': 'A'}, version='2')])

    def test_zip_verifies_each_member_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            f = p / 'data.txt'
            f.write_text('test', encoding='utf-8')
            hashes = {'data.txt': r.sha_file(f)}
            r.write(p / 'DELIVERY_MANIFEST.json', {'files': hashes})
            with zipfile.ZipFile(p / 'good.zip', 'w') as z:
                z.write(f, 'data.txt')
                z.write(p / 'DELIVERY_MANIFEST.json', 'DELIVERY_MANIFEST.json')
            r.verify_zip(p / 'good.zip', hashes)
            with zipfile.ZipFile(p / 'bad.zip', 'w') as z:
                z.writestr('data.txt', 'altered')
                z.write(p / 'DELIVERY_MANIFEST.json', 'DELIVERY_MANIFEST.json')
            with self.assertRaises(ValueError):
                r.verify_zip(p / 'bad.zip', hashes)


if __name__ == '__main__':
    unittest.main()
