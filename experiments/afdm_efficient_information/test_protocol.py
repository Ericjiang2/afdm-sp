"""Recorder contract fixtures only; these are not scientific study evidence."""
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from experiments.afdm_efficient_information import protocol as p
from experiments.afdm_higher_order_information import protocol as old


def fixture_result(output):
    p.dump(output / 'raw.json', {'fixture': True})
    return {'fixture': True}


class ProtocolContracts(unittest.TestCase):
    @contextmanager
    def fixture(self, **limits):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission = root / 'mission'
            mission.mkdir()
            contract = dict(max_wall_seconds=20, max_total_reserved_wall_seconds=30,
                            max_new_development_observations=5, output_limit_bytes=1000000)
            contract.update(limits)
            (mission / 'run_contract.json').write_text(json.dumps(contract))
            with patch.object(p, 'MISSION', mission), patch.object(p, 'ARTIFACT', root / 'results'), patch.object(p, 'committed_sources', return_value={'head': 'fixture'}):
                yield root

    def test_registration_snapshot_and_old_state_isolation(self):
        with self.fixture() as root:
            frozen = root / 'frozen_old'
            frozen.mkdir()
            sentinel = frozen / 'keep.json'
            sentinel.write_text('{"old": true}\n')
            original_source = old.hashes([old.__file__])

            def calculate(output):
                reg = json.loads((output / 'registration.json').read_text())
                self.assertEqual(reg['schema'], 'efficient-information-attempt/1')
                self.assertEqual(reg['cumulative_reserved_wall_seconds'], 10)
                self.assertEqual(reg['cumulative_reserved_new_observations'], 2)
                self.assertTrue((output / 'environment.json').exists())
                snapshots = list((output / 'source_snapshot').iterdir())
                saved_bytes = [path.read_bytes() for path in snapshots]
                for source in [Path(p.__file__), Path(old.__file__), Path(__file__), p.MISSION / 'run_contract.json']:
                    self.assertIn(source.read_bytes(), saved_bytes)
                return fixture_result(output)

            with patch.object(old, 'ARTIFACT', frozen), patch.object(old, 'MISSION', frozen):
                p.run('first', dict(seed=[1], new_observations=2), [], calculate, 10)
                self.assertEqual(old.ARTIFACT, frozen)
                self.assertEqual(old.MISSION, frozen)
                self.assertEqual(list(frozen.iterdir()), [sentinel])
                self.assertEqual(sentinel.read_text(), '{"old": true}\n')
            self.assertEqual(old.hashes([old.__file__]), original_source)
            attempt = json.loads((p.ARTIFACT / 'first/attempt.json').read_text())
            self.assertEqual(attempt['status'], 'complete')
            self.assertEqual(attempt['reserved_wall_seconds'], 10)
            self.assertTrue(any(key.endswith('/raw.json') for key in attempt['artifact_sha256']))
            before = p.hashes(path for path in (p.ARTIFACT / 'first').rglob('*') if path.is_file())
            with self.assertRaises(FileExistsError):
                p.run('first', dict(seed=[1], new_observations=0), [], fixture_result, 10)
            self.assertEqual(before, p.hashes(path for path in (p.ARTIFACT / 'first').rglob('*') if path.is_file()))

    def test_failed_attempt_retains_raw_and_both_reservations(self):
        with self.fixture():
            def fail(output):
                fixture_result(output)
                raise RuntimeError('deliberate fixture failure')

            with self.assertRaisesRegex(RuntimeError, 'deliberate'):
                p.run('failed', dict(seed=[1], new_observations=4), [], fail, 20)
            attempt = json.loads((p.ARTIFACT / 'failed/attempt.json').read_text())
            self.assertEqual(attempt['status'], 'invalid_partial')
            self.assertEqual(attempt['reserved_new_observations'], 4)
            self.assertEqual(attempt['reserved_wall_seconds'], 20)
            self.assertTrue((p.ARTIFACT / 'failed/raw.json').exists())
            self.assertTrue(any(key.endswith('/raw.json') for key in attempt['artifact_sha256']))
            self.assertGreater(attempt['peak_rss_bytes'], 0)
            with self.assertRaisesRegex(ValueError, 'total reserved wall'):
                p.run('wall_blocked', dict(seed=[1], new_observations=0), [], fixture_result, 11)
            with self.assertRaisesRegex(ValueError, 'observation budget'):
                p.run('observation_blocked', dict(seed=[1], new_observations=2), [], fixture_result, 10)
            self.assertFalse((p.ARTIFACT / 'wall_blocked').exists())
            self.assertFalse((p.ARTIFACT / 'observation_blocked').exists())
            p.run('exact_remaining', dict(seed=[1], new_observations=1), [], fixture_result, 10)
            reg = json.loads((p.ARTIFACT / 'exact_remaining/registration.json').read_text())
            self.assertEqual(reg['cumulative_reserved_wall_seconds'], 30)
            self.assertEqual(reg['cumulative_reserved_new_observations'], 5)

    def test_uncommitted_source_is_rejected_before_callback_or_stage(self):
        with self.fixture(), patch.object(p, 'committed_sources', side_effect=ValueError('uncommitted study source')):
            with self.assertRaisesRegex(ValueError, 'uncommitted study source'):
                p.run('blocked', dict(seed=[1], new_observations=0), [], fixture_result, 10)
            self.assertFalse(p.ARTIFACT.exists())
        with tempfile.TemporaryDirectory(dir=p.PACKAGE) as directory:
            source = Path(directory) / 'uncommitted.py'
            source.write_text('fixture = True\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted study source'):
                p.committed_sources([source])

    def test_changed_head_bytes_rejected(self):
        source = Path(p.__file__)
        answers = [subprocess.CompletedProcess([], 0, 'fixture-head\n'),
                   subprocess.CompletedProcess([], 0, str(source.relative_to(p.ROOT)) + '\n'),
                   subprocess.CompletedProcess([], 0, b'different HEAD bytes\n')]
        with patch('subprocess.run', side_effect=answers):
            with self.assertRaisesRegex(ValueError, 'differs from HEAD'):
                p.committed_sources([source])

    def test_invalid_allocations_rejected_without_stage(self):
        with self.fixture():
            for config in [dict(seed=[1]), dict(seed=[1], new_observations=True),
                           dict(seed=[1], new_observations=-1),
                           dict(seed=[1], new_observations=0, receiver_calls=1),
                           dict(seed=[1], new_observations=0, decoder_calls=1),
                           dict(seed=[1], new_observations=0, new_confirmation_stream=True)]:
                with self.subTest(config=config), self.assertRaises(ValueError):
                    p.run('blocked', config, [], fixture_result, 10)
            for wall in [True, 0, 21, float('inf'), float('nan')]:
                with self.subTest(wall=wall), self.assertRaises(ValueError):
                    p.run('blocked', dict(seed=[1], new_observations=0), [], fixture_result, wall)
            self.assertFalse(p.ARTIFACT.exists())

    def test_exhausted_output_and_concurrent_run_rejected(self):
        with self.fixture(output_limit_bytes=1):
            p.ARTIFACT.mkdir()
            (p.ARTIFACT / 'retained_raw').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError, 'output byte budget'):
                p.run('blocked', dict(seed=[1], new_observations=0), [], fixture_result, 10)
            self.assertFalse((p.ARTIFACT / 'blocked').exists())
        with self.fixture():
            p.ARTIFACT.mkdir()
            with (p.ARTIFACT / '.task.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                with self.assertRaisesRegex(RuntimeError, 'study is active'):
                    p.run('blocked', dict(seed=[1], new_observations=0), [], fixture_result, 10)
            self.assertFalse((p.ARTIFACT / 'blocked').exists())

    def test_late_task_import_is_retained_as_failure(self):
        name = 'efficient_protocol_late_fixture'
        module = ModuleType(name)
        module.__file__ = str(p.PACKAGE / 'late_fixture.py')
        with self.fixture():
            def calculate(output):
                sys.modules[name] = module
                return fixture_result(output)
            try:
                with self.assertRaisesRegex(RuntimeError, 'source import graph changed'):
                    p.run('late', dict(seed=[1], new_observations=1), [], calculate, 10)
            finally:
                sys.modules.pop(name, None)
            self.assertEqual(json.loads((p.ARTIFACT / 'late/attempt.json').read_text())['status'], 'invalid_partial')

    def test_late_numerical_pool_is_retained_as_failure(self):
        with self.fixture():
            recorder = p._recorder()
            bindings = [{'pools': []}, {'pools': [{'num_threads': 1, 'user_api': 'openmp'}]}]
            with patch.object(p, '_recorder', return_value=recorder), patch.object(recorder.runpy, 'run_path', side_effect=[{'blas_binding': lambda: bindings[0]}, {'blas_binding': lambda: bindings[1]}]):
                with self.assertRaisesRegex(RuntimeError, 'numerical thread binding changed'):
                    p.run('late_pool', dict(seed=[1], new_observations=1), [], fixture_result, 10)
            self.assertEqual(json.loads((p.ARTIFACT / 'late_pool/attempt.json').read_text())['status'], 'invalid_partial')


if __name__ == '__main__':
    unittest.main()
