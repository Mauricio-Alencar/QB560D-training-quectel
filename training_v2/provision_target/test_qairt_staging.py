"""Exercise the archive layout and ownership guards without touching a device."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtimes/qairt_2_51'))
import update_qairt as q


class LocalAdapter:
    def __init__(self):
        self.commands = []
        self.members = []

    def python(self, code, evidence, label):
        # Target code uses Linux paths; normalize realpath separators in the
        # Windows fixture while retaining actual resolution/containment checks.
        realpath = os.path.realpath
        with contextlib.redirect_stdout(io.StringIO()) as output, patch('os.path.realpath', side_effect=lambda path, **kw: Path(realpath(path, **kw)).as_posix()):
            exec(compile(code, label, 'exec'), {})
        return output.getvalue()

    def shell(self, command, evidence, label):
        self.commands.append(command)

    def push(self, source, destination):
        with tarfile.open(source) as archive:
            self.members = archive.getnames()
        shutil.copyfile(source, destination)


class RuntimeStaging(unittest.TestCase):
    def fixture(self, remote, nested=False):
        root = remote/'payload' if nested else remote
        names = (['bin/'+name for name in q.BIN_NAMES] +
                 ['lib/'+name for name in q.LIB_NAMES] +
                 ['dsp/'+name for name in q.DSP_NAMES] +
                 ['model/mobilenet_v2.dlc', 'input/dog.raw', 'input/input_list.txt',
                  'probe_runtime.py', 'cleanup_target.py'])
        for name in names:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture '+name.encode())
        (root/'ownership.json').write_text(json.dumps(dict(package='update_QIART', version=q.VERSION, remote=remote.as_posix())))
        rows = [dict(path=path.relative_to(root).as_posix(), sha256=q.sha(path)) for path in root.rglob('*') if path.is_file()]
        (root/'files.json').write_text(json.dumps(rows))
        return root

    def test_verified_flat_runtime_is_reused_without_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = Path(folder)/'runtime'
            self.fixture(remote)
            adapter = LocalAdapter()
            with patch.object(q, 'stage') as stage:
                q.ensure_staged(adapter, remote.as_posix(), Path(folder)/'evidence')
                stage.assert_not_called()
            self.assertIn('qnn-net-run', adapter.commands[0])

    def test_unknown_directory_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = Path(folder)/'runtime'
            remote.mkdir()
            (remote/'keep.txt').write_text('existing data')
            with self.assertRaisesRegex(RuntimeError, 'no recognized ownership'):
                q.ensure_staged(LocalAdapter(), remote.as_posix(), Path(folder))
            self.assertEqual((remote/'keep.txt').read_text(), 'existing data')

    def test_modified_file_and_incomplete_manifest_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = Path(folder)/'runtime'
            root = self.fixture(remote)
            (root/'input/dog.raw').write_bytes(b'changed')
            with self.assertRaisesRegex(AssertionError, 'Target checksum mismatch'):
                q.require_owner(LocalAdapter(), remote.as_posix(), Path(folder))
            (root/'files.json').write_text('[]')
            with self.assertRaisesRegex(AssertionError, 'Incomplete QAIRT manifest'):
                q.require_owner(LocalAdapter(), remote.as_posix(), Path(folder))

    def test_nested_runtime_refuses_conflicting_root_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = Path(folder)/'runtime'
            self.fixture(remote, nested=True)
            (remote/'bin').mkdir()
            with self.assertRaisesRegex(AssertionError, 'Conflicting QAIRT path'):
                q.expose_payload(LocalAdapter(), remote.as_posix(), Path(folder))
            self.assertTrue((remote/'bin').is_dir())
            self.assertFalse((remote/'lib').exists())

    def test_archive_retains_one_payload_level_and_exact_file_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload = self.fixture(root/'source', nested=True)
            remote = root/'destination'
            remote.mkdir()
            adapter = LocalAdapter()
            q.push_payload(adapter, payload, remote.as_posix(), root/'evidence')
            self.assertTrue(all(name.startswith('payload/') and not name.startswith('payload/payload/') for name in adapter.members))
            self.assertFalse((remote/'.qairt-payload.tar').exists())
            q.require_owner(adapter, (root/'source').as_posix(), root/'evidence', payload_root=payload.as_posix())
            for source in payload.rglob('*'):
                if source.is_file():
                    self.assertEqual((remote/'payload'/source.relative_to(payload)).read_bytes(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
