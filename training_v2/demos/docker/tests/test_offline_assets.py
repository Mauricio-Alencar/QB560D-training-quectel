"""Reject incomplete downloads before attempting an ADB connection."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'host'))
from stage import verify_asset


class OfflineAssets(unittest.TestCase):
    def test_complete_bytes_pass_and_truncated_copy_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'image.tar.gz'
            data = b'reviewed offline archive'
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            verify_asset(path, digest, len(data), 'image')
            path.write_bytes(data[:-1])
            with self.assertRaisesRegex(ValueError, 'expected 24 bytes, found 23'):
                verify_asset(path, digest, len(data), 'image')

    def test_lfs_pointer_has_a_specific_recovery_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'image.tar.gz'
            path.write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 24\n')
            with self.assertRaisesRegex(ValueError, 'Git LFS pointer'):
                verify_asset(path, '0'*64, 24, 'image')

    def test_same_length_corruption_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'runtime.tgz'
            path.write_bytes(b'changed!')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_asset(path, hashlib.sha256(b'reviewed').hexdigest(), 8, 'runtime')


if __name__ == '__main__':
    unittest.main()
