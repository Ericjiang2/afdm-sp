"""Unit fixtures for development admission, never actual experiment evidence."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from .bottleneck_pilot import sha
from .trans_next_profile_run import execute


class QPSKAdmissionTests(unittest.TestCase):
    def test_changed_admission_or_algorithm_cannot_reach_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root/'fixture-input'
            data.write_text('unit fixture only')
            producer = root/'producer.json'
            algorithm = Path(__file__).parent/'mp_detect_bp_torch.py'
            producer.write_text(json.dumps({algorithm.name: sha(algorithm)}))
            admission = root/'admission.json'
            admission.write_text(json.dumps(dict(status='PASS', records=20, CE_states=180,
                source_sha256=sha(producer))))
            c = dict(schema='trans-qpsk-profile-v1', stage='development', device='cpu', threads=1,
                blocks=list(range(32)), snrs=[7, 8], F_limit=128, tag='fixture',
                input_summary=str(data), input_summary_sha256=sha(data),
                checkpoint_path=str(data), checkpoint_sha256=sha(data),
                engineering_admission=str(admission), engineering_admission_sha256=sha(admission),
                engineering_source_manifest=str(producer), engineering_source_sha256=sha(producer),
                arms=[dict(name='QPSK_MEAN', receiver=dict(bp_edge_projection='qpsk_tanh')),
                      dict(name='QPSK_REF47', receiver=dict(bp_edge_projection='qpsk_tanh'),
                           feedback=dict(refresh_checkpoints=[4, 7]))])
            contract = root/'contract.json'
            contract.write_text(json.dumps(c))
            args = types.SimpleNamespace(root=root/'fixture', contract=contract,
                contract_sha256=sha(contract), source_manifest=producer, source_sha256=sha(producer))
            with patch('afdm_sp_joint_unrolled.trans_next_profile_run.setup_guard',
                       side_effect=RuntimeError('unit-boundary')):
                with self.assertRaisesRegex(RuntimeError, 'unit-boundary'):
                    execute(args)
                admission.write_text(admission.read_text()+' ')
                with self.assertRaisesRegex(ValueError, 'audit'):
                    execute(args)
                c['engineering_admission_sha256'] = sha(admission)
                contract.write_text(json.dumps(c)); args.contract_sha256 = sha(contract)
                with patch('afdm_sp_joint_unrolled.trans_next_profile_run.sha',
                           side_effect=lambda p: 'wrong-algorithm' if Path(p) == algorithm else sha(p)):
                    with self.assertRaisesRegex(ValueError, 'qualified projection algorithm'):
                        execute(args)


if __name__ == '__main__':
    unittest.main()
