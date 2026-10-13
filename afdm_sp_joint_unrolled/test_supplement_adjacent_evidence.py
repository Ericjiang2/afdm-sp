"""Synthetic integrity contracts; no generated frames or receiver calls."""
import tempfile
from pathlib import Path
import unittest

import numpy as np

import supplement_adjacent_evidence as evidence


class EvidenceContracts(unittest.TestCase):
    def test_roundtrip_then_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'raw.npz'
            original = np.array([1+2j, 3-4j], dtype=np.complex64)
            np.savez_compressed(path, value=original)
            raw = {'file': {'path': str(path), 'bytes': path.stat().st_size,
                            'sha256': evidence.file_sha(path)},
                   'metadata': {'H': {'array': 'value', 'shape': [2],
                                'dtype': 'complex64', 'sha256': evidence.array_hash(original)}}}
            restored = evidence.load_raw(raw, directory)
            np.testing.assert_array_equal(restored['H'], original)
            with path.open('ab') as handle:
                handle.write(b'corruption')
            with self.assertRaisesRegex(ValueError, 'size/hash changed'):
                evidence.load_raw(raw, directory)

    def test_raw_path_cannot_escape_run_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'outside.npz'
            np.savez(path, value=np.arange(3))
            raw = {'file': {'path': str(path), 'bytes': path.stat().st_size,
                            'sha256': evidence.file_sha(path)}, 'metadata': {}}
            with self.assertRaises(ValueError):
                evidence.load_raw(raw, Path(directory) / 'batch')

    def test_metadata_cannot_substitute_for_actual_input_identity(self):
        observed = dict(y=np.array([1j]), pilot=np.array([.5j]),
                        sigma2=np.array(.1), constellation=np.array([.5+.5j]))
        truth = {name: np.array([1]) for name in ('H', 'info', 'coded', 'noise', 'data')}
        metadata = {'input_hashes': {key: evidence.array_hash((observed if key in observed else truth)[key])
                    for key in ('y', 'H', 'info', 'coded', 'noise', 'pilot', 'data')}}
        evidence.validate_input({'observed': observed, 'truth': truth}, metadata)
        truth['info'][0] = 0
        with self.assertRaisesRegex(ValueError, 'actual arrays'):
            evidence.validate_input({'observed': observed, 'truth': truth}, metadata)

    def test_info_and_codeword_errors_have_separate_denominators(self):
        truth = dict(info=np.array([0, 1]), coded=np.array([0, 1, 1, 0]))
        result = dict(info_hat=np.array([1, 1]), decoded=np.array([1, 1, 0, 0]),
            info_error_vector=np.array([True, False]),
            code_error_vector=np.array([True, False, True, False]))
        scores = dict(coded_bit_errors=1, FER=1)
        output = evidence.validate_errors(result, truth, scores)
        self.assertEqual((output['bit_errors'], output['bits']), (1, 2))
        self.assertEqual((output['codeword_errors'], output['codeword_bits']), (2, 4))
        result['code_error_vector'][0] = False
        with self.assertRaisesRegex(ValueError, 'saved vector differs'):
            evidence.validate_errors(result, truth, scores)


if __name__ == '__main__':
    unittest.main()
