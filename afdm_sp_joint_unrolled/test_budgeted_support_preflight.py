import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from afdm_sp_joint_unrolled.budgeted_support_preflight import main, probe


class PreflightTests(unittest.TestCase):
    def test_cpu_is_explicit_and_numerically_valid(self):
        result = probe('cpu')
        self.assertTrue(result['passed'])
        self.assertEqual(result['device'], 'cpu')
        self.assertTrue(all(c['tensor_device'] == 'cpu' for c in result['checks']))

    def test_missing_cuda_is_failure_and_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'failed.json'
            with patch('torch.cuda.is_available', return_value=False), contextlib.redirect_stderr(io.StringIO()):
                code = main(['--output', str(output)])
            record = json.loads(output.read_text())
            self.assertEqual(code, 1)
            self.assertFalse(record['passed'])
            self.assertEqual(record['device'], 'cuda')
            self.assertNotIn('checks', record)

    def test_existing_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'existing.json'
            output.write_text('previous evidence')
            with self.assertRaises(FileExistsError):
                main(['--device', 'cpu', '--output', str(output)])
            self.assertEqual(output.read_text(), 'previous evidence')


if __name__ == '__main__':
    unittest.main()
