"""Run the installer in a fresh fixture with no evidence directory or real daemon."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh'), 'Requires a POSIX shell; also run on the target')
class FirstInstallation(unittest.TestCase):
    def test_fresh_install_creates_readiness_log_directory(self):
        with tempfile.TemporaryDirectory(prefix='qb-docker-installer-') as folder:
            root = Path(folder)
            for name in ('offline/runtime', 'runtime/docker', 'config', 'target', 'fake-bin'):
                (root/name).mkdir(parents=True)
            (root/'.owner').write_text('qb560d-training-docker-v1\n')
            (root/'offline/runtime/buildx-v0.38.1.linux-arm64').write_text('fixture')
            (root/'config/qb560d-docker-demo.service').write_text('fixture unit')
            (root/'offline/runtime.sha256').write_text('fixture checksums')
            scripts = {'fake-bin/id': 'echo 0', 'fake-bin/uname': 'echo aarch64',
                       'fake-bin/sha256sum': 'exit 0', 'fake-bin/systemctl': 'exit 0',
                       'runtime/docker/dockerd': 'exit 0', 'target/docker.sh': 'echo fixture-docker-ready'}
            for name, body in scripts.items():
                path = root/name
                path.write_text('#!/bin/sh\n'+body+'\n')
                path.chmod(0o755)
            source = (Path(__file__).resolve().parents[1]/'target/install.sh').read_text()
            source = source.replace('root=/opt/qb560d-docker-demo', 'root='+shlex.quote(str(root)))
            source = source.replace('unit=/etc/systemd/system/qb560d-docker-demo.service', 'unit='+shlex.quote(str(root/'test.service')))
            script = root/'install.sh'
            script.write_text(source)
            result = subprocess.run(['sh', str(script)], env=dict(os.environ, PATH=str(root/'fake-bin')+os.pathsep+os.environ['PATH']), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('RESULT: ENGINE_READY', result.stdout)
            self.assertEqual((root/'evidence/docker-info.txt').read_text().strip(), 'fixture-docker-ready')


if __name__ == '__main__':
    unittest.main()
