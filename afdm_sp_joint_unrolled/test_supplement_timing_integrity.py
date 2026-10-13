"""File-integrity and output-budget contracts; no receiver calls."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from afdm_sp_joint_unrolled import supplement_timing_integrity as integrity
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles, OutputMeter


class TimingIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def bound(self):
        path = self.root/'input'
        path.write_bytes(b'original')
        return path, BoundFiles({str(path): hashlib.sha256(b'original').hexdigest()})

    def test_content_only_read_at_entry_and_explicit_full_verification(self):
        path, bound = self.bound()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('hot path read')):
            bound.check()
            bound.check()
        bound.verify()
        self.assertEqual(path.read_bytes(), b'original')

    def test_full_verify_rejects_same_size_content_edit_with_restored_mtime(self):
        path, bound = self.bound()
        stamp = path.stat()
        path.write_bytes(b'modified')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(ValueError):
            bound.verify()

    def test_changed_ctime_rejected_at_hot_boundary(self):
        path, bound = self.bound()
        original = integrity._signature(path)
        with patch.object(integrity, '_signature', return_value=(
                *original[:-1], original[-1]+1)):
            with self.assertRaisesRegex(ValueError, 'file changed'):
                bound.check()

    def test_full_verify_rejects_content_when_every_metadata_field_collides(self):
        path, bound = self.bound()
        original = integrity._signature(path)
        path.write_bytes(b'modified')
        # A real remote filesystem reproduced this collision within one tick.
        with patch.object(integrity, '_signature', return_value=original):
            bound.check()
            with self.assertRaisesRegex(ValueError, 'content changed'):
                bound.verify()

    def test_same_size_file_replacement_rejected(self):
        path, bound = self.bound()
        replacement = self.root/'replacement'
        replacement.write_bytes(b'original')
        replacement.replace(path)
        with self.assertRaises(ValueError):
            bound.check()

    def test_missing_or_wrong_initial_hash_rejected(self):
        path, bound = self.bound()
        with self.assertRaises(ValueError):
            BoundFiles({str(path): '0'*64})
        path.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            bound.check()

    def test_meter_accounts_files_and_scratch_without_tree_scans(self):
        meter = OutputMeter(self.root, 10)
        meter.require_space(8)
        p = self.root/'data'
        p.write_bytes(b'12345')
        meter.record(p)
        self.assertEqual(meter.used, 5)
        with patch.object(Path, 'rglob', side_effect=AssertionError('hot path tree scan')):
            meter.require_space(5)
            with self.assertRaises(OSError):
                meter.require_space(6)
        meter.verify()

    def test_meter_rejects_untracked_changed_or_missing_outputs(self):
        for kind in ('extra', 'changed', 'missing'):
            with self.subTest(kind=kind):
                root = self.root/kind
                root.mkdir()
                meter = OutputMeter(root, 100)
                p = root/'data'
                p.write_bytes(b'a')
                meter.record(p)
                if kind == 'extra':
                    (root/'unexpected').write_bytes(b'a')
                elif kind == 'changed':
                    p.write_bytes(b'longer')
                else:
                    p.unlink()
                with self.assertRaises(ValueError):
                    meter.verify()

    def test_meter_rejects_duplicate_outside_and_over_budget_files(self):
        meter = OutputMeter(self.root, 1)
        p = self.root/'data'
        p.write_bytes(b'a')
        meter.record(p)
        with self.assertRaises(ValueError):
            meter.record(p)
        with self.assertRaises(ValueError):
            meter.record(self.root.parent/'outside')
        other = self.root/'more'
        other.write_bytes(b'b')
        with self.assertRaises(OSError):
            meter.record(other)

    def test_declared_setup_cache_is_included(self):
        meter = OutputMeter(self.root, 10)
        cache = self.root/'code-cache'
        cache.mkdir()
        (cache/'code').write_bytes(b'123')
        meter.adopt_tree(cache)
        self.assertEqual(meter.used, 3)
        meter.verify()


if __name__ == '__main__':
    unittest.main()
