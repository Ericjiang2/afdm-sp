"""Recorder fixtures only; these tests do not generate research observations."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.afdm_method_advantage import protocol as p
from experiments.afdm_efficient_information import protocol as original


def fixture_calculation(output):
    p.dump(output / 'fixture.json', {'fixture': True})
    return {'fixture': True}


class ProtocolTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission = root / 'mission'
            mission.mkdir()
            (mission / 'run_contract.json').write_text(json.dumps(dict(
                max_wall_seconds=10, max_total_reserved_wall_seconds=15,
                max_new_development_observations=3, output_limit_bytes=1000000)))
            with patch.object(p, 'MISSION', mission), patch.object(p, 'ARTIFACT', root/'out'), \
                    patch.object(p, 'committed_sources', return_value={'head': 'fixture'}):
                yield

    def test_private_admission_and_duplicate_rejection(self):
        old = (original.MISSION, original.ARTIFACT, original.PACKAGE)
        with self.fixture():
            p.run('fixture', {'seed': [1], 'new_observations': 0}, [], fixture_calculation, 10)
            result = json.loads((p.ARTIFACT/'fixture/attempt.json').read_text())
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['reserved_wall_seconds'], 10)
            with self.assertRaises(FileExistsError):
                p.run('fixture', {'seed': [1], 'new_observations': 0}, [], fixture_calculation, 10)
            with self.assertRaisesRegex(ValueError, 'total reserved wall'):
                p.run('overbudget', {'seed': [1], 'new_observations': 0}, [], fixture_calculation, 10)
        self.assertEqual(old, (original.MISSION, original.ARTIFACT, original.PACKAGE))

    def test_uncommitted_source_rejected_before_new_observations(self):
        with self.fixture(), patch.object(p, 'committed_sources', side_effect=ValueError('uncommitted')):
            with self.assertRaisesRegex(ValueError, 'uncommitted'):
                p.run('rejected', {'seed': [1], 'new_observations': 3}, [], fixture_calculation, 10)
            self.assertFalse(p.ARTIFACT.exists())

    def test_new_package_source_is_actually_checked(self):
        with tempfile.TemporaryDirectory(dir=p.PACKAGE) as directory:
            path = Path(directory)/'uncommitted.py'
            path.write_text('fixture = True\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted study source'):
                p.committed_sources([path])


if __name__ == '__main__':
    unittest.main()
