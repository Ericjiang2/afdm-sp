import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.afdm_higher_order_information import protocol as p


class ProtocolContracts(unittest.TestCase):
    def fixture(self,directory):
        root=Path(directory); mission=root/'mission'; mission.mkdir()
        (mission/'run_contract.json').write_text(json.dumps(dict(max_wall_seconds=30,
            max_new_development_observations=5,output_limit_bytes=1000000)))
        return mission,root/'results'

    def test_registration_environment_and_source_before_work(self):
        with tempfile.TemporaryDirectory() as directory:
            mission,artifact=self.fixture(directory)
            def calculate(output):
                self.assertTrue((output/'registration.json').exists())
                self.assertTrue((output/'environment.json').exists())
                self.assertTrue((output/'source_snapshot').is_dir())
                reg=json.loads((output/'registration.json').read_text())
                self.assertEqual(reg['config']['new_observations'],2)
                p.dump(output/'raw.json',dict(fixture=True))
                return dict(fixture=True)
            with patch.object(p,'MISSION',mission),patch.object(p,'ARTIFACT',artifact),patch.object(p,'committed_sources',return_value=dict(head='fixture')):
                p.run('fixture',dict(seed=[1],new_observations=2),[],calculate,wall_seconds=10)
                attempt=json.loads((artifact/'fixture/attempt.json').read_text())
                self.assertEqual(attempt['status'],'complete')
                self.assertTrue(any(k.endswith('/raw.json') for k in attempt['artifact_sha256']))
                with self.assertRaises(FileExistsError): p.run('fixture',dict(seed=[1],new_observations=2),[],calculate,wall_seconds=10)

    def test_failed_work_and_observation_reservation_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            mission,artifact=self.fixture(directory)
            def fail(output): raise RuntimeError('deliberate fixture failure')
            with patch.object(p,'MISSION',mission),patch.object(p,'ARTIFACT',artifact),patch.object(p,'committed_sources',return_value=dict(head='fixture')):
                with self.assertRaisesRegex(RuntimeError,'deliberate'):
                    p.run('failed',dict(seed=[1],new_observations=4),[],fail,wall_seconds=10)
                attempt=json.loads((artifact/'failed/attempt.json').read_text())
                self.assertEqual(attempt['status'],'invalid_partial')
                with self.assertRaisesRegex(ValueError,'observation budget'):
                    p.run('blocked',dict(seed=[1],new_observations=2),[],fail,wall_seconds=10)
                self.assertFalse((artifact/'blocked').exists())

    def test_invalid_allocation_and_source_admission(self):
        for config in (dict(seed=[1]),dict(seed=[1],new_observations=True),dict(seed=[1],new_observations=0,receiver_calls=1)):
            with self.assertRaises(ValueError): p._observations(config)
        with tempfile.TemporaryDirectory(dir=p.PACKAGE) as directory:
            path=Path(directory)/'uncommitted_fixture.py';path.write_text('fixture = 1\n')
            with self.assertRaisesRegex(ValueError,'uncommitted study source'): p.committed_sources([path])


if __name__=='__main__': unittest.main()
