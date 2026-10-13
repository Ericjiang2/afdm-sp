"""Deterministic thresholds, failure denominators, and recorder contracts."""
import json
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
import sys
from unittest.mock import patch

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol
from .study import cp_interval, proportion, thresholds


def fixture_result(output):
    dump(output/'raw.json', dict(fixture=True))
    return dict(new_observations=0, geometry_probes=0, fixture=True)


class StudyContracts(unittest.TestCase):
    def test_virtual_module_paths_are_not_project_sources(self):
        module = ModuleType('fixture_virtual')
        module.__file__ = '_ops.py'
        with patch.dict(sys.modules, fixture_virtual=module):
            self.assertNotIn((protocol.ROOT/'_ops.py').resolve(), protocol.project_sources())

    def test_missing_real_source_is_an_explicit_error(self):
        module = ModuleType('fixture_missing_real')
        module.__file__ = str(protocol.PACKAGE/'missing_real_fixture.py')
        with patch.dict(sys.modules, fixture_missing_real=module):
            with self.assertRaises(FileNotFoundError):
                protocol.project_sources()

    def test_order_statistic_and_strict_comparison(self):
        records = [dict(statistics={'4': dict(status='ok', Q=float(i), U=0)},
                        complete_group_seconds=0) for i in range(20)]
        config = dict(prefixes=[4], alpha=.1)
        result = thresholds([records, records], config)['4']
        self.assertEqual(result['by_condition'][0]['rank_one_based'], 19)
        self.assertEqual(result['threshold'], 18.)
        self.assertEqual(proportion(records, 4, 18., .05)['rejects'], 1)
        records[0]['statistics']['4'].update(status='failed', Q=None)
        with self.assertRaisesRegex(ValueError, 'calibration failure'):
            thresholds([records], config)

    def test_full_denominator_with_failed_decisions(self):
        records = [dict(statistics={'4': dict(status=s, Q=q, U=None)},
                        complete_group_seconds=0) for s, q in
                   [('ok', 3.), ('ok', 0.), ('failed', None), ('failed', None)]]
        result = proportion(records, 4, 1., .05)
        self.assertEqual(result['groups'], 4)
        self.assertEqual(result['failures'], 2)
        self.assertEqual(result['rejection_rate_bounds'], [.25, .75])
        self.assertEqual(result['confidence_interval'], [cp_interval(1, 4, .05)[0], cp_interval(3, 4, .05)[1]])
        self.assertEqual(cp_interval(0, 4, .05)[0], 0)
        self.assertEqual(cp_interval(4, 4, .05)[1], 1)

    def test_private_recorder_registration_and_failure(self):
        real_load = protocol._load

        def fixture_load(name, path):
            module = real_load(name, path)
            if name == '_coherent_private_admission':
                module.committed_sources = lambda paths: dict(head='fixture', committed_task_source_sha256={})
            return module

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'control').mkdir()
            (root/'control/run_contract.json').write_text(json.dumps(dict(
                max_wall_seconds=10, max_total_reserved_wall_seconds=20,
                max_new_development_observations=10, output_limit_bytes=10000000,
                max_geometry_probes=5, max_process_memory_bytes=8589934592)))
            config = dict(seed=[1], new_observations=0, new_geometry_probes=2)

            def calculate(output):
                self.assertTrue((output/'registration.json').exists())
                self.assertTrue((output/'environment.json').exists())
                snapshots = [p.read_bytes() for p in (output/'source_snapshot').iterdir()]
                self.assertIn((protocol.PACKAGE/'thread_binding.py').read_bytes(), snapshots)
                return fixture_result(output)

            with patch.object(protocol, '_load', side_effect=fixture_load):
                protocol.run('fixture', config, [], calculate, artifact_root=root, wall_seconds=5)
                with self.assertRaises(FileExistsError):
                    protocol.run('fixture', config, [], calculate, artifact_root=root, wall_seconds=5)

                def fail(output):
                    fixture_result(output)
                    raise RuntimeError('intentional fixture error')

                with self.assertRaisesRegex(RuntimeError, 'intentional fixture'):
                    protocol.run('failure', config, [], fail, artifact_root=root, wall_seconds=5)
                attempt = json.loads((root/'execution/failure/attempt.json').read_text())
                self.assertEqual(attempt['status'], 'invalid_partial')
                self.assertEqual(attempt['reserved_wall_seconds'], 5)
                self.assertTrue((root/'execution/failure/raw.json').exists())
                with self.assertRaisesRegex(ValueError, 'geometry probe reservation'):
                    protocol.run('blocked', config, [], calculate, artifact_root=root, wall_seconds=5)
                self.assertFalse((root/'execution/blocked').exists())


if __name__ == '__main__':
    unittest.main()
