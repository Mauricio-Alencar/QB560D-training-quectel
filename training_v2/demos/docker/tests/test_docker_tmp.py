"""Exercise Docker's missing temporary directory without touching a real daemon."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh'), 'Requires POSIX; run on the target')
class TemporaryDirectoryRecovery(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qb-docker-tmp-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ('target', 'offline/images', 'runtime/docker', 'config'):
            (self.root/name).mkdir(parents=True)
        (self.root/'.owner').write_text('qb560d-training-docker-v1\n')
        self.source = Path(__file__).resolve().parents[1]/'target'

    def script(self, name):
        content = (self.source/name).read_text().replace(
            'root=/opt/qb560d-docker-demo', 'root='+shlex.quote(str(self.root)))
        path = self.root/'target'/name
        path.write_text(content)
        return path

    def execute(self, script, *args):
        return subprocess.run(['sh', str(script), *args], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=20)

    def test_load_recovers_missing_tmp_with_an_already_running_engine(self):
        archive = self.root/'offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz'
        archive.write_bytes(b'fixture image')
        (self.root/'offline/image.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  offline/images/'+archive.name+'\n')
        (self.root/'offline/image.lock.json').write_text(json.dumps({'image_id': 'sha256:fixture'}))
        cli = self.root/'target/docker.sh'
        cli.write_text('''#!/bin/sh
root='''+shlex.quote(str(self.root))+'''
case "$1" in
 load) [ -d "$root/data/tmp" ] || { echo 'missing daemon import tmp'; exit 1; };;
 image) case "$*" in *Architecture*) echo linux/arm64;; *) echo sha256:fixture;; esac;;
 *) exit 1;;
esac
''')
        script = self.script('demo.sh')
        for attempt in range(2):
            self.assertFalse((self.root/'data/tmp').exists())
            result = self.execute(script, 'load')
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue((self.root/'data/tmp').is_dir())
            (self.root/'data/tmp').rmdir()

    def test_daemon_creates_tmp_before_starting_dockerd(self):
        daemon = self.root/'runtime/docker/dockerd'
        daemon.write_text('#!/bin/sh\ntest -d '+shlex.quote(str(self.root/'data/tmp'))+' || exit 42\necho DAEMON_TMP_READY\n')
        daemon.chmod(0o755)
        result = self.execute(self.script('daemon.sh'))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('DAEMON_TMP_READY', result.stdout)

    def test_foreign_directory_is_refused_before_creating_data(self):
        (self.root/'.owner').write_text('foreign\n')
        result = self.execute(self.script('daemon.sh'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root/'data').exists())

    def test_install_restarts_empty_daemon_after_data_tree_was_deleted(self):
        fake = self.root/'fake-bin'
        fake.mkdir()
        (self.root/'offline/runtime').mkdir()
        (self.root/'offline/runtime/buildx-v0.38.1.linux-arm64').write_text('fixture')
        (self.root/'config/qb560d-docker-demo.service').write_text('fixture unit')
        scripts = {'id': 'echo 0', 'uname': 'echo aarch64', 'sha256sum': 'exit 0',
                   'systemctl': 'echo "$*" >> '+shlex.quote(str(self.root/'service-actions'))}
        for name, body in scripts.items():
            path = fake/name
            path.write_text('#!/bin/sh\n'+body+'\n')
            path.chmod(0o755)
        (self.root/'runtime/docker/dockerd').write_text('#!/bin/sh\nexit 0\n')
        (self.root/'runtime/docker/dockerd').chmod(0o755)
        (self.root/'target/docker.sh').write_text('#!/bin/sh\n[ "$1" = ps ] && exit 0\necho fixture-docker-ready\n')
        script = self.script('install.sh')
        script.write_text(script.read_text().replace('unit=/etc/systemd/system/qb560d-docker-demo.service',
                                                    'unit='+shlex.quote(str(self.root/'fixture.service'))))
        result = subprocess.run(['sh', str(script)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=20, env=dict(os.environ, PATH=str(fake)+os.pathsep+os.environ['PATH']))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('restart qb560d-docker-demo.service', (self.root/'service-actions').read_text())
        self.assertTrue((self.root/'data/tmp').is_dir())
        # A failed CLI must not look like an empty container list.
        (self.root/'service-actions').write_text('')
        (self.root/'target/docker.sh').write_text('#!/bin/sh\n[ "$1" = ps ] && exit 17\necho fixture-docker-ready\n')
        result = subprocess.run(['sh', str(script)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=20, env=dict(os.environ, PATH=str(fake)+os.pathsep+os.environ['PATH']))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('restart qb560d-docker-demo.service', (self.root/'service-actions').read_text())


if __name__ == '__main__':
    unittest.main()
