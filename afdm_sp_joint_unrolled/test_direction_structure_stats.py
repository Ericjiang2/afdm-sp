"""Pure statistical/admission fixtures, not receiver or scientific-run evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from afdm_sp_joint_unrolled.direction_structure_stats import comparison, load_run, validate_table, corrected_metadata, validate_source_equivalence


class StructureStatisticsTests(unittest.TestCase):
    def test_positive_means_link_benefit(self):
        result = comparison([1, 1, 0, 0], [0, 0, 0, 0])
        self.assertEqual(result['delta'], .5)
        self.assertEqual(result['comparisons'], 3)
        self.assertEqual(comparison([0, 0], [1, 0])['delta'], -.5)

    def test_zero_errors_are_not_zero_uncertainty(self):
        result = comparison([0] * 255, [0] * 255)
        self.assertLess(result['interval'][0], 0)
        self.assertGreater(result['interval'][1], 0)
        self.assertTrue(result['precision_insufficient'])

    def test_missing_and_duplicate_fixture_rejected(self):
        with self.assertRaisesRegex(ValueError, 'requires255'):
            validate_table([])
        fixture = {'SNR': 8, 'block_id': 0, 'arm_id': 'M_link', '_kind': 'structure_CE'}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_table([fixture, fixture.copy()])

    def test_polluted_source_fixture_rejected_before_reading_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = {'split': 'mechanism', 'protocol_sha256': 'fixture-protocol',
                        'source_sha256': 'fixture-original'}
            complete = {'status': 'complete', 'protocol_sha256': 'fixture-protocol',
                        'source_sha256': 'fixture-polluted',
                        'calls_attempted': {'structure_CE': 4, 'structure_terminal': 4},
                        'calls_completed': {'structure_CE': 4, 'structure_terminal': 4}}
            for name, value in [('contract', contract), ('complete', complete)]:
                (root / (name + '.json')).write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'source mismatch'):
                load_run(root, 'fixture-protocol')

    def test_explicit_correction_fixture_preserves_original(self):
        row={'source_sha256':{'numeric.py':'fixture'},'device':'cuda','dtype':'complex128'}
        contract={'source_sha256':row['source_sha256'],'command':['python','driver','--device','cpu']}
        digest=hashlib.sha256(json.dumps(row['source_sha256'],sort_keys=True).encode()).hexdigest()
        entry={'record_sha256':'record','contract_sha256':'contract','source_manifest_sha256':digest,
               'original_device':'cuda','original_dtype':'complex128'}
        manifest={'reason':'device_metadata_fix','records':[entry],'sources':{digest:row['source_sha256']}}
        fixed=corrected_metadata(row,'record',contract,'contract',manifest)
        self.assertEqual(fixed['device'],'cpu')
        self.assertEqual(fixed['original_device'],'cuda')
        self.assertEqual(row['device'],'cuda')
        with self.assertRaisesRegex(ValueError,'missing/duplicate'):
            corrected_metadata(row,'missing',contract,'contract',manifest)
        with self.assertRaisesRegex(ValueError,'binding'):
            corrected_metadata(row,'record',contract,'wrong-contract',manifest)
        for command in (['--device','cuda'],['--device','cpu','--device','cpu'],['--device=cpu']):
            with self.assertRaisesRegex(ValueError,'unique'):
                corrected_metadata(row,'record',dict(contract,command=command),'contract',manifest)

    def test_source_equivalence_fixture_rejects_numerical_drift(self):
        first={'numeric.py':'same','direction_structure_run.py':'old'}
        second=dict(first,**{'direction_structure_run.py':'new'})
        manifest={'reason':'device_metadata_fix','source_maps':[first,second]}
        self.assertEqual(validate_source_equivalence(manifest),[first,second])
        second['numeric.py']='changed'
        with self.assertRaisesRegex(ValueError,'numerical source drift'):
            validate_source_equivalence(manifest)


if __name__ == '__main__':
    unittest.main()
