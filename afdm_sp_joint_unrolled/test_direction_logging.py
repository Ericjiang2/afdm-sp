"""Strict logging unit fixtures; these are not receiver/E2E evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.direction_logging import REQUIRED_FIELDS,validate_record,validate_pair


def fixture_record():
    inputs={'y':'fixture-y','pilot':'fixture-p','H':'fixture-H','info':'fixture-info',
            'coded':'fixture-coded','data':'fixture-data','noise':'fixture-noise'}
    record=dict.fromkeys(REQUIRED_FIELDS,None)
    record.update(run_id='fixture-not-E2E',split='engineering',block_id=0,
        channel_seed=1,data_seed={'seed_words':[1,2,3]},noise_seed={'seed_words':[1,2,4]},
        code_id='fixture-code',interleaver_id='identity-fixture',SNR=8,rho=.5,P_phys=8,
        generator_id='fixture',truncation_id='fixture',source_sha256={},config_sha256='fixture',
        device='cpu',dtype='complex128',library_versions={},deterministic_flags={},
        raw_y_hash=inputs['y'],pilot_hash=inputs['pilot'],H_true_hash=inputs['H'],
        truth_access_level='none',arm_id='b0-s1',H_cancel_source='fixture-estimate',
        H_data_source='fixture-estimate',H_cov_source='scalar-fixture',sigma_source='fixture',
        sigma_value=.1,pilot_cancellation_identity_check={'relative_error':0.},
        S_initial=[1],S_submitted=[1],K_nominal=1,K_effective=1,
        graph_edges_each_stage=[],raw_bit_errors=2,coded_bit_errors=0,FER=0,
        hard_output_hash='fixture-hard',decoder_status={'syndrome_ok':True},
        channel_error={},posterior_audit={},pilot_residual={},data_residual={},message_confidence={},
        call_type='full',elapsed_seconds=.1,peak_gpu_bytes=0,snapshot={'scope':'fixture'},
        input_hashes=inputs,protocol_sha256='fixture-protocol',evidence_kind='unit-fixture')
    return record


class LoggingContracts(unittest.TestCase):
    def test_minimal_labeled_record_and_immutable_publish(self):
        row=fixture_record()
        validate_record(row,expected_inputs=row['input_hashes'],deployable=True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'record.json'
            publish_json(path,row)
            self.assertEqual(json.loads(path.read_text())['evidence_kind'],'unit-fixture')
            with self.assertRaises(FileExistsError):publish_json(path,row)

    def test_every_required_field_is_required(self):
        for field in REQUIRED_FIELDS:
            row=fixture_record();del row[field]
            with self.subTest(field=field),self.assertRaises(ValueError):validate_record(row)

    def test_nested_nan_not_published(self):
        row=fixture_record();row['posterior_audit']={'bad':float('nan')}
        with self.assertRaises(ValueError):validate_record(row)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.json'
            with self.assertRaises(ValueError):publish_json(path,row)
            self.assertFalse(path.exists())

    def test_unpaired_inputs_and_duplicate_arms_rejected(self):
        a=fixture_record();b=copy.deepcopy(a);b['arm_id']='ridge-s1'
        validate_pair([a,b])
        b['input_hashes']['noise']='different-noise'
        with self.assertRaises(ValueError):validate_pair([a,b])
        with self.assertRaises(ValueError):validate_pair([a,a])
        b=copy.deepcopy(a);b['raw_y_hash']='unlinked-y'
        with self.assertRaises(ValueError):validate_record(b)

    def test_oracle_cannot_enter_deployable_registry(self):
        row=fixture_record();row['truth_access_level']='CSI_oracle'
        validate_record(row,deployable=False)
        with self.assertRaises(ValueError):validate_record(row,deployable=True)

    def test_invalid_support_error_and_fer_rejected(self):
        for change in ({'S_submitted':[1,1]},{'S_initial':[515]},
                       {'coded_bit_errors':1},{'raw_bit_errors':-1},{'sigma_value':0}):
            row=fixture_record();row.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):validate_record(row)


if __name__=='__main__':
    unittest.main()
