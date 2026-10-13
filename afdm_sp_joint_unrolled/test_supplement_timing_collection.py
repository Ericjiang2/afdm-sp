"""Fake-only tests for the COST-02 pilot/formal timing collector."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled import supplement_timing as timing


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, sort_keys=True))
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Frame:
    pass


class FakeTimingHooks:
    def __init__(self, *, telemetry=None, mutate_source=False,
                 mutate_input=False):
        self.events = []
        self.source = {'supplement_timing.py': 'a' * 64}
        self.telemetry_values = list(telemetry or [])
        self.mutate_source = mutate_source
        self.mutate_input = mutate_input
        self.run_count = 0
        self.build_count = 0

    def cuda_available(self):
        return True

    def configure(self, device):
        self.events.append(('configure', device))

    def sources(self):
        return copy.deepcopy(self.source)

    def prepare_timing(self, args, manifest):
        self.events.append(('prepare',))
        return {'code': {'G': np.zeros((8, 4), np.uint8),
                         'H': np.zeros((4, 8), np.uint8), 'k': 4, 'n': 8},
                'code_sha256': {'G': 'g' * 64, 'H': 'h' * 64}}

    def make_timing_frame(self, args, context, snr, block, symbol,
                          manifest):
        self.events.append(('generate', snr, block, symbol))
        observed = {'y': np.ones(4), 'pilot': np.ones(4),
                    'sigma2': np.array(1.), 'constellation': np.ones(4)}
        frame = Frame()
        frame.observed = observed
        frame.metadata = {
            'campaign_id': timing.CAMPAIGN_ID, 'split': 'timing',
            'block': block, 'snr_db': snr, 'family': 'F_C',
            'arm_id': symbol, 'scenario': 'G0',
            'protocol_sha256': timing.sha(args.protocol),
            'input_hashes': {'y': timing.array_hash(observed['y']),
                             'pilot': timing.array_hash(observed['pilot'])},
            'confirmation_authority': {
                'manifest_sha256': args.timing_manifest_sha256,
                'timing_purpose': manifest['timing_purpose']}}
        return frame

    def build_timing(self, symbol, context, snr, prior_path):
        self.build_count += 1
        token = self.build_count
        self.events.append(('build', symbol, token, snr,
                            str(prior_path)))
        parent = self

        class Receiver:
            def run(self, observed, *, audit):
                parent.run_count += 1
                parent.events.append(('run', symbol, token, audit))
                if parent.mutate_source:
                    parent.source['supplement_timing.py'] = 'b' * 64
                if parent.mutate_input:
                    observed['y'][0] += 1
                return {'H': np.eye(4), 'sigma2': 1.,
                    'sigma2_terminal': 1., 'x_soft': np.ones(4),
                    'llr': np.ones(8), 'x_hard': np.ones(4, complex),
                    'decoded': np.zeros(8, np.uint8),
                    'info_hat': np.zeros(4, np.uint8), 'support': [0],
                    'graphs': [], 'support_trace': [], 'dals': []}
        return Receiver()

    def sync(self, device):
        self.events.append(('sync', device))

    def telemetry(self, device):
        self.events.append(('telemetry', device))
        if self.telemetry_values:
            return self.telemetry_values.pop(0)
        return {'status': 'ok', 'gpu_uuid': timing.TIMING_GPU_UUID,
                'compute_pids': [os.getpid()], 'observed_unix': time.time()}


class TimingCollectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.protocol = self.root / 'data.json'
        self.checkpoint = self.root / 'checkpoint'
        self.freeze = self.root / 'representative.json'
        self.global_freeze = self.root / 'global-freeze.json'
        self.prior = self.root / 'prior8.pt'
        for path, data in ((self.protocol, b'protocol'),
                           (self.checkpoint, b'checkpoint'),
                           (self.freeze, b'representative'),
                           (self.prior, b'prior8')):
            write(path, data)
        write(self.global_freeze, {
            'schema':'afdm-supplement-global-freeze-v1',
            'status':'GLOBAL_FROZEN_NOT_FAMILY_ADMISSION',
            'campaign_id':timing.CAMPAIGN_ID, 'alpha_total':.05,
            'family_m':{'F_C':102},
            'data_protocol':{'sha256':timing.sha(self.protocol)}})
        self.manifest = self.root / 'manifest.json'
        self.manifest_value = {
            'schema': 'COST02-timing-collection-manifest-v1',
            'status': 'accepted_for_collection',
            'campaign_id': timing.CAMPAIGN_ID, 'issue': 'COST-02',
            'family': 'F_C', 'scenario': 'G0',
            'timing_purpose': 'timing-pilot', 'proceed_timing': True,
            'protocol_sha256': timing.sha(self.protocol),
            'global_freeze_sha256': timing.sha(self.global_freeze),
            'checkpoint_sha256': timing.sha(self.checkpoint),
            'representative_freeze_sha256': timing.sha(self.freeze),
            'source_manifest': {'supplement_timing.py': 'a' * 64},
            'arm_ids': list(timing.TIMING_SYMBOLS),
            'requested_snr_cells': [8],
            'n_by_snr': {'7': 1, '8': 2, '9': 1},
            'warmup_by_snr': {'7': 0, '8': 1, '9': 0},
            'block_start': 0,
            'ledger_path': str(self.root / 'timing-ledger'),
            'runtime_admitted_unix': time.time(),
            'runtime_deadline_unix': time.time() + 300,
            'prior_by_snr': {'8': {'path': str(self.prior),
                'sha256': timing.sha(self.prior)}},
            'order_rule': timing.TIMING_ORDER_RULE,
            'calls': {'F': 9, 'T': 0, 'E': 0},
            'timing_family_cap_F': 9,
            'measurement_boundary': timing.TIMING_BOUNDARY,
            'resource_limits': {'cpu_threads': 1,
                'cuda_allocator_fraction': .25,
                'gpu_uuid': timing.TIMING_GPU_UUID,
                'max_output_bytes': 256 * 1024**2,
                'deadline_seconds': 1800, 'host_cpu_headroom_cores': 16,
                'minimum_disk_free_bytes': 256 * 1024**2}}
        self.sign_manifest(self.manifest_value)
        self.manifest_sha = write(self.manifest, self.manifest_value)

    def args(self, **changes):
        values = dict(protocol=self.protocol, checkpoint=self.checkpoint,
            representative_freeze=self.freeze,
            representative_freeze_sha256=timing.sha(self.freeze),
            global_freeze=self.global_freeze,
            global_freeze_sha256=timing.sha(self.global_freeze),
            timing_manifest=self.manifest,
            timing_manifest_sha256=self.manifest_sha,
            timing_ledger=self.root / 'timing-ledger',
            out=self.root / 'out',
            deadline_unix=self.manifest_value['runtime_deadline_unix'],
            max_output_bytes=256 * 1024**2, device='cuda:0',
            allow_cpu=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def update_manifest(self, change):
        value = copy.deepcopy(self.manifest_value)
        change(value)
        self.sign_manifest(value)
        self.manifest_value = value
        self.manifest_sha = write(self.manifest, value)

    def sign_manifest(self, value):
        request_sha = timing.timing_request_sha256(value)
        authorization = self.root / ('authorization-' + request_sha + '.json')
        auth_sha = write(authorization, {
            'schema':timing.TIMING_AUTHORIZATION_SCHEMA,
            'status':'accepted', 'source':'test fixture',
            'authorized':['F_C:'+value['timing_purpose']],
            'request_sha256':request_sha})
        value['authorization']={'status':'accepted',
            'evidence_path':str(authorization),'evidence_sha256':auth_sha}

    def test_pilot_collects_deterministic_order_and_isolated_models(self):
        hooks = FakeTimingHooks()
        self.assertEqual(timing.execute_timing(self.args(), hooks=hooks), 0)
        receipt = json.loads((self.root / 'out/complete.json').read_text())
        self.assertEqual(receipt['calls'], {'F': 9, 'T': 0, 'E': 0})
        self.assertEqual(receipt['measured_n_by_snr'], {'8': 2})
        self.assertEqual(receipt['uncollected_snr_cells'], [7, 9])
        self.assertEqual(len(receipt['measured_records']), 6)
        self.assertEqual(len(receipt['warmup_records']), 3)
        builds = [event for event in hooks.events if event[0] == 'build']
        self.assertEqual(len({event[2] for event in builds}), 9)
        for index, event in enumerate(hooks.events):
            if event[0] == 'run':
                self.assertEqual(hooks.events[index - 1][0], 'sync')
                self.assertEqual(hooks.events[index + 1][0], 'sync')
        orders = sorted((self.root / 'out').glob('order-*.json'))
        self.assertEqual(len(orders), 3)
        self.assertEqual(json.loads(orders[1].read_text())['order'],
                         timing.timing_order(8, 0))

    def test_missing_or_tampered_manifest_rejects_before_generation(self):
        for args in (self.args(timing_manifest=self.root / 'missing'),
                     self.args(timing_manifest_sha256='0' * 64)):
            hooks = FakeTimingHooks()
            with self.assertRaisesRegex(ValueError, 'manifest'):
                timing.execute_timing(args, hooks=hooks)
            self.assertFalse(any(event[0] == 'generate'
                                 for event in hooks.events))

    def test_unsupported_arm_and_missing_snr_prior_reject(self):
        self.update_manifest(lambda value: value['arm_ids'].append('A02-group'))
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            timing.execute_timing(self.args(), hooks=FakeTimingHooks())
        self.update_manifest(lambda value: (value.update(
            arm_ids=list(timing.TIMING_SYMBOLS), requested_snr_cells=[7]),
            value.update(calls={'F': 3, 'T': 0, 'E': 0})))
        with self.assertRaisesRegex(ValueError, 'prior'):
            timing.execute_timing(self.args(out=self.root / 'prior-fail'),
                                  hooks=FakeTimingHooks())

    def test_formal_overlap_and_small_formal_count_reject(self):
        self.update_manifest(lambda value: value.update(
            timing_purpose='timing-confirmation', block_start=0,
            pilot_manifest_path='missing.json',
            pilot_manifest_sha256='0' * 64))
        with self.assertRaisesRegex(ValueError, 'formal'):
            timing.execute_timing(self.args(), hooks=FakeTimingHooks())

    def test_duplicate_reservation_and_cap_reject(self):
        first = self.args()
        timing.execute_timing(first, hooks=FakeTimingHooks())
        with self.assertRaisesRegex((FileExistsError, ValueError),
                                   'exists|reservation'):
            timing.execute_timing(self.args(out=self.root / 'second'),
                                  hooks=FakeTimingHooks())

    def test_deadline_storage_cuda_and_telemetry_reject(self):
        cases = [
            (self.args(deadline_unix=time.time() - 1), FakeTimingHooks(),
             'deadline'),
            (self.args(max_output_bytes=1), FakeTimingHooks(), 'storage'),
            (self.args(device='cpu', allow_cpu=False), FakeTimingHooks(),
             'explicit'),
            (self.args(), FakeTimingHooks(telemetry=[{'status': 'ambiguous'}]),
             'telemetry'),
            (self.args(), FakeTimingHooks(telemetry=[{'status': 'ok',
                'gpu_uuid': timing.TIMING_GPU_UUID,
                'compute_pids': [999999]}]), 'foreign')]
        for index, (args, hooks, message) in enumerate(cases):
            args.out = self.root / ('reject-' + str(index))
            with self.subTest(message=message):
                with self.assertRaisesRegex((ValueError, TimeoutError,
                                             OSError), message):
                    timing.execute_timing(args, hooks=hooks)
                self.assertEqual(hooks.run_count, 0)

    def test_source_and_input_mutation_publish_bounded_failure(self):
        for label, hooks in [('source', FakeTimingHooks(mutate_source=True)),
                             ('input', FakeTimingHooks(mutate_input=True))]:
            args = self.args(out=self.root / label,
                             timing_ledger=self.root / (label + '-ledger'))
            manifest = copy.deepcopy(self.manifest_value)
            manifest['ledger_path'] = str(args.timing_ledger.resolve())
            self.sign_manifest(manifest)
            args.timing_manifest = self.root / (label + '-manifest.json')
            args.timing_manifest_sha256 = write(args.timing_manifest, manifest)
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, label):
                    timing.execute_timing(args, hooks=hooks)
                failure = json.loads((args.out / 'failure.json').read_text())
                self.assertEqual(failure['status'], 'invalid_incomplete')
                self.assertEqual(failure['calls']['F'], 1)

    def test_formal_admission_binds_completed_pilot_and_existing_data_authority(self):
        from afdm_sp_joint_unrolled.supplement_data import _confirm_manifest
        timing.execute_timing(self.args(), hooks=FakeTimingHooks())
        completion = self.root/'out/complete.json'
        formal = copy.deepcopy(self.manifest_value)
        formal.update(timing_purpose='timing-confirmation', block_start=2,
            n_by_snr={'7': 1024, '8': 1024, '9': 1024},
            calls={'F': 3075, 'T': 0, 'E': 0}, timing_family_cap_F=3084,
            pilot_manifest_path=str(self.manifest), pilot_manifest_sha256=self.manifest_sha,
            pilot_completion_path=str(completion), pilot_completion_sha256=timing.sha(completion))
        formal['resource_limits'].update(max_output_bytes=16*1024**3,
                                        minimum_disk_free_bytes=16*1024**3)
        self.sign_manifest(formal)
        path = self.root/'formal.json'
        digest = write(path, formal)
        args = self.args(mode='timing-confirmation', timing_manifest=path,
            timing_manifest_sha256=digest, max_output_bytes=16*1024**3,
            out=self.root/'formal-output')
        hooks = FakeTimingHooks()
        checked = timing.validate_timing_request(args, hooks)
        bound = timing._timing_files(args, checked)
        authority = _confirm_manifest({'frozen_manifest_path': str(path),
            'frozen_manifest_sha256': digest}, timing.sha(self.protocol),
            'F_C', 'A2', 2, 8, 'G0', timing_purpose='timing-confirmation')
        self.assertEqual(authority['block_start'], checked['block_start'])
        self.assertEqual(authority['pilot_manifest_sha256'], self.manifest_sha)
        for pattern in ('contract.json', 'record-F-', 'raw-F-',
                        'telemetry-', 'order-', 'authorization-'):
            self.assertTrue(any(pattern in bound_path for bound_path in bound),
                            pattern)
        self.assertEqual(hooks.run_count, 0)
        self.assertFalse(args.out.exists())
        raw = next((self.root/'out').glob('raw-*.npz'))
        raw.write_bytes(b'corrupted pilot raw')
        with self.assertRaisesRegex(ValueError, 'pilot raw'):
            timing.validate_timing_request(args, hooks)

    def test_post_block_contamination_preserves_partial_outputs_and_reservation(self):
        okay = {'status': 'ok', 'gpu_uuid': timing.TIMING_GPU_UUID,
                'compute_pids': [os.getpid()], 'observed_unix': time.time()}
        foreign = {**okay, 'compute_pids': [999999]}
        hooks = FakeTimingHooks(telemetry=[okay, okay, foreign])
        args = self.args()
        with self.assertRaisesRegex(ValueError, 'foreign'):
            timing.execute_timing(args, hooks=hooks)
        failure = json.loads((args.out/'failure.json').read_text())
        self.assertEqual(hooks.run_count, 3)
        self.assertEqual(failure['calls']['F'], 3)
        self.assertEqual(len(list(args.out.glob('raw-*.npz'))), 3)
        self.assertFalse((args.out/'complete.json').exists())
        ledger = json.loads(Path(failure['reservation']['path']).read_text())
        self.assertEqual(ledger['calls_reserved']['F'], 9)
        self.assertTrue(failure['failure_receipt_compacted'])
        self.assertEqual(failure['telemetry_records']['count'], 3)
        self.assertEqual(failure['records']['count'], 3)
        self.assertEqual(failure['last_started']['identity']['ordinal'], 3)

    def test_large_partial_collection_keeps_compact_failure_receipt(self):
        groups = 30
        calls = groups * len(timing.TIMING_SYMBOLS)
        limit = (calls * timing.PER_TIMING_CALL_ESTIMATE_BYTES +
                 timing.TIMING_SCRATCH_BYTES +
                 timing.TIMING_AUXILIARY_RESERVE_BYTES +
                 timing.FAILURE_RESERVE_BYTES + 1024**2)
        self.update_manifest(lambda value: (
            value['n_by_snr'].update({'8': groups}),
            value['warmup_by_snr'].update({'8': 0}),
            value.update(calls={'F': calls, 'T': 0, 'E': 0},
                         timing_family_cap_F=calls),
            value['resource_limits'].update(
                max_output_bytes=limit, minimum_disk_free_bytes=limit)))
        okay = {'status': 'ok', 'gpu_uuid': timing.TIMING_GPU_UUID,
                'compute_pids': [os.getpid()], 'observed_unix': time.time()}
        foreign = {**okay, 'compute_pids': [999999]}
        hooks = FakeTimingHooks(telemetry=[okay] * (2 * groups) + [foreign])
        args = self.args(max_output_bytes=limit)
        with self.assertRaisesRegex(ValueError, 'foreign'):
            timing.execute_timing(args, hooks=hooks)
        failure_path = args.out / 'failure.json'
        failure = json.loads(failure_path.read_text())
        self.assertLess(failure_path.stat().st_size,
                        timing.FAILURE_RESERVE_BYTES)
        self.assertEqual(failure['records']['count'], calls)
        self.assertEqual(failure['telemetry_records']['count'], 2*groups+1)
        self.assertEqual(failure['order_records']['count'], groups)
        self.assertEqual(failure['records']['complete_originals_preserved_as'],
                         'record-F-*.json and raw-F-*.npz')
        self.assertEqual(len(list(args.out.glob('record-F-*.json'))), calls)
        self.assertEqual(len(list(args.out.glob('raw-F-*.npz'))), calls)
        self.assertEqual(failure['last_started']['identity']['ordinal'], calls)

    def test_allocation_and_prior_mismatch_are_rejected_before_generation(self):
        hooks = FakeTimingHooks()
        with self.assertRaisesRegex(ValueError, 'ledger'):
            timing.execute_timing(self.args(timing_ledger=self.root/'other-ledger'), hooks=hooks)
        self.prior.write_bytes(b'changed calibration')
        with self.assertRaisesRegex(ValueError, 'prior'):
            timing.execute_timing(self.args(), hooks=hooks)
        self.assertFalse(any(event[0] == 'generate' for event in hooks.events))

    def test_cuda_disk_and_exclusive_lock_fail_before_numerical_work(self):
        hooks = FakeTimingHooks()
        with patch.object(hooks, 'cuda_available', return_value=False):
            with self.assertRaisesRegex(ValueError, 'CUDA unavailable'):
                timing.execute_timing(self.args(), hooks=hooks)
        with patch.object(timing.shutil, 'disk_usage') as disk:
            disk.return_value.free = 0
            with self.assertRaisesRegex(OSError, 'disk'):
                timing.execute_timing(self.args(out=self.root/'disk'), hooks=hooks)
        with patch.object(timing.fcntl, 'flock', side_effect=BlockingIOError):
            with self.assertRaisesRegex(ValueError, 'device lane'):
                timing.execute_timing(self.args(out=self.root/'locked'), hooks=hooks)
        self.assertEqual(hooks.run_count, 0)
        self.assertFalse(any(event[0] == 'generate' for event in hooks.events))

    def test_preparation_cannot_rebind_changed_input(self):
        hooks = FakeTimingHooks()
        prepare = hooks.prepare_timing
        def mutate(args, manifest):
            context = prepare(args, manifest)
            self.checkpoint.write_bytes(b'changed during setup')
            return context
        hooks.prepare_timing = mutate
        with self.assertRaisesRegex(ValueError, 'input file changed'):
            timing.execute_timing(self.args(), hooks=hooks)
        self.assertEqual(hooks.run_count, 0)
        self.assertFalse(any(event[0] == 'generate' for event in hooks.events))

    def test_explicit_real_hooks_cannot_bypass_real_path_gate(self):
        with patch.object(timing, '_real_timing_paths',
                          side_effect=ValueError('real path marker')) as gate:
            with self.assertRaisesRegex(ValueError, 'real path marker'):
                timing.execute_timing(self.args(), hooks=timing.RealHooks())
        gate.assert_called_once()

    def test_formal_rejects_changed_checkpoint_and_representative_freeze(self):
        timing.execute_timing(self.args(), hooks=FakeTimingHooks())
        completion = self.root/'out/complete.json'
        base = copy.deepcopy(self.manifest_value)
        base.update(timing_purpose='timing-confirmation', block_start=2,
            n_by_snr={'7':1024,'8':1024,'9':1024},
            calls={'F':3075,'T':0,'E':0}, timing_family_cap_F=3084,
            pilot_manifest_path=str(self.manifest), pilot_manifest_sha256=self.manifest_sha,
            pilot_completion_path=str(completion), pilot_completion_sha256=timing.sha(completion))
        limit=16*1024**3
        base['resource_limits'].update(max_output_bytes=limit,
                                       minimum_disk_free_bytes=limit)
        for field,arg_name in (('checkpoint_sha256','checkpoint'),
                               ('representative_freeze_sha256','representative_freeze')):
            changed=copy.deepcopy(base)
            replacement=self.root/('other-'+arg_name)
            write(replacement,b'different method definition')
            changed[field]=timing.sha(replacement)
            self.sign_manifest(changed)
            path=self.root/('formal-'+arg_name+'.json')
            digest=write(path,changed)
            args=self.args(mode='timing-confirmation',timing_manifest=path,
                timing_manifest_sha256=digest,max_output_bytes=limit,
                out=self.root/('formal-'+arg_name+'-out'))
            setattr(args,arg_name,replacement)
            if arg_name=='representative_freeze':
                args.representative_freeze_sha256=timing.sha(replacement)
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'formal'):
                    timing.validate_timing_request(args,FakeTimingHooks())

    def test_real_formal_rejects_fixture_pilot(self):
        timing.execute_timing(self.args(), hooks=FakeTimingHooks())
        completion = self.root/'out/complete.json'
        formal = copy.deepcopy(self.manifest_value)
        formal.update(timing_purpose='timing-confirmation', block_start=2,
            n_by_snr={'7':1024,'8':1024,'9':1024},
            calls={'F':3075,'T':0,'E':0}, timing_family_cap_F=3084,
            pilot_manifest_path=str(self.manifest),
            pilot_manifest_sha256=self.manifest_sha,
            pilot_completion_path=str(completion),
            pilot_completion_sha256=timing.sha(completion))
        self.sign_manifest(formal)
        with patch.object(timing, '_require_real_path'):
            with self.assertRaisesRegex(ValueError, 'real CUDA pilot'):
                timing._validate_formal_link(
                    formal, self.root/'formal.json', real=True)

    def test_storage_admission_includes_scratch_and_auxiliary_reserve(self):
        limit=13*1024**2
        self.update_manifest(lambda value:(
            value['n_by_snr'].update({'8':1}),
            value['warmup_by_snr'].update({'8':0}),
            value.update(calls={'F':3,'T':0,'E':0},timing_family_cap_F=3),
            value['resource_limits'].update(max_output_bytes=limit,
                                             minimum_disk_free_bytes=limit)))
        hooks=FakeTimingHooks()
        with self.assertRaisesRegex(ValueError,'storage'):
            timing.execute_timing(self.args(max_output_bytes=limit),hooks=hooks)
        self.assertFalse(any(event[0]=='generate' for event in hooks.events))

    def test_per_call_retained_output_bound_is_enforced(self):
        args = self.args()
        with patch.object(timing, 'PER_TIMING_CALL_ESTIMATE_BYTES', 4096):
            with self.assertRaisesRegex(OSError, 'retention bound'):
                timing.execute_timing(args, hooks=FakeTimingHooks())
        failure = json.loads((args.out/'failure.json').read_text())
        self.assertEqual(failure['calls']['F'], 1)
        self.assertTrue((args.out/'raw-F-000001.npz').exists())
        self.assertTrue((args.out/'record-F-000001.json').exists())

    def test_global_freeze_and_exact_authorization_signature(self):
        value=json.loads(self.global_freeze.read_text())
        value['family_m']['F_C']=101
        global_sha=write(self.global_freeze,value)
        self.update_manifest(lambda manifest:manifest.update(
            global_freeze_sha256=global_sha))
        with self.assertRaisesRegex(ValueError,'global freeze'):
            timing.validate_timing_request(self.args(
                global_freeze_sha256=global_sha),FakeTimingHooks())

        self.setUp()
        manifest=copy.deepcopy(self.manifest_value)
        manifest['runtime_admitted_unix']-=1
        self.manifest_sha=write(self.manifest,manifest)
        with self.assertRaisesRegex(ValueError,'authorization'):
            timing.validate_timing_request(self.args(),FakeTimingHooks())

    def test_real_indirect_paths_and_cpu_observation_contract(self):
        self.update_manifest(lambda m: m['prior_by_snr']['8'].update(
            path='/data/not-this-campaign-owner/nonexistent-prior.pt'))
        with self.assertRaisesRegex(ValueError,'prior'):
            timing.validate_timing_request(self.args(),FakeTimingHooks(),
                                           real=True)
        telemetry={'status':'ok','gpu_uuid':timing.TIMING_GPU_UUID,
            'compute_pids':[os.getpid()],'observed_unix':time.time(),
            'cpu_count':64,'load_average':[0.,0.,0.],
            'cpu_affinity':[0,1],'numerical_threads':1,'interop_threads':1,
            'memory_free_MiB':8192,'memory_used_MiB':1,
            'utilization_percent':0}
        timing._check_telemetry(telemetry,real=True)
        telemetry.pop('cpu_affinity')
        with self.assertRaisesRegex(ValueError,'CPU telemetry'):
            timing._check_telemetry(telemetry,real=True)

    def test_real_reservation_rejects_external_prior_manifest_path(self):
        ledger = self.root/'existing-ledger'
        ledger.mkdir()
        write(ledger/'reservation-old.json', {
            'schema':'COST02-timing-reservation-v1',
            'campaign_id':timing.CAMPAIGN_ID,
            'manifest_path':'/data/not-this-campaign-owner/nonexistent-manifest.json',
            'manifest_sha256':self.manifest_sha})
        manifest = copy.deepcopy(self.manifest_value)
        manifest['_manifest_path'] = str(self.manifest)
        with self.assertRaisesRegex(ValueError, 'reserved timing manifest'):
            timing.reserve_timing(ledger, self.root/'new-output',
                self.manifest_sha, manifest, 'c'*64, real=True)


if __name__ == '__main__':
    unittest.main()
