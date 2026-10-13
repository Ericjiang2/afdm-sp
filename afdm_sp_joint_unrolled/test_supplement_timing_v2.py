"""Full-role collector integration with fake receivers and frozen A/I/P inputs."""
import copy
import json
import time
import unittest
from unittest.mock import patch

import numpy as np

from . import supplement_timing as timing
from . import supplement_timing_integrity as integrity
from . import test_supplement_timing_collection as fixtures
from .supplement_scene_candidates import INPUT_FILES
from .supplement_timing_catalogue import resolve_catalogue
from .test_supplement_scene_candidates import inputs_root, load_inputs


class FullHooks(fixtures.FakeTimingHooks):
    def __init__(self, change=None):
        super().__init__()
        self.change = change

    def make_timing_frame(self, args, context, snr, block, symbol, manifest):
        frame = super().make_timing_frame(args, context, snr, block, symbol, manifest)
        pilot = manifest['catalogue']['methods'][symbol]['pilot']
        frame.observed['y'] *= int(pilot[-1])+1
        frame.observed['pilot'] *= int(pilot[-1])+1
        frame._truth = {'H': np.eye(4), 'data': np.ones(4), 'noise': np.zeros(4),
                        'info': np.zeros(4, np.uint8), 'coded': np.zeros(8, np.uint8)}
        if self.change is not None and symbol == 'B0':
            if self.change in frame._truth:
                frame._truth[self.change] = frame._truth[self.change]+1
            else:
                frame.observed[self.change] = frame.observed[self.change]+1
        frame.metadata['pilot_id'] = pilot
        frame.metadata['power'] = {'passes_declared_simulation_power_gate': True,
                                   'fixture_only': True}
        frame.metadata['input_hashes'].update({k: timing.array_hash(v)
            for k, v in {**frame._truth, **frame.observed}.items()})
        return frame


class FullCollectorContracts(unittest.TestCase):
    def setUp(self):
        f = self.f = fixtures.TimingCollectionTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        root = inputs_root()
        freeze, inputs = load_inputs()
        f.freeze = root/'A02-representatives.json'
        global_value = json.loads(f.global_freeze.read_text())
        global_value['global_manifest'] = {'sha256': timing.sha(root/'global-contrast-manifest.json')}
        fixtures.write(f.global_freeze, global_value)
        f.update_manifest(lambda m: m.update(global_freeze_sha256=timing.sha(f.global_freeze),
            representative_freeze_sha256=timing.sha(f.freeze)))
        self.old = {'path': str(f.manifest), 'sha256': f.manifest_sha}
        self.value = copy.deepcopy(f.manifest_value)
        def bind(path):
            return {'path': str(path), 'sha256': timing.sha(path)}
        catalogue = resolve_catalogue(freeze, inputs)
        self.value.update(schema='COST02-timing-collection-manifest-v2',
            catalogue=catalogue, arm_ids=catalogue['arm_ids'],
            selection={'candidate_freeze': bind(root/'candidate-freeze.json'),
                       'inputs': {key: bind(root/name) for key, name in INPUT_FILES.items()}},
            excluded_manifests=[self.old], block_start=2,
            calls={'F': 45, 'T': 0, 'E': 0}, timing_family_cap_F=54)
        self.value['resource_limits'].update(max_output_bytes=512*1024**2,
                                             minimum_disk_free_bytes=512*1024**2)
        self.path = f.root/'v2-pilot.json'
        self.save()

    def save(self):
        self.f.sign_manifest(self.value)
        self.digest = fixtures.write(self.path, self.value)

    def args(self, **changes):
        return self.f.args(timing_manifest=self.path, timing_manifest_sha256=self.digest,
            max_output_bytes=self.value['resource_limits']['max_output_bytes'],
            deadline_unix=self.value['runtime_deadline_unix'], **changes)

    def reserve_old(self):
        # Reserving without running demonstrates that unused history still excludes data.
        value = copy.deepcopy(self.f.manifest_value)
        value['_manifest_path'] = str(self.f.manifest)
        timing.reserve_timing(self.f.root/'timing-ledger', self.f.root/'old-output',
            self.f.manifest_sha, value, 'f'*64)

    def test_full_collection_covers_alias_targets_and_pilot_specific_pairing(self):
        self.reserve_old()
        hooks = FullHooks()
        self.assertEqual(timing.execute_timing(self.args(), hooks=hooks), 0)
        complete = json.loads((self.f.root/'out/complete.json').read_text())
        self.assertEqual(complete['calls']['F'], 45)
        self.assertEqual(complete['measured_n_by_snr'], {'8': 2})
        symbols = {r['identity']['symbol'] for r in complete['measured_records']}
        self.assertEqual(symbols, set(self.value['arm_ids']))
        self.assertFalse(symbols & set(self.value['catalogue']['aliases']))
        for i, event in enumerate(hooks.events):
            if event[0] == 'run':
                self.assertEqual(hooks.events[i-1][0], 'sync')
                self.assertEqual(hooks.events[i+1][0], 'sync')
        self.assertEqual(complete['catalogue'], self.value['catalogue'])
        self.assertFalse(complete['deployment_cost_pass'])

    def test_ledger_omission_and_unreserved_exclusion_fail_before_calls(self):
        with self.assertRaisesRegex(ValueError, 'history|exclusion'):
            timing.execute_timing(self.args(), hooks=FullHooks())
        self.reserve_old()
        self.value.update(block_start=0, excluded_manifests=[])
        self.save()
        hooks = FullHooks()
        with self.assertRaisesRegex(ValueError, 'history|exclusion'):
            timing.execute_timing(self.args(out=self.f.root/'omitted'), hooks=hooks)
        self.assertEqual(hooks.run_count, 0)

    def test_metadata_collision_cannot_publish_success_with_changed_checkpoint(self):
        self.reserve_old()
        hooks = FullHooks()
        prepare = hooks.prepare_timing
        checkpoint = self.f.checkpoint
        original_signature = integrity._signature(checkpoint)
        real_signature = integrity._signature

        def mutate(args, manifest):
            context = prepare(args, manifest)
            checkpoint.write_bytes(b'Checkpoint')
            return context

        def signature(path):
            return original_signature if path == checkpoint else real_signature(path)

        hooks.prepare_timing = mutate
        with patch.object(integrity, '_signature', side_effect=signature):
            with self.assertRaisesRegex(ValueError, 'content changed'):
                timing.execute_timing(self.args(), hooks=hooks)
        self.assertEqual(hooks.run_count, 45)
        out = self.f.root/'out'
        self.assertFalse((out/'complete.json').exists())
        failure = json.loads((out/'failure.json').read_text())
        self.assertEqual(failure['status'], 'invalid_incomplete')
        self.assertEqual(failure['calls'], {'F': 45, 'E': 0, 'T': 0})

    def test_formal_binds_complete_v2_pilot_and_all_historical_files(self):
        from .supplement_data import _confirm_manifest
        self.reserve_old()
        timing.execute_timing(self.args(), hooks=FullHooks())
        completion = self.f.root/'out/complete.json'
        pilot_path, pilot_digest = self.path, self.digest
        self.value.pop('excluded_manifests')
        self.value.update(timing_purpose='timing-confirmation', block_start=4,
            n_by_snr={'7': 1024, '8': 1024, '9': 1024},
            calls={'F': 15375, 'T': 0, 'E': 0}, timing_family_cap_F=15429,
            pilot_manifest_path=str(pilot_path), pilot_manifest_sha256=pilot_digest,
            pilot_completion_path=str(completion), pilot_completion_sha256=timing.sha(completion))
        self.value['resource_limits'].update(max_output_bytes=64*1024**3,
                                             minimum_disk_free_bytes=64*1024**3)
        self.path = self.f.root/'v2-formal.json'
        self.save()
        checked = timing.validate_timing_request(self.args(), FullHooks())
        bound = timing._timing_files(self.args(), checked)
        self.assertIn(self.old['path'], bound)
        self.assertIn(str(pilot_path), bound)
        self.assertEqual(len(checked['_excluded_manifest_bindings']), 2)
        token = {'frozen_manifest_path': str(self.path), 'frozen_manifest_sha256': self.digest}
        authority = _confirm_manifest(token, self.value['protocol_sha256'],
            'F_C', 'Pfixed:p1', 4, 8, 'G0', timing_purpose='timing-confirmation')
        self.assertEqual(authority['block_start'], 4)
        raw = next((self.f.root/'out').glob('raw-*.npz'))
        raw.write_bytes(b'changed pilot result')
        with self.assertRaisesRegex(ValueError, 'pilot raw'):
            timing.validate_timing_request(self.args(), FullHooks())

    def test_changed_common_inputs_or_same_pilot_observation_stop(self):
        self.reserve_old()
        for field in ('H', 'noise', 'sigma2', 'constellation', 'y', 'pilot'):
            hooks = FullHooks(change=field)
            # Each failure has its own local ledger but the identical signed ancestry.
            with self.subTest(field=field):
                if field != 'H':
                    self.setUp()
                    self.reserve_old()
                with self.assertRaisesRegex(ValueError, 'paired'):
                    timing.execute_timing(self.args(), hooks=hooks)
                self.assertFalse((self.f.root/'out/complete.json').exists())

    def test_catalogue_and_source_bindings_reject_before_generation(self):
        for kind in ('alias', 'recipe', 'source', 'contrast'):
            value = copy.deepcopy(self.value)
            if kind == 'alias':
                value['catalogue']['aliases']['Pfixed:p0'] = 'B_star_2'
            elif kind == 'recipe':
                value['catalogue']['methods']['old_B_star']['parameters'][2] = 1.
            else:
                key = 'pilot_npz' if kind == 'source' else 'global_contrasts'
                value['selection']['inputs'][key]['sha256'] = '0'*64
            self.f.sign_manifest(value)
            digest = fixtures.write(self.path, value)
            args = self.args()
            args.timing_manifest_sha256 = digest
            hooks = FullHooks()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                timing.validate_timing_request(args, hooks)
            self.assertEqual(hooks.run_count, 0)

    def test_bounded_v2_duration_does_not_relax_v1(self):
        self.value['runtime_admitted_unix'] = time.time()
        self.value['runtime_deadline_unix'] = time.time()+7100
        self.value['resource_limits']['deadline_seconds'] = 7200
        self.save()
        timing.validate_timing_request(self.args(), FullHooks())
        self.value['resource_limits']['deadline_seconds'] = 86401
        self.save()
        with self.assertRaisesRegex(ValueError, 'deadline'):
            timing.validate_timing_request(self.args(), FullHooks())
        with self.assertRaisesRegex(TimeoutError, 'deadline'):
            timing.validate_timing_request(self.f.args(deadline_unix=time.time()+7100), fixtures.FakeTimingHooks())


if __name__ == '__main__':
    unittest.main()
