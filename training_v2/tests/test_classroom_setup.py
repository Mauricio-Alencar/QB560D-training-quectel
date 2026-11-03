"""Classroom path guards and safe reuse of the private Pillow wheel."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from target_layout import DEFAULT_REMOTE, validate_remote


class TargetPaths(unittest.TestCase):
    def test_persistent_and_transient_labs_are_explicit(self):
        self.assertEqual(validate_remote(DEFAULT_REMOTE),'/opt/qb560d-training-payload')
        self.assertEqual(validate_remote('/tmp/qb560d-training'),'/tmp/qb560d-training')

    def test_other_roots_and_traversal_are_refused(self):
        for path in ('/opt','/','/opt/qb560d-training-payload/../other','relative','/tmp/unrelated'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_remote(path)


class PillowPreparation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qb-pillow-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root/'target').mkdir()
        (self.root/'wheelhouse').mkdir()
        self.script = self.root/'target/unpack_pillow.py'
        self.script.write_bytes((ROOT/'target/unpack_pillow.py').read_bytes())
        name='pillow-10.4.0-cp38-cp38-manylinux_2_17_aarch64.whl'
        wheel=self.root/'wheelhouse'/name
        with zipfile.ZipFile(wheel,'w') as archive:
            archive.writestr('PIL/example.txt','reviewed wheel bytes')
        self.lock=self.root/'wheelhouse/wheels.lock.json'
        self.lock.write_text(json.dumps({name:{'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}}))

    def prepare(self):
        with patch('platform.machine',return_value='aarch64'), patch.object(sys,'version_info',(3,8,10)), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(self.script),run_name='__main__')

    def test_first_prepare_and_repeat_preserve_reviewed_bytes(self):
        self.prepare()
        current=self.root/'.python-deps/PIL/example.txt'
        before=current.read_bytes()
        self.prepare()
        self.assertEqual(current.read_bytes(),before)

    def test_existing_modified_dependency_is_refused_and_preserved(self):
        self.prepare()
        current=self.root/'.python-deps/PIL/example.txt'
        current.write_text('user change')
        with self.assertRaisesRegex(SystemExit,'differs or is incomplete'):
            self.prepare()
        self.assertEqual(current.read_text(),'user change')

    def test_bad_wheel_hash_does_not_create_dependency_tree(self):
        lock=json.loads(self.lock.read_text())
        next(iter(lock.values()))['sha256']='0'*64
        self.lock.write_text(json.dumps(lock))
        with self.assertRaisesRegex(SystemExit,'Wheel hash mismatch'):
            self.prepare()
        self.assertFalse((self.root/'.python-deps').exists())


if __name__=='__main__':
    unittest.main()
