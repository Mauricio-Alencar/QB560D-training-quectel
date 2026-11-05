"""Verify portable preparation refuses damaged archives and unsafe destinations."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

HELPER = Path(__file__).with_name('prepare_portable_python.ps1')


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell'), 'Windows PowerShell required')
class PortableBoundaries(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qb-python-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'tools/python38'
        self.source.mkdir(parents=True)
        self.package = self.source / 'python.3.8.10.nupkg'

    def fixture(self, name='tools/python.exe', payload=b'fixture'):
        with zipfile.ZipFile(self.package, 'w') as archive:
            archive.writestr(name, payload)
        digest = hashlib.sha256(self.package.read_bytes()).hexdigest()
        lock = {'version': '3.8.10', 'archive': self.package.name,
                'files': {self.package.name: {'bytes': self.package.stat().st_size, 'sha256': digest}}}
        (self.source / 'python38.lock.json').write_text(json.dumps(lock), encoding='utf-8')
        return digest

    def run_helper(self, *args):
        env = {key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'}
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(HELPER), '-Version', '3.8',
                                 '-TrainingRoot', str(self.root), *args],
                                cwd=self.root, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60)
        return result.returncode, result.stdout.decode(errors='replace')

    def test_check_only_verifies_without_creating_runtime(self):
        self.fixture()
        code, output = self.run_helper('-CheckOnly')
        self.assertEqual(code, 0, output)
        self.assertFalse((self.root / '.build').exists())

    def test_changed_package_is_refused_before_extraction(self):
        self.fixture()
        with self.package.open('ab') as stream:
            stream.write(b'changed')
        code, output = self.run_helper()
        self.assertNotEqual(code, 0, output)
        self.assertIn('hash/size mismatch', output)
        self.assertFalse((self.root / '.build').exists())

    def test_archive_member_cannot_escape_runtime(self):
        self.fixture('tools/../../escaped.txt')
        code, output = self.run_helper()
        self.assertNotEqual(code, 0, output)
        self.assertIn('Unsafe member', output)
        self.assertFalse((self.root / 'escaped.txt').exists())
        self.assertFalse((self.root / '.build/escaped.txt').exists())

    def test_existing_foreign_directory_is_preserved(self):
        self.fixture()
        runtime = self.root / '.build/portable-python38'
        runtime.mkdir(parents=True)
        existing = runtime / 'keep.txt'
        existing.write_bytes(b'owned by someone else')
        code, output = self.run_helper()
        self.assertNotEqual(code, 0, output)
        self.assertIn('no ownership marker', output)
        self.assertEqual(existing.read_bytes(), b'owned by someone else')

    def test_changed_runtime_member_is_refused_and_preserved(self):
        digest = self.fixture()
        runtime = self.root / '.build/portable-python38'
        runtime.mkdir(parents=True)
        (runtime / '.portable-python.json').write_text(json.dumps({'package_sha256': digest}))
        executable = runtime / 'python.exe'
        executable.write_bytes(b'changed existing runtime')
        code, output = self.run_helper()
        self.assertNotEqual(code, 0, output)
        self.assertIn('member changed', output)
        self.assertEqual(executable.read_bytes(), b'changed existing runtime')


if __name__ == '__main__':
    unittest.main()
