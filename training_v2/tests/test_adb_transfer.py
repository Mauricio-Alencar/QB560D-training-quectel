"""Exercise real local copies beyond MAX_PATH with a simulated ADB subprocess."""
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from adb_transport import local_path,transfer_files
from provision_session import Session


@unittest.skipUnless(os.name=='nt','Windows path regression')
class WindowsTransfers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='qb-transfer-test-')
        self.root=Path(self.temp.name)
        def cleanup():
            if self.root.exists():shutil.rmtree(local_path(self.root))
            self.temp.cleanup()
        self.addCleanup(cleanup)
        self.deep=self.root/('training-'+'x'*70)/('evidence-'+'y'*70)/('verification-'+'z'*70)
        self.assertGreater(len(str(self.deep)),260)

    def test_pull_to_existing_long_directory_preserves_run_folder(self):
        local_path(self.deep).mkdir(parents=True)
        def adb(argv,**kwargs):
            staged=Path(argv[-1]);self.assertLess(len(str(staged)),260)
            (staged/'htp/Result_4').mkdir(parents=True)
            (staged/'htp/Result_4/class_logits.raw').write_bytes(b'reviewed tensor')
            return subprocess.CompletedProcess(argv,0)
        with patch('adb_transport.subprocess.run',side_effect=adb):
            transfer_files(['adb','-t','4'],'pull','/opt/demo/results/run-001',self.deep)
        self.assertEqual((local_path(self.deep)/'run-001/htp/Result_4/class_logits.raw').read_bytes(),b'reviewed tensor')

    def test_failed_pull_does_not_copy_partial_output_or_change_existing_data(self):
        local_path(self.deep).mkdir(parents=True)
        existing=local_path(self.deep)/'keep.txt';existing.write_bytes(b'existing')
        def adb(argv,**kwargs):
            staged=Path(argv[-1]);staged.mkdir();(staged/'partial').write_bytes(b'not accepted')
            return subprocess.CompletedProcess(argv,1)
        with patch('adb_transport.subprocess.run',side_effect=adb):
            result=transfer_files(['adb'],'pull','/opt/demo/results/run-002',self.deep,check=False)
        self.assertEqual(result.returncode,1)
        self.assertEqual(existing.read_bytes(),b'existing')
        self.assertFalse((local_path(self.deep)/'run-002').exists())

    def test_push_of_long_source_directory_passes_unchanged_bytes_through_short_path(self):
        local_path(self.deep).mkdir(parents=True)
        (local_path(self.deep)/'input.raw').write_bytes(b'reviewed input')
        def adb(argv,**kwargs):
            staged=Path(argv[-2]);self.assertLess(len(str(staged)),260)
            self.assertEqual((staged/'input.raw').read_bytes(),b'reviewed input')
            self.assertEqual(argv[-1],'/opt/demo/input')
            return subprocess.CompletedProcess(argv,0)
        with patch('adb_transport.subprocess.run',side_effect=adb):
            transfer_files(['adb'],'push',self.deep,'/opt/demo/input')
        self.assertEqual((local_path(self.deep)/'input.raw').read_bytes(),b'reviewed input')

    def test_provisioning_writes_long_profile_log_paths(self):
        session=Session.__new__(Session)
        session.password=None
        session._send=lambda value:None
        session._until=lambda pattern,timeout:b'__BEGIN_fixed__\nprofile output\n__END_fixed__=0\n'
        with patch('provision_session.uuid.uuid4',return_value=SimpleNamespace(hex='fixed')):
            output,status=session.run('true',self.deep/'hand_landmark_detector','profile-hand_landmark_detector')
        self.assertEqual(status,0)
        self.assertEqual((local_path(self.deep)/'hand_landmark_detector/profile-hand_landmark_detector.log').read_text(encoding='utf-8'),output)


if __name__=='__main__':unittest.main()
