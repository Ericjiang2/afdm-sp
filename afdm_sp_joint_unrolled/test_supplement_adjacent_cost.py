"""Synthetic scope/telemetry tests and a real child-process deadline test; zero F."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

import supplement_adjacent_cost_run as collector
import supplement_adjacent_cost_stats as statistics

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads(Path(os.environ['ADJACENT_COST_CONTRACT']).read_text())
spec = importlib.util.spec_from_file_location('pipeline', HERE/'cost512-pipeline-v1.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class CostScopeTests(unittest.TestCase):
    def test_scope_rejects_changed_sample_physics_methods_and_purpose(self):
        manifest = dict(methods=CONTRACT['methods'], admitted_purposes=['cost-warmup', 'cost-measurement'])
        collector.validate_cost_contract(CONTRACT, manifest, 'cuda:0')
        for key, value in [('physical_N', 512), ('n_per_snr', 1024), ('new_F', {'total': 4698})]:
            changed = copy.deepcopy(CONTRACT)
            changed[key] = value
            with self.assertRaises(ValueError):
                collector.validate_cost_contract(changed, manifest, 'cuda:0')
        changed = copy.deepcopy(manifest)
        changed['methods']['I1']['outer_BP'] = 20
        with self.assertRaises(ValueError):
            collector.validate_cost_contract(CONTRACT, changed, 'cuda:0')
        with self.assertRaises(ValueError):
            collector.validate_cost_contract(CONTRACT, manifest, 'cpu')
        with self.assertRaises(ValueError):
            collector.validate_cost_contract(CONTRACT, dict(manifest, admitted_purposes=['confirm']), 'cuda:0')

    def test_rejected_telemetry_is_retained(self):
        bad = dict(compute_pids=[os.getpid(), 987654321], numerical_threads=1, interop_threads=1,
            load_average=[0, 0, 0], cpu_count=128, temperature_C=50, disk_free_bytes=30_000_000_000,
            prior_workers_alive=[])
        saved = []
        with patch.object(collector, 'telemetry', return_value=bad):
            with self.assertRaisesRegex(ValueError, 'another GPU'):
                collector.record_telemetry(None, HERE, [], 'rejected.json', lambda p, v: saved.append((p, v)))
        self.assertEqual(saved, [('rejected.json', bad)])
        valid = dict(bad, compute_pids=[os.getpid()])
        collector.validate_telemetry(valid, os.getpid())
        for key, value in [('numerical_threads', 2), ('interop_threads', 2), ('temperature_C', 86),
                           ('disk_free_bytes', 1), ('prior_workers_alive', [dict(pid=1)]),
                           ('load_average', [113, 0, 0])]:
            with self.assertRaises(ValueError):
                collector.validate_telemetry(dict(valid, **{key: value}), os.getpid())

    def test_new_endpoint_inventory_and_chronological_shape(self):
        self.assertEqual(len(statistics.validate_design(CONTRACT)), 18)
        changed = copy.deepcopy(CONTRACT)
        changed['endpoints'].pop()
        with self.assertRaises(ValueError):
            statistics.validate_design(changed)
        changed = copy.deepcopy(CONTRACT)
        changed['endpoints'][0]['arm_column'] = 1
        with self.assertRaises(ValueError):
            statistics.validate_design(changed)
        x, blocks = np.ones((512, 9)), np.arange(1547, 2059)
        statistics.validate_matrix(x, blocks)
        for values, ids in ((x[:-1], blocks[:-1]), (x, blocks+1), (x*0, blocks), (x*np.nan, blocks)):
            with self.assertRaises(ValueError):
                statistics.validate_matrix(values, ids)

    def test_inconclusive_and_threshold_fail_cannot_become_pass(self):
        rows = [dict(r, status='COST_PASS', valid_for_cost_decision=True) for r in CONTRACT['endpoints']]
        decision = statistics.comparison_decisions(rows)
        self.assertTrue(all(r['cost_pass'] for r in decision.values()))
        rows[0].update(status='COST_BOUND_EXCEEDS_LIMIT')
        self.assertEqual(statistics.comparison_decisions(rows)['I1_over_A2']['status'], 'COST_BOUND_EXCEEDS_LIMIT')
        rows[1].update(status='UNRESOLVED_STABILITY', valid_for_cost_decision=False)
        self.assertEqual(statistics.comparison_decisions(rows)['I1_over_A2']['status'], 'INCONCLUSIVE')
        with self.assertRaises(ValueError):
            statistics.comparison_decisions(rows[:-1])

    def test_full_frozen_bootstrap_on_synthetic_constant_ratios(self):
        # Zero physical observations. Shared scaling gives known exact mean/p95 ratios.
        base = np.random.default_rng(7421).lognormal(0., .005, (512, 1))
        factors = np.tile([.8, 1., .6], 3)
        x = base*factors
        result = statistics.analyze_matrix(CONTRACT, x, statistics.load_helpers(CONTRACT))
        self.assertEqual(len(result['endpoints']), 18)
        self.assertEqual(sum(e['pooled']['draws'] for e in result['ensembles']), 600000)
        for endpoint in result['endpoints']:
            expected = factors[endpoint['arm_column']]/factors[endpoint['reference_column']]
            self.assertAlmostEqual(endpoint['point_ratio'], expected, places=12)
            self.assertAlmostEqual(endpoint['upper_ratio'], expected, places=12)

    def test_actual_child_deadline_reaps_only_created_process(self):
        with tempfile.TemporaryDirectory(prefix='adjacent-cost-contract-') as directory:
            root = Path(directory)
            target = root/'sleeper.py'
            target.write_text('import signal,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\ntime.sleep(30)\n')
            stages = []
            started = time.time()
            with patch.object(pipeline, 'PYTHON', sys.executable):
                with self.assertRaises(subprocess.TimeoutExpired):
                    pipeline.run_stage(root, 'deadline-test', [str(target)], os.environ.copy(),
                        started+.3, started+2., stages)
            self.assertLess(time.time()-started, 2.)
            self.assertLess(stages[0]['exitcode'], 0)
            self.assertIsNone(pipeline.process_identity(stages[0]['pid']))
            self.assertEqual(int((root/'deadline-test.exit').read_text()), stages[0]['exitcode'])
            self.assertTrue((root/'deadline-test-stage.json').is_file())

    def test_admission_finds_actual_unregistered_project_worker(self):
        with tempfile.TemporaryDirectory(prefix='adjacent-cost-inventory-') as directory:
            root = Path(directory)/'project/afdm_sp_joint_unrolled/outputs'
            process = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)',
                str(root)], start_new_session=True)
            try:
                self.assertIn(process.pid, [p['pid'] for p in pipeline.active_project_workers(root)])
            finally:
                pipeline.stop_owned(process, time.time()+2.)


if __name__ == '__main__':
    unittest.main()
