"""Contract tests and real generator/pilot checks; no production F/E/T calls."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from .budgeted_support_diagnostics import array_hash
from .e1_ldpc import build_code
from .supplement_data import SupplementData
from .supplement_pilot_frames import pilot_frames
from . import supplement_scene_candidates as scene


def inputs_root():
    return Path(os.environ['AFDM_TEST_SCENE_INPUTS'])


def load_inputs():
    root = inputs_root()
    freeze = json.loads((root/'candidate-freeze.json').read_text())
    inputs = {k: json.loads((root/name).read_text()) for k, name in scene.INPUT_FILES.items() if k != 'pilot_npz'}
    return freeze, inputs


class Contracts(unittest.TestCase):
    def test_all_frozen_candidates_and_exact_aliases(self):
        freeze, inputs = load_inputs()
        arms = scene.validate_freeze(freeze, inputs)
        self.assertEqual(len(arms), 12)
        self.assertEqual(len(freeze['symbolic_aliases']), 15)
        batches = [scene.identities(0, 1, arms)]
        batches += [scene.identities(b, min(b+16, 192), arms) for b in range(1, 192, 16)]
        ids = [x for batch in batches for x in batch]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 13824)
        self.assertEqual(scene.full_calls(ids), 12768)
        self.assertEqual(scene.full_calls(batches[0]), 72)
        self.assertEqual(sum(a == 'Bstar' and b < 16 for b, _, _, a in ids), 96)

    def test_frozen_method_and_power_schedule_changes_rejected(self):
        freeze, inputs = load_inputs()
        for kind in ('missing', 'lambda', 'pilot', 'alias', 'multiplicity', 'feedback'):
            with self.subTest(kind=kind):
                value = copy.deepcopy(freeze)
                if kind == 'missing':
                    del value['physical_arms']['diagonal']
                elif kind == 'lambda':
                    value['physical_arms']['soft']['recipe'] = 'A02-soft-lambda0.01'
                elif kind == 'pilot':
                    value['physical_arms']['Pmatched-p1']['pilot'] = 'p0'
                elif kind == 'alias':
                    value['symbolic_aliases']['Pfixed:p2'] = 'Pfixed-p1'
                elif kind == 'multiplicity':
                    value['m'] = 15
                else:
                    value['physical_arms']['I1']['outer_BP'] = 20
                with self.assertRaises(ValueError):
                    scene.validate_freeze(value, inputs)

    def test_duplicate_reservation_and_changed_binding_rejected(self):
        freeze, _ = load_inputs()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ids = scene.identities(0, 1, freeze['physical_arms'])
            scene.reserve(root/'first', ids, {'source': 'frozen'})
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                scene.reserve(root/'duplicate', ids, {'source': 'frozen'})
            with self.assertRaisesRegex(ValueError, 'bindings changed'):
                scene.reserve(root/'changed', scene.identities(1, 2, freeze['physical_arms']), {'source': 'changed'})
            receipt = next((root/'candidate-ledger').glob('reservation-*.json'))
            row = json.loads(receipt.read_text()); row['F'] -= 1
            receipt.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'history'):
                scene.reserve(root/'tampered', scene.identities(1, 2, freeze['physical_arms']), {'source': 'frozen'})

    def test_receiver_dispatch_does_not_receive_truth(self):
        freeze, _ = load_inputs()
        observed = {'y': object(), 'pilot': object(), 'sigma2': object(), 'constellation': object()}
        result = {'sentinel': 'result'}
        with patch.object(scene, 'BaselineReceiver') as factory, \
                patch.object(scene, 'CodeFeedback') as feedback, \
                patch.object(scene, 'UniformBPSchedule') as schedule, \
                patch.object(scene, 'CancellationTransform') as cancellation, \
                patch.object(scene, 'validate_result_audit') as audit:
            factory.return_value.run.return_value = result
            for descriptor in freeze['physical_arms'].values():
                factory.reset_mock(); feedback.reset_mock(); schedule.reset_mock(); cancellation.reset_mock(); audit.reset_mock()
                self.assertIs(scene.run_arm('model', 'code', 'system', descriptor, observed), result)
                args, kwargs = factory.return_value.run.call_args
                self.assertEqual(args, (observed,))
                self.assertEqual(set(kwargs)-{'audit'},
                    {'code_feedback', 'bp_schedule'} if descriptor['interface'] == 'I1' else
                    {'terminal_transform'} if descriptor['interface'] in ('scalar', 'diagonal', 'lowrank') else set())
                if descriptor['interface'] == 'I1':
                    feedback.assert_called_once_with('code', checkpoint=1, control='legal')
                    schedule.assert_called_once_with(outer_bp_iterations=12)
                    audit.assert_called_once_with(result, 'I1')

    def test_existing_baseline_requires_exact_captured_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = dict(block_id=16, SNR=8, unit='integer', recipe_id='B0-p2-s0.5', input_hashes={'y': 'original'})
            p = root/'baseline.json'; p.write_text(json.dumps(row))
            binding = dict(identity=[16, 8, 'integer'], record=scene.file_binding(p), recapture=False)
            frame = SimpleNamespace(metadata=dict(block=16, snr_db=8, scenario='integer', input_hashes={'y': 'original'}))
            self.assertEqual(scene.validate_baseline(frame, binding), row)
            frame.metadata['input_hashes']['y'] = 'different'
            with self.assertRaisesRegex(ValueError, 'producer hashes'):
                scene.validate_baseline(frame, binding)
            p.write_text(json.dumps(dict(row, FER=1)))
            with self.assertRaisesRegex(ValueError, 'hash/size'):
                scene.validate_baseline(frame, binding)

    def test_real_n1024_counterexample_generator_and_pilot_lineage(self):
        root = inputs_root()
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)/'code-cache'; cache.mkdir()
            code = build_code(cache_dir=cache)
            data = SupplementData(root/'data-protocol.json', code)
            with np.load(root/'pilots.npz', allow_pickle=False) as archive:
                pilots = {k: archive[k] for k in archive.files}
            for name in scene.SCENES:
                with self.subTest(scene=name):
                    system = scene.system_for(data.protocol['scenarios'][name])
                    # Engineering namespace: no new production or independent confirmation cell.
                    f = data.make_frame(system, 'engineering', 0, 8, scenario=name)
                    frames = pilot_frames(f, pilots, c1=system.c1, c2=system.c2, preserve_original_p0=True)
                    self.assertEqual(f.metadata['generator'], 'truncated_daft')
                    for g in frames.values():
                        self.assertEqual(g.metadata['scenario'], name)
                        for k in ('H', 'data', 'noise', 'info', 'coded'):
                            self.assertEqual(array_hash(g._truth[k]), f.metadata['input_hashes'][k])
                        expected = g._truth['H']@(g.observed['pilot']+g._truth['data']) + np.sqrt(g.observed['sigma2'])*g._truth['noise']
                        np.testing.assert_allclose(g.observed['y'], expected, rtol=1e-12, atol=1e-12)
                    np.testing.assert_array_equal(frames['p0'].observed['y'], f.observed['y'])


if __name__ == '__main__':
    unittest.main()
