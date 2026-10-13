"""Fake-only contract tests for the COST-02 engineering equivalence entrypoint."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from afdm_sp_joint_unrolled import supplement_timing as timing


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if not isinstance(value, bytes) else '')
    if isinstance(value, bytes):
        path.write_bytes(value)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeHooks:
    def __init__(self, *, cuda=True, perturb=False, mutate_source=False,
                 wrong_frame=False, expire_prepare=False, expire_build=False,
                 nonbinary=False, transpose_code=False):
        self.cuda = cuda
        self.perturb = perturb
        self.mutate_source = mutate_source
        self.wrong_frame = wrong_frame
        self.expire_prepare = expire_prepare
        self.expire_build = expire_build
        self.nonbinary = nonbinary
        self.transpose_code = transpose_code
        self.events = []
        self.reservations = []
        self.tokens = []
        self.source = {'supplement_timing.py': 'a' * 64}

    def cuda_available(self):
        return self.cuda

    def configure(self, device):
        self.events.append(('configure', device))

    def sources(self):
        return copy.deepcopy(self.source)

    def reserve(self, out, contract):
        self.reservations.append(copy.deepcopy(contract['calls_reserved']))
        return str(Path(out).parent / 'supplement-engineering-ledger')

    def prepare(self, args):
        if self.mutate_source:
            self.source['supplement_timing.py'] = 'e' * 64
        if self.expire_prepare:
            args.deadline_unix = timing.time.time() - 1
        observed = {'y': np.ones(4), 'pilot': np.ones(4),
                    'sigma2': np.array(1.), 'constellation': np.ones(4)}
        metadata = {'campaign_id': timing.CAMPAIGN_ID,
                    'split': 'engineering',
                    'block': 1 if self.wrong_frame else 0, 'snr_db': 8,
                    'protocol_sha256': timing.sha(args.protocol),
                    'rng_words': {'channel': [1, 2, 3]}, 'channel_seed': 7,
                    'input_hashes': {
                        'y': timing.array_hash(observed['y']),
                        'pilot': timing.array_hash(observed['pilot'])}}
        code = {'G': np.zeros((4, 8) if self.transpose_code else (8, 4),
                              dtype=np.uint8),
                'H': np.zeros((4, 8), dtype=np.uint8), 'k': 4, 'n': 8}
        return {'frame': type('Frame', (), {'observed': observed,
                                             'metadata': metadata})(),
                'code': code,
                'code_sha256': {'G': 'c' * 64, 'H': 'd' * 64}}

    def build(self, symbol, context):
        if self.expire_build:
            context['args'].deadline_unix = timing.time.time() - 1
        token = object()
        self.tokens.append(token)
        self.events.append(('build', symbol, id(token)))
        parent = self
        class Receiver:
            def run(self, observed, *, audit):
                parent.events.append(('run', symbol, audit, id(token)))
                delta = 2e-5 if parent.perturb and symbol == 'B_star_1' and not audit else 0.
                graphs = [{'stage': 'graph'}] if audit else []
                supports = [{'selected': [0]}] if audit else []
                dals = [{'iteration': index, 'H': np.eye(4)}
                        for index in range(9)] if audit else []
                return {'H': np.eye(4) + delta, 'sigma2': 1.,
                    'sigma2_terminal': 1., 'x_soft': np.ones(4),
                    'llr': np.ones(8), 'x_hard': np.ones(4, complex),
                    'decoded': np.zeros(8, dtype=np.uint8),
                    'info_hat': np.full(4, 2 if parent.nonbinary else 0,
                                        dtype=np.uint8), 'support': [0],
                    'graphs': graphs, 'support_trace': supports, 'dals': dals,
                    'capacity_trace': supports}
        return Receiver()

    def sync(self, device):
        self.events.append(('sync', device))


class TimingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.protocol = self.root / 'data.json'
        self.checkpoint = self.root / 'checkpoint'
        self.prior = self.root / 'prior'
        write(self.protocol, b'data')
        write(self.checkpoint, b'checkpoint')
        write(self.prior, b'prior')
        self.freeze = self.root / 'freeze.json'
        recipes = {
            'B_star_1': timing.expected_freeze_recipe('B_star_1'),
            'B_star_2': timing.expected_freeze_recipe('B_star_2')}
        freeze = {'symbolic_arm_mapping': {'B_star_1': 'A02-Bstar',
                   'B_star_2': 'A02-hard'}, 'recipes': recipes}
        self.freeze_sha = write(self.freeze, freeze)
        self.engineering = self.root / 'engineering.json'
        engineering = timing.expected_engineering_protocol(
            timing.sha(self.protocol), timing.sha(self.checkpoint),
            timing.sha(self.prior), self.freeze_sha)
        self.engineering_sha = write(self.engineering, engineering)

    def args(self, **changes):
        values = dict(protocol=self.protocol, checkpoint=self.checkpoint, prior=self.prior,
            representative_freeze=self.freeze,
            representative_freeze_sha256=self.freeze_sha,
            engineering_protocol=self.engineering,
            engineering_protocol_sha256=self.engineering_sha,
            out=self.root / 'out', deadline_unix=timing.time.time() + 300,
            max_output_bytes=512 * 1024**2, device='cuda:0', allow_cpu=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def test_fake_success_has_exact_identities_isolation_and_timing_order(self):
        hooks = FakeHooks()
        self.assertEqual(timing.execute(self.args(), hooks=hooks), 0)
        receipt = json.loads((self.root / 'out/complete.json').read_text())
        self.assertEqual(receipt['calls'], {'F': 6, 'T': 0, 'E': 0})
        self.assertEqual(len(receipt['records']), 6)
        identities = {(row['identity']['symbol'], row['identity']['audit'])
                      for row in receipt['records']}
        self.assertEqual(identities,
                         {(symbol, audit) for symbol in timing.SYMBOLS
                          for audit in timing.MODES})
        observer = json.loads((self.root / 'out/observer-F-001.json').read_text())
        self.assertEqual(observer['dals_event_count'], 9)
        self.assertEqual(observer['dals_summaries'][0]['H']['shape'], [4, 4])
        self.assertIsNone(observer['dals_summaries'][0]['H']['value'])
        self.assertEqual(hooks.reservations, [{'F': 6, 'T': 0, 'E': 0}])
        builds = [event for event in hooks.events if event[0] == 'build']
        self.assertEqual(len(builds), 6)
        self.assertEqual(len({event[2] for event in builds}), 6)
        for index, event in enumerate(hooks.events):
            if event[0] == 'run':
                self.assertEqual(hooks.events[index - 1][0], 'sync')
                self.assertEqual(hooks.events[index + 1][0], 'sync')

    def test_duplicate_output_and_small_storage_cap_reject(self):
        hooks = FakeHooks()
        out = self.root / 'existing'
        out.mkdir()
        with self.assertRaises(FileExistsError):
            timing.execute(self.args(out=out), hooks=hooks)
        with self.assertRaisesRegex(ValueError, 'storage'):
            timing.execute(self.args(out=self.root / 'small', max_output_bytes=1), hooks=hooks)

    def test_wrong_freeze_mapping_rejects_before_reservation(self):
        value = json.loads(self.freeze.read_text())
        value['symbolic_arm_mapping']['B_star_2'] = 'A02-group'
        bad_sha = write(self.freeze, value)
        hooks = FakeHooks()
        with self.assertRaisesRegex(ValueError, 'representative'):
            timing.execute(self.args(representative_freeze_sha256=bad_sha), hooks=hooks)
        self.assertEqual(hooks.reservations, [])

    def test_observer_on_off_difference_fails_and_retains_attempt(self):
        hooks = FakeHooks(perturb=True)
        with self.assertRaisesRegex(ValueError, 'equivalence'):
            timing.execute(self.args(), hooks=hooks)
        failure = json.loads((self.root / 'out/failure.json').read_text())
        self.assertEqual(failure['calls'], {'F': 6, 'T': 0, 'E': 0})
        self.assertEqual(len(failure['records']), 6)

    def test_no_cuda_never_falls_back_and_cpu_requires_explicit_flag(self):
        hooks = FakeHooks(cuda=False)
        with self.assertRaisesRegex(ValueError, 'CUDA'):
            timing.execute(self.args(), hooks=hooks)
        cpu = FakeHooks(cuda=False)
        self.assertEqual(timing.execute(self.args(out=self.root / 'cpu', device='cpu',
                                                  allow_cpu=True), hooks=cpu), 0)
        with self.assertRaisesRegex(ValueError, 'explicit'):
            timing.validate_request(self.args(out=self.root / 'badcpu', device='cpu',
                                                allow_cpu=False), hooks=cpu)

    def test_shared_ledger_enforces_remaining_six_F_without_reclaim(self):
        def contract(full_calls):
            return {'campaign_id': timing.CAMPAIGN_ID,
                    'max_full_calls': full_calls,
                    'calls_reserved': {'F': full_calls, 'T': 0, 'E': 0},
                    'config_sha256': str(full_calls) * 64}

        timing.reserve_profile(self.root / 'prior', contract(122))
        timing.reserve_profile(self.root / 'six', contract(6))
        with self.assertRaisesRegex(ValueError, 'cumulative'):
            timing.reserve_profile(self.root / 'seventh', contract(1))

    def test_source_mutation_during_prepare_rejects_before_reservation(self):
        hooks = FakeHooks(mutate_source=True)
        with self.assertRaisesRegex(ValueError, 'source package changed'):
            timing.execute(self.args(), hooks=hooks)
        self.assertEqual(hooks.reservations, [])

    def test_true_relative_gate_rejects_small_scale_and_accepts_two_zeros(self):
        base = {key: np.zeros(1) for key in timing.CONTINUOUS + timing.EXACT}
        base.update(H=np.zeros((1, 1)), sigma2=np.array(0.),
                    sigma2_terminal=np.array(0.))
        same = {key: value.copy() for key, value in base.items()}
        self.assertEqual(timing.compare_pair(base, same, 'zero')['fields']
                         ['sigma2']['relative_l2'], 0.)
        on = {key: value.copy() for key, value in base.items()}
        off = {key: value.copy() for key, value in base.items()}
        on['sigma2'], off['sigma2'] = np.array(1.01e-4), np.array(1e-4)
        with self.assertRaisesRegex(ValueError, 'tolerance'):
            timing.compare_pair(on, off, 'tiny')
        huge_on = {key: value.copy() for key, value in base.items()}
        huge_off = {key: value.copy() for key, value in base.items()}
        huge_on['x_soft'] = np.array([1e308, -1e308])
        huge_off['x_soft'] = np.array([-1e308, 1e308])
        with np.errstate(over='ignore', invalid='ignore'):
            with self.assertRaisesRegex(ValueError, 'tolerance'):
                timing.compare_pair(huge_on, huge_off, 'overflow')

    def test_expired_prepare_and_wrong_frame_never_run_or_reserve(self):
        for hooks, message in ((FakeHooks(expire_prepare=True), 'deadline'),
                               (FakeHooks(wrong_frame=True), 'identity')):
            with self.subTest(message=message):
                with self.assertRaisesRegex((TimeoutError, ValueError), message):
                    timing.execute(self.args(out=self.root / message), hooks=hooks)
                self.assertEqual(hooks.reservations, [])
                self.assertFalse(any(event[0] == 'run' for event in hooks.events))

        build = FakeHooks(expire_build=True)
        with self.assertRaisesRegex(TimeoutError, 'deadline'):
            timing.execute(self.args(out=self.root / 'build-deadline'), hooks=build)
        self.assertEqual(build.reservations, [{'F': 6, 'T': 0, 'E': 0}])
        self.assertFalse(any(event[0] == 'run' for event in build.events))

    def test_nonbinary_receiver_result_is_rejected(self):
        hooks = FakeHooks(nonbinary=True)
        with self.assertRaisesRegex(ValueError, 'binary'):
            timing.execute(self.args(), hooks=hooks)
        failure = json.loads((self.root / 'out/failure.json').read_text())
        self.assertEqual(failure['calls']['F'], 1)

        transposed = FakeHooks(transpose_code=True)
        with self.assertRaisesRegex(ValueError, 'LDPC dimensions'):
            timing.execute(self.args(out=self.root / 'transpose'),
                           hooks=transposed)
        self.assertEqual(json.loads((self.root / 'transpose/failure.json')
                                    .read_text())['calls']['F'], 1)

    def test_real_hooks_factory_and_cuda_fraction_boundary(self):
        hooks = timing.RealHooks()
        args = type('Args', (), {'checkpoint': self.checkpoint,
                    'prior': self.prior, 'device': 'cuda:0'})()
        models = [type('Model', (), {'cfg': object(),
                   'use_soft_decisions': False})() for _ in range(3)]
        context = {'args': args, 'system': object(), 'code': object()}
        with mock.patch.object(timing, 'build_receiver', side_effect=models) as factory, \
                mock.patch.object(timing, 'load_prior', return_value=('lookup', {})) as prior, \
                mock.patch.object(timing, 'A2Receiver', side_effect=lambda model, code: ('A2', model)), \
                mock.patch.object(timing, 'BaselineReceiver',
                    side_effect=lambda model, code, recipe, system: (model, recipe)):
            a2 = hooks.build('A2', context)
            b1 = hooks.build('B_star_1', context)
            b2 = hooks.build('B_star_2', context)
        self.assertEqual(factory.call_count, 3)
        self.assertIs(a2[1].model, models[0])
        self.assertEqual((b1[1], b2[1]), ('B0-p2-s0.5',
                                          'bounded-param-p3-s1'))
        self.assertEqual(prior.call_args.args[:3], (self.prior, 8, 1024))
        self.assertEqual(prior.call_args.kwargs,
                         {'l_max': 102, 'k_max': 2, 'nomination_cap': 40,
                          'receiver_shell': 'direct40'})
        with mock.patch.object(timing.torch, 'set_num_threads') as threads, \
                mock.patch.object(timing.torch.cuda,
                                  'set_per_process_memory_fraction') as fraction:
            hooks.configure('cuda:0')
        threads.assert_called_once_with(1)
        self.assertEqual(fraction.call_args.args[0], .25)

    def test_npz_peak_budget_is_prechecked_without_double_counting_temp(self):
        root = self.root / 'raw-budget'
        root.mkdir()
        values = {'x': np.zeros(32, dtype=np.float64)}
        limit = sum(value.nbytes for value in values.values()) + \
            timing.NPZ_OVERHEAD_BYTES
        descriptor = timing._bounded_npz(root / 'raw.npz', values, root, limit)
        self.assertEqual(descriptor['sha256'], timing.sha(root / 'raw.npz'))
        self.assertFalse(any(path.name.startswith('.timing-')
                             for path in root.iterdir()))
        with self.assertRaisesRegex(OSError, 'budget'):
            timing._bounded_npz(root / 'second.npz', values, root, 1)


if __name__ == '__main__':
    unittest.main()
