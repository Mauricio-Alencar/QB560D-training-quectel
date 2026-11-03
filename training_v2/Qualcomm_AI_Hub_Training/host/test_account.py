"""Offline checks for credential handling. No real token or API request is used."""
import configparser
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import account


class AccountTests(unittest.TestCase):
    def test_copied_portal_command_is_parsed_without_execution(self):
        self.assertEqual(account.token_from_paste('qai-hub configure --api_token fixture-value'), 'fixture-value')
        self.assertEqual(account.token_from_paste('qai-hub configure --api_token=fixture-value'), 'fixture-value')
        with self.assertRaises(ValueError):
            account.token_from_paste('qai-hub configure --api_token fixture-value; unwanted-command')

    def invoke(self, path, failure=False):
        output = io.StringIO()
        with patch('sys.argv', ['account.py', 'configure']), \
             patch('qai_hub.api_utils.get_config_path', return_value=str(path)), \
             patch('getpass.getpass', return_value='offline-fixture-token'), \
             patch('qai_hub.Client') as client, redirect_stdout(output):
            if failure:
                client.return_value.get_devices.side_effect = RuntimeError('offline-fixture-token')
            else:
                client.return_value.get_devices.return_value = [object()]
            status = account.main()
        return status, output.getvalue()

    def test_success_saves_without_printing_token(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'client.ini'
            status, output = self.invoke(path)
            self.assertEqual(status, 0)
            self.assertIn('ACCOUNT_READY', output)
            self.assertNotIn('offline-fixture-token', output)
            cfg = configparser.ConfigParser();cfg.read(path)
            self.assertEqual(cfg['api']['api_token'], 'offline-fixture-token')
            self.assertEqual(cfg['api']['api_url'], 'https://workbench.aihub.qualcomm.com')

    def test_failed_validation_does_not_save_or_print_token(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'client.ini'
            status, output = self.invoke(path, failure=True)
            self.assertEqual(status, 2)
            self.assertFalse(path.exists())
            self.assertNotIn('offline-fixture-token', output)

    def test_existing_config_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'client.ini';path.write_text('existing',encoding='utf-8')
            status, _ = self.invoke(path)
            self.assertEqual(status, 0)
            self.assertEqual(path.read_text(encoding='utf-8'), 'existing')

    def test_project_config_refused(self):
        path = Path(account.__file__).resolve().parents[1]/'do-not-create.ini'
        with self.assertRaises(SystemExit):self.invoke(path)
        self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
