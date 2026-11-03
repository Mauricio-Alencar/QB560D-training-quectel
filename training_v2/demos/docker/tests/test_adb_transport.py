import os
from pathlib import Path
import sys
import subprocess
import tempfile
import shutil
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'host'))
import adb_transport
from adb_transport import AdbSession, AuthenticationError

FAKE = Path(__file__).with_name('fake_adb.py')


class LoginProtocol(unittest.TestCase):
    def session(self, **kwargs):
        return AdbSession(base=[sys.executable, str(FAKE)], password='dummy-test-password', **kwargs)

    def test_login_and_clean_command(self):
        with self.session() as connection:
            result = connection.run('hello')
            self.assertTrue(connection.auth['login_prompt'])
            self.assertTrue(connection.auth['password_prompt'])
            self.assertEqual(connection.auth['uid'], 0)
            self.assertEqual(result.stdout.strip(), b'RESULT:hello')

    def test_remote_nonzero_is_preserved(self):
        with self.session() as connection:
            self.assertEqual(connection.run('CASE_EXIT_7').returncode, 7)

    def test_commands_with_unicode_and_long_lines(self):
        value = 'ECHO:' + ('ação ' * 2500)
        with self.session() as connection:
            self.assertEqual(connection.run(value).stdout.decode().strip(), 'RESULT:' + value.strip())

    def test_output_prompt_words_do_not_trigger_another_login(self):
        with self.session() as connection:
            self.assertEqual(connection.run('CASE_PROMPTS_IN_OUTPUT').stdout.strip(), b'login:\nPassword:')

    def test_accidental_secret_output_is_redacted(self):
        with self.session() as connection:
            output = connection.run('CASE_SECRET_OUTPUT').stdout
            self.assertNotIn(b'dummy-test-password', output)
            self.assertIn(b'[REDACTED]', output)

    def test_wrong_password_prevents_transfer(self):
        connection = AdbSession(base=[sys.executable, str(FAKE)], password='incorrect-dummy')
        with mock.patch('adb_transport.subprocess.run') as transfer:
            with self.assertRaises(AuthenticationError) as raised:
                connection.transfer('push', 'source', '/tmp/destination')
            transfer.assert_not_called()
        self.assertNotIn('incorrect-dummy', str(raised.exception))

    def test_nonroot_shell_is_refused(self):
        with mock.patch.dict(os.environ, {'FAKE_ADB_MODE':'nonroot'}):
            with self.assertRaises(AuthenticationError):
                self.session().connect()

    def test_direct_root_shell_needs_no_password(self):
        with mock.patch.dict(os.environ, {'FAKE_ADB_MODE':'direct'}):
            provider = mock.Mock(side_effect=AssertionError('Password must not be requested'))
            with AdbSession(base=[sys.executable, str(FAKE)], password_provider=provider) as connection:
                self.assertEqual(connection.run('direct').returncode, 0)
                provider.assert_not_called()

    def test_timeout_terminates_the_local_adb_session(self):
        with self.session() as connection:
            with self.assertRaises(TimeoutError):
                connection.run('CASE_TIMEOUT', timeout=0.05)
            self.assertIsNone(connection._process)


class DeviceSelection(unittest.TestCase):
    listing = 'List of devices attached\n? device product:qcm6490-Ubuntu transport_id:1\n? device product:qcm6490-Ubuntu transport_id:2\n'

    @mock.patch('adb_transport.resolve_adb', return_value='adb')
    @mock.patch('adb_transport.subprocess.check_output', return_value=listing)
    def test_repeated_serial_requires_explicit_transport(self, *_):
        with self.assertRaises(ValueError):
            adb_transport.select_device(serial='?')

    @mock.patch('adb_transport.resolve_adb', return_value='adb')
    @mock.patch('adb_transport.subprocess.check_output', return_value=listing)
    def test_explicit_transport_selects_the_intended_box(self, *_):
        base, identity = adb_transport.select_device(transport_id='2')
        self.assertEqual(base, ['adb','-t','2'])
        self.assertEqual(identity['transport_id'], '2')


@unittest.skipUnless(os.name == 'nt', 'Windows path workaround')
class WindowsTransfers(unittest.TestCase):
    def connection(self):
        return AdbSession(base=[sys.executable, str(FAKE)], password='dummy-test-password')

    def test_pull_directory_to_long_unicode_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / ('Pasta com acentos ação ' * 5).strip()
            destination = parent / ('subpasta ' * 12).strip() / 'target'
            def adb_pull(args, **kwargs):
                staged = Path(args[-1]);staged.mkdir();(staged/'result.json').write_text('{"ok":true}')
                self.assertLess(len(str(staged)), 200)
                return subprocess.CompletedProcess(args,0)
            try:
                with self.connection() as connection, mock.patch('adb_transport.subprocess.run',side_effect=adb_pull):
                    connection.transfer('pull','/opt/demo/evidence',destination)
                self.assertEqual((adb_transport.local_path(destination)/'result.json').read_text(),'{"ok":true}')
            finally:
                if adb_transport.local_path(parent).exists():
                    assert parent.parent == Path(temporary)
                    shutil.rmtree(adb_transport.local_path(parent))

    def test_pull_keeps_adb_existing_directory_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination=Path(temporary)
            def adb_pull(args, **kwargs):
                Path(args[-1]).write_bytes(b'report')
                return subprocess.CompletedProcess(args,0)
            with self.connection() as connection, mock.patch('adb_transport.subprocess.run',side_effect=adb_pull):
                connection.transfer('pull','/opt/demo/report.json',destination)
            self.assertEqual((destination/'report.json').read_bytes(),b'report')

    def test_push_preserves_basename_and_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'pasta com acentos ação';source.mkdir();(source/'file.txt').write_text('payload')
            def adb_push(args, **kwargs):
                staged=Path(args[-2])
                self.assertEqual(staged.name,source.name)
                self.assertEqual((staged/'file.txt').read_text(),'payload')
                self.assertEqual(args[-1],'/opt/demo/')
                return subprocess.CompletedProcess(args,0)
            with self.connection() as connection, mock.patch('adb_transport.subprocess.run',side_effect=adb_push):
                connection.transfer('push',source,'/opt/demo/')


if __name__ == '__main__':
    unittest.main()
