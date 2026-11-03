"""Local checks of installer boundaries; never connects to ADB or installs software."""
import contextlib,copy,io,json,os,stat,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import provision
import target_install
class Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Synthetic baseline: the tests must also run in a fresh student ZIP,
        # without a saved machine inventory or an ADB connection.
        (provision.ROOT/'evidence').mkdir(exist_ok=True)
        cls.inv=dict(os_release={'ID':'ubuntu','VERSION_ID':'20.04'},
            identity={'uid':0,'architecture':'aarch64','glibc':['glibc','2.31'],
                      'python':'3.8.10','kernel':'5.4.219-perf'},
            build_files={'/etc/build_version':'synthetic-test-bsp'},
            ai_libraries=[{'path':'/usr/lib/libSNPE.so','sha256':'1'*64}],
            tools={name:{'path':'/usr/bin/'+name} for name in
                   ('python3','sh','base64','tar','gzip','gcc','make','systemctl','sha256sum','findmnt')},
            system_libraries_for_ss={'libmnl.so.0':['/lib/libmnl.so.0']},
            compiler_headers={name:True for name in
                              ('/usr/include/stdio.h','/usr/include/pthread.h','/usr/include/sys/socket.h')},
            mounts={'/opt':{'output':'/dev/example /opt ext4 rw'}})
    def test_plan_does_not_connect_to_target(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='plan-test-') as folder:
            self.assertIn(provision.ROOT.resolve(),Path(folder).resolve().parents)
            inventory=Path(folder)/'inventory.json';inventory.write_text(json.dumps(self.inv))
            with patch.object(provision,'Session',side_effect=AssertionError('Unexpected ADB connection')),contextlib.redirect_stdout(io.StringIO()):
                result=provision.plan(inventory,Path(folder)/'plan.json')
            self.assertFalse(result['installation_executed']);self.assertEqual(result['status'],'READY_TO_REVIEW')
    def test_missing_library_blocks_plan(self):
        changed=copy.deepcopy(self.inv);changed['system_libraries_for_ss']['libmnl.so.0']=[]
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='plan-test-') as folder:
            self.assertIn(provision.ROOT.resolve(),Path(folder).resolve().parents)
            inventory=Path(folder)/'inventory.json';inventory.write_text(json.dumps(changed))
            with contextlib.redirect_stdout(io.StringIO()):result=provision.plan(inventory,Path(folder)/'plan.json')
            self.assertEqual(result['status'],'BLOCKED');self.assertTrue(any('libmnl' in b for b in result['blockers']))
    def test_wrong_abi_blocks_plan(self):
        changed=copy.deepcopy(self.inv);changed['identity']['architecture']='x86_64'
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='plan-test-') as folder:
            self.assertIn(provision.ROOT.resolve(),Path(folder).resolve().parents)
            inventory=Path(folder)/'inventory.json';inventory.write_text(json.dumps(changed))
            with contextlib.redirect_stdout(io.StringIO()):result=provision.plan(inventory,Path(folder)/'plan.json')
            self.assertEqual(result['status'],'BLOCKED')
    def test_vendor_change_changes_firmware_fingerprint(self):
        changed=copy.deepcopy(self.inv);next(r for r in changed['ai_libraries'] if r.get('sha256'))['sha256']='0'*64
        self.assertNotEqual(provision.fingerprint(self.inv),provision.fingerprint(changed))
    def test_reboot_and_clock_do_not_change_firmware_fingerprint(self):
        changed=copy.deepcopy(self.inv);changed['identity']['boot_id']='another-boot';changed['at_target_utc']='2026-11-01T12:00:00+00:00'
        self.assertEqual(provision.fingerprint(self.inv),provision.fingerprint(changed))
    def test_changed_bundle_blocks_apply(self):
        with self.assertRaisesRegex(AssertionError,'Bundle changed'):provision.check_bundle({'bundle_manifest_sha256':'0'*64})
    def test_wheel_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='archive-test-') as folder:
            root=Path(folder).resolve();self.assertIn(provision.ROOT.resolve(),root.parents);dest=root/'deps';dest.mkdir();archive=root/'bad.whl'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside.txt','unsafe')
            with self.assertRaises(AssertionError):target_install.extract_wheel(archive,dest)
            self.assertFalse((root/'outside.txt').exists())
    def test_wheel_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='archive-test-') as folder:
            root=Path(folder).resolve();self.assertIn(provision.ROOT.resolve(),root.parents);dest=root/'deps';dest.mkdir();archive=root/'bad.whl'
            info=zipfile.ZipInfo('module/link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(archive,'w') as z:z.writestr(info,'../../outside')
            with self.assertRaisesRegex(AssertionError,'symlink'):target_install.extract_wheel(archive,dest)
    def test_real_wheels_extract_to_private_directory(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='archive-test-') as folder:
            dest=Path(folder).resolve();self.assertIn(provision.ROOT.resolve(),dest.parents)
            numpy=next((provision.ROOT/'cache').glob('numpy-1.24.4-*.whl'))
            pillow=next((provision.REPO/'wheelhouse').glob('pillow-10.4.0-*.whl'))
            target_install.extract_wheel(numpy,dest);target_install.extract_wheel(pillow,dest)
            self.assertTrue((dest/'numpy/__init__.py').is_file());self.assertTrue((dest/'PIL/Image.py').is_file())
    def test_ss_deb_extracts_only_ss_and_copyright(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='archive-test-') as folder:
            root=Path(folder).resolve();self.assertIn(provision.ROOT.resolve(),root.parents)
            with patch.object(target_install,'WORK',root),patch.object(target_install.subprocess,'check_output',return_value='libc.so.6 => /lib/libc.so.6'),patch.object(target_install,'run'),contextlib.redirect_stdout(io.StringIO()):
                target_install.ss_binary(provision.ROOT/'cache/iproute2_5.5.0-1ubuntu1_arm64.deb')
            self.assertEqual({p.name for p in (root/'tools/ss-5.5.0').iterdir()},{'ss','copyright'})
    def test_future_source_times_shift_without_changing_content_or_relative_order(self):
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='clock-test-') as folder:
            root=Path(folder).resolve();source=root/'build/iperf-3.22';source.mkdir(parents=True)
            earlier=source/'Makefile.am';later=source/'Makefile.in'
            earlier.write_bytes(b'source');later.write_bytes(b'generated')
            os.utime(earlier,ns=(2_000_000_000_000_000_000,2_000_000_000_000_000_000))
            os.utime(later,ns=(2_000_000_010_000_000_000,2_000_000_010_000_000_000))
            before={p:p.stat().st_mtime_ns for p in (earlier,later)}
            now=1_700_000_000_000_000_000
            with patch.object(target_install,'WORK',root),patch.object(target_install.time,'time_ns',return_value=now),contextlib.redirect_stdout(io.StringIO()):
                target_install.normalize_build_times(source)
            self.assertEqual(earlier.read_bytes(),b'source');self.assertEqual(later.read_bytes(),b'generated')
            self.assertEqual(later.stat().st_mtime_ns-earlier.stat().st_mtime_ns,before[later]-before[earlier])
            self.assertTrue(all(p.stat().st_mtime_ns<=now-60_000_000_000 for p in (source,earlier,later)))
    def test_build_timestamp_fix_refuses_outside_tree(self):
        with self.assertRaises(AssertionError):target_install.normalize_build_times(Path(__file__).resolve().parent)
    def test_verify_stops_with_recovery_message_when_installation_is_incomplete(self):
        class IncompleteSession:
            base=[];identity='test'
            def run(self,*args):return ('MISSING: /opt/qb560d-workshop/env.sh\n',1)
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'cache',prefix='verify-test-') as folder:
            with self.assertRaisesRegex(RuntimeError,'Installation incomplete.*MISSING'):
                provision.verify(IncompleteSession(),Path(folder))
    def test_verify_gesture_paths_fit_windows_and_are_unique_between_runs(self):
        session=SimpleNamespace(base=[],identity='test',run=Mock(return_value=('',0)))
        q=SimpleNamespace(test=Mock())
        h=SimpleNamespace(SAMPLES={'closed_fist.jpg':'Closed_Fist'},ROOT=provision.REPO/'demos/hand_gesture',run=Mock(return_value={'passed':True}))
        with tempfile.TemporaryDirectory(dir=provision.ROOT/'evidence',prefix='20261101T164246206935Z-',suffix='-apply') as folder:
            evidence=Path(folder)/'verification'
            with patch.object(provision,'modules',return_value=(q,h)):
                provision.verify(session,evidence);provision.verify(session,evidence)
            paths=[call.args[4] for call in h.run.call_args_list]
            self.assertNotEqual(paths[0],paths[1])
            for path in paths:
                self.assertLess(len(str(path/'canned_gesture_classifier/profile-canned_gesture_classifier.log')),260)
if __name__=='__main__':unittest.main(verbosity=2)
