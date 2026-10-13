"""Synthetic failed-stage recovery; no remote or scientific execution."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


class HarvestFailures(unittest.TestCase):
    def test_failed_and_unfinished_stages_are_kept_without_success_claim(self):
        path = Path(__file__).resolve().parents[2]/'afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007/dispatch/harvest_remote.py'
        spec = importlib.util.spec_from_file_location('fixture_harvest', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for finished in (False, True):
            with self.subTest(finished=finished), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                module.ROOT = root
                (root/'source_v1').mkdir()
                (root/'source_v1/SOURCE_MANIFEST.json').write_text('{"sha256":{}}')
                stage = root/'execution/D'
                stage.mkdir(parents=True)
                registration = dict(config=dict(phase='D', new_observations=0, new_geometry_probes=1056640), wall_cap_seconds=60)
                (stage/'registration.json').write_text(json.dumps(registration))
                (stage/'partial.json').write_text('{"synthetic_failure_evidence":true}')
                if finished:
                    (stage/'attempt.json').write_text(json.dumps(dict(status='failed', exit_code=1, wall_seconds=.25, peak_rss_bytes=2048)))
                with contextlib.redirect_stdout(io.StringIO()):
                    module.main()
                report = json.loads((root/'RESOURCE_RESULTS.json').read_text())
                self.assertFalse(report['all_required_phases_complete'])
                self.assertEqual(report['missing_successful_phases'], ['A', 'D', 'P'])
                self.assertEqual(report['total_registered_observations'], 0)
                self.assertEqual(report['total_stage_wall_seconds'], .25 if finished else None)
                self.assertEqual(report['stages'][0]['status'], 'failed' if finished else 'unfinished')
                with tarfile.open(root/'small_evidence.tar.gz') as archive:
                    self.assertIn('execution/D/partial.json', archive.getnames())


if __name__ == '__main__':
    unittest.main()
