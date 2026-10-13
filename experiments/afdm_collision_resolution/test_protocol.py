"""Tiny recorder fixtures; no scientific observations or remote operations."""
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.afdm_collision_resolution import protocol as p
from experiments.afdm_efficient_information import protocol as frozen


def fixture_calculation(output):
    p.dump(output/'raw.json', dict(artificial_fixture=True))
    return dict(artificial_fixture=True)


class CollisionProtocolTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission = root/'mission'
            mission.mkdir()
            (mission/'run_contract.json').write_text(json.dumps(dict(max_wall_seconds=20,
                max_total_reserved_wall_seconds=30, max_new_development_observations=5,
                output_limit_bytes=1000000)))
            with (patch.object(p, 'MISSION', mission), patch.object(p, 'ARTIFACT', root/'results'),
                  patch.object(p, 'committed_sources', return_value=dict(head='fixture'))):
                yield root

    def test_private_paths_and_frozen_state_are_unchanged(self):
        before = (frozen.ROOT, frozen.PACKAGE, frozen.MISSION, frozen.ARTIFACT)
        with self.fixture():
            p.run('tiny', dict(seed=[1], new_observations=0), [], fixture_calculation, 10)
            registration = json.loads((p.ARTIFACT/'tiny/registration.json').read_text())
            attempt = json.loads((p.ARTIFACT/'tiny/attempt.json').read_text())
            snapshots = [path.read_bytes() for path in (p.ARTIFACT/'tiny/source_snapshot').iterdir()]
            self.assertIn(Path(p.__file__).read_bytes(), snapshots)
            self.assertIn(p.IMPLEMENTATION.read_bytes(), snapshots)
            self.assertEqual(registration['cumulative_reserved_wall_seconds'], 10)
            self.assertEqual(attempt['reserved_new_observations'], 0)
            self.assertEqual(attempt['status'], 'complete')
            with self.assertRaises(FileExistsError):
                p.run('tiny', dict(seed=[1], new_observations=0), [], fixture_calculation, 10)
        self.assertEqual(before, (frozen.ROOT, frozen.PACKAGE, frozen.MISSION, frozen.ARTIFACT))

    def test_failure_retains_raw_and_both_reservations(self):
        with self.fixture():
            def fail(output):
                fixture_calculation(output)
                raise RuntimeError('deliberate fixture failure')
            with self.assertRaisesRegex(RuntimeError, 'deliberate'):
                p.run('failed', dict(seed=[2], new_observations=4), [], fail, 20)
            attempt = json.loads((p.ARTIFACT/'failed/attempt.json').read_text())
            self.assertEqual(attempt['status'], 'invalid_partial')
            self.assertEqual(attempt['reserved_wall_seconds'], 20)
            self.assertEqual(attempt['reserved_new_observations'], 4)
            self.assertTrue(any(name.endswith('/raw.json') for name in attempt['artifact_sha256']))
            with self.assertRaisesRegex(ValueError, 'total reserved wall'):
                p.run('wall_blocked', dict(seed=[2], new_observations=0), [], fixture_calculation, 11)
            with self.assertRaisesRegex(ValueError, 'observation budget'):
                p.run('observation_blocked', dict(seed=[2], new_observations=2), [], fixture_calculation, 10)

    def test_source_gate_runs_before_stage_and_preserves_lock(self):
        with self.fixture(), patch.object(p, 'committed_sources', side_effect=ValueError('uncommitted source')):
            with self.assertRaisesRegex(ValueError, 'uncommitted'):
                p.run('uncommitted', dict(seed=[1], new_observations=0), [], fixture_calculation, 10)
            self.assertFalse(p.ARTIFACT.exists())
        with self.fixture():
            p.ARTIFACT.mkdir()
            with (p.ARTIFACT/'.task.lock').open('a') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                with self.assertRaisesRegex(RuntimeError, 'study is active'):
                    p.run('locked', dict(seed=[1], new_observations=0), [], fixture_calculation, 10)
            self.assertFalse((p.ARTIFACT/'locked').exists())

    def test_actual_uncommitted_new_package_file_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=p.PACKAGE) as directory:
            path = Path(directory)/'uncommitted.py'
            path.write_text('artificial_fixture = True\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted study source'):
                p.committed_sources([path])


if __name__ == '__main__':
    unittest.main()
