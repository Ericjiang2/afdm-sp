"""Synthetic validation only; no receiver calls or scientific evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('analysis', HERE / 'analyze-i01-development-v1.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)

class FrozenFamilyTests(unittest.TestCase):
    def setUp(self):
        self.family = json.loads((HERE.parent / 'evidence/global-contrast-manifest.json').read_text())['families']['F_I']

    def test_original(self):
        self.assertEqual(len(analysis.validate_family(self.family)), 48)

    def test_duplicate_replacing_interaction(self):
        index = next(i for i,c in enumerate(self.family['contrasts']) if c['id'].startswith('information_x'))
        self.family['contrasts'][index] = copy.deepcopy(self.family['contrasts'][0])
        with self.assertRaises(ValueError):
            analysis.validate_family(self.family)

    def test_allocations(self):
        for key, value in [('alpha', .5), ('m_max', 65), ('m_used_after_selection', 48), ('unused_slots_recycle_alpha', True)]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.family)
                changed[key] = value
                with self.assertRaises(ValueError):
                    analysis.validate_family(changed)

    def test_definitions(self):
        for key, value in [('coefficients', [-1, 1]), ('arms', ['Irealloc', 'I0']), ('snr_db', 9), ('method', 'linear_CP'), ('scene', 'other'), ('id', 'invented')]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.family)
                changed['contrasts'][0][key] = value
                with self.assertRaises(ValueError):
                    analysis.validate_family(changed)

    def test_missing_contrast(self):
        self.family['contrasts'].pop()
        with self.assertRaises(ValueError):
            analysis.validate_family(self.family)

class CompleteDesignTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((HERE.parent / 'evidence/global-contrast-manifest.json').read_text())
        proofs = []
        for b in range(192):
            for snr in (7, 8, 9):
                for arm in analysis.ARMS:
                    error = int(arm == 'I0' and b < 10)
                    errors = dict(FER=error, coded_bit_errors=error, raw_bit_errors=error,
                                  decoded_codeword_bit_errors=error, coded_bits_denominator=1024,
                                  raw_bits_denominator=512)
                    proofs.append(dict(identity=[b, snr, arm], errors=errors))
        self.audit = dict(status='passed', F_audited=3456, batches=[dict(proofs=proofs)])

    def test_known_paired_direction(self):
        result = analysis.analyze(self.audit, self.manifest)
        self.assertEqual(len(result['arm_summaries']), 18)
        self.assertEqual(len(result['contrasts']), 48)
        first = next(c for c in result['contrasts'] if c['id'] == 'info:I0-Irealloc@nominal:7')
        self.assertEqual((first['W'], first['L']), (10, 0))
        self.assertAlmostEqual(first['delta'], 10 / 192)

    def test_incomplete_or_duplicate_data(self):
        for change in ('partial', 'missing', 'duplicate'):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.audit)
                if change == 'partial':
                    altered['F_audited'] -= 1
                elif change == 'missing':
                    altered['batches'][0]['proofs'].pop()
                else:
                    altered['batches'][0]['proofs'][-1] = altered['batches'][0]['proofs'][0]
                with self.assertRaises(ValueError):
                    analysis.analyze(altered, self.manifest)

if __name__ == '__main__':
    unittest.main()
