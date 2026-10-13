"""Local contract tests; no real receiver, decoding, or remote simulation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('oracle_one_shot_v1',
    Path(__file__).with_name('oracle_one_shot_v1.py'))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(stage):
    phase, blocks = runner.STAGES[stage]
    return dict(schema=runner.SCHEMA, stage=stage, blocks=blocks, snrs=[7, 8],
        arm=runner.ARM[phase], device='cpu', threads=1, outer_iterations=10,
        terminal_bp_iterations=20, checkpoints=[1, 4, 7],
        terminal_check_prior='retain', terminal_bp_temperature=1.,
        terminal_variance_source='physical', initial_lstsq_driver='gels',
        receiver_recipe='B0-p2-s0.5', bounds=dict(F=len(blocks)*2, seconds=7200),
        output_bytes=1024**3)


class OneShotRunnerContractTests(unittest.TestCase):
    def test_default_has_independent_four_f_budget_and_oracle_has_64_total(self):
        default = contract('default-engineering')
        self.assertEqual(runner.validate_contract(default), ('default', [0, 20]))
        oracle_eng = contract('oracle-engineering'); oracle_eng['default_admission'] = 'evidence/default.json'
        oracle_dev = contract('oracle-development')
        oracle_dev.update(default_admission='evidence/default.json',
            engineering_admission='evidence/engineering.json')
        self.assertEqual(runner.validate_contract(oracle_eng)[1], [0, 20])
        self.assertEqual(runner.validate_contract(oracle_dev)[1], [b for b in range(32) if b not in (0, 20)])
        self.assertEqual(default['bounds']['F'], 4)
        self.assertEqual(oracle_eng['bounds']['F'] + oracle_dev['bounds']['F'], 64)

    def test_oracle_rejects_missing_default_gate_and_changed_g1_route(self):
        c = contract('oracle-engineering')
        with self.assertRaisesRegex(ValueError, 'default'):
            runner.validate_contract(c)
        c['default_admission'] = 'evidence/default.json'
        for key, wrong in [('bounds', dict(F=64, seconds=7200)),
                           ('checkpoints', [1, 7]), ('terminal_bp_temperature', 2.),
                           ('arm', 'G1_FULL')]:
            changed = dict(c, **{key: wrong})
            with self.subTest(key=key), self.assertRaises(ValueError):
                runner.validate_contract(changed)

    def test_pass_receipt_binds_saved_summary_source_script_and_four_exact_f(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'evidence').mkdir(); (root/'runs').mkdir()
            summary = root/'runs/default-summary.json'; summary.write_text('{"status":"COMPLETE"}')
            receipt = root/'evidence/default.json'
            accepted = dict(status='PASS', stage='default-engineering', saved_F=4,
                default_exact=True, source_sha256='source', script_sha256='script',
                summary_path='runs/default-summary.json', summary_sha256=digest(summary))
            receipt.write_text(json.dumps(accepted))
            c = contract('oracle-engineering')
            c.update(default_admission='evidence/default.json', default_admission_sha256=digest(receipt))
            runner.check_admission(c, root, digest, phase='oracle',
                source_hash='source', script_hash='script')
            for key, bad in [('saved_F', 3), ('default_exact', False),
                             ('source_sha256', 'other'), ('summary_sha256', 'other')]:
                changed = dict(accepted, **{key: bad}); receipt.write_text(json.dumps(changed))
                c['default_admission_sha256'] = digest(receipt)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'default'):
                    runner.check_admission(c, root, digest, phase='oracle',
                        source_hash='source', script_hash='script')

    def test_default_state_must_be_exact_and_truth_free(self):
        calls = []
        def compare(actual, old):
            calls.append((actual, old))
            if actual['symbol'] != old['symbol']:
                raise ValueError('state differs')
        self.assertTrue(runner.check_default({'symbol': 1}, {'symbol': 1}, compare))
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'true data'):
            runner.check_default({'symbol': 1, 'one_shot_true_data_ce_records': []},
                {'symbol': 1}, compare)
        with self.assertRaisesRegex(ValueError, 'state differs'):
            runner.check_default({'symbol': 2}, {'symbol': 1}, compare)


if __name__ == '__main__':
    unittest.main()
