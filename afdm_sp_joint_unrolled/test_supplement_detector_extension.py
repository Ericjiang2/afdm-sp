"""Synthetic admission/accounting fixtures, not campaign or GPU evidence."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from . import supplement_detector_extension as ext
from . import supplement_detector_run as run
from .supplement_detectors import catalogue, terminal
from .e1_ldpc import build_code


class AllocationFixture:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = {'fixture.py': 'a' * 64}
        self.allocation = {
            'schema': ext.ALLOCATION_SCHEMA,
            'status': 'allocated_not_runtime_admission',
            'campaign_id': ext.CAMPAIGN_ID, 'issue': 'DET-01',
            'candidates': list(ext.ADDITIONAL_IDS),
            'qualification_T': 16, 'development_T': 384, 'total_T_cap': 400,
            'hard_wall_seconds': 3600, 'output_cap_bytes': 1024**3,
            'new_F': 0, 'new_E': 0, 'training': False,
            'confirmation_access': False, 'source_manifest': self.source,
            'admitted_unix': time.time(), 'deadline_unix': time.time() + 300,
            'run_root': str(self.root / 'run'),
        }
        approval = {
            'status': 'USER_APPROVED_SCOPE_AMENDMENT_IMPLEMENTATION_NOT_RUNTIME_ADMISSION',
            'candidates': list(ext.ADDITIONAL_IDS), 'qualification_calls_T': 16,
            'development_calls_T': 384, 'total_T_cap': 400, 'new_F': 0, 'new_E': 0,
            'training': False, 'confirmation_access': False,
            'evidence_kind': 'synthetic fixture; not user authorization'}
        transfer = {
            'status': 'APPROVED_ALLOCATION_DESIGN_NOT_RUNTIME_ADMISSION',
            'original_T': 512, 'replacement_T': 512, 'incremental_total_T': 0,
            'replacement_units': [
                {'stage':'DET-01-additional-qualification','T':16},
                {'stage':'DET-01-additional-development','T':384},
                {'stage':'DET-01-stability-probes-retained','T':112}]}
        approval_ref = self.write('approval.json', approval)
        transfer['approval_sha256'] = approval_ref['sha256']
        self.allocation['references'] = {
            'approval': approval_ref,
            'budget_transfer': self.write('transfer.json', transfer),
            'proposal': self.write('proposal.md', '# Approved proposal\n'),
            'residual_contract': self.write('residual.md', '# Frozen residual\n'),
            'original_qualification_admission': self.write('original-q.json', {}),
            'original_development_admission': self.write('original-d.json', {}),
        }

    def write(self, name, value):
        path = self.root / name
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def bound(self):
        ref = self.write('allocation.json', self.allocation)
        return ext.validate_allocation(ref['path'], ref['sha256'], self.source)


class ExtensionTests(AllocationFixture, unittest.TestCase):
    def test_markdown_references_are_hash_bound_not_json(self):
        allocation = self.bound()
        self.assertEqual(len(allocation['_bound_files']), 7)
        ext.unchanged(allocation, self.source)
        (self.root / 'proposal.md').write_text('# Changed\n')
        with self.assertRaises(ValueError):
            ext.unchanged(allocation, self.source)

    def test_scope_source_and_common_deadline_changes_rejected(self):
        for key, value in (
                ('total_T_cap', 401), ('candidates', ['BP80']),
                ('training', True), ('confirmation_access', True),
                ('source_manifest', {}), ('deadline_unix', float('inf')),
                ('admitted_unix', 'not-a-time')):
            with self.subTest(key=key):
                original = self.allocation[key]
                self.allocation[key] = value
                with self.assertRaises(ValueError):
                    self.bound()
                self.allocation[key] = original

    def test_exact_identity_domains(self):
        self.assertEqual(len(ext.identities(ext.STAGES[0], range(4))), 16)
        all_development = [row for start in range(0, 192, 16)
                           for row in ext.identities(ext.STAGES[1], range(start, start + 16))]
        self.assertEqual(len({tuple(row) for row in all_development}), 384)
        for stage, blocks in (
                ('unknown', [0]), (ext.STAGES[0], [0]),
                (ext.STAGES[0], range(1, 5)), (ext.STAGES[1], []),
                (ext.STAGES[1], [-1]), (ext.STAGES[1], [192]),
                (ext.STAGES[1], [True]), (ext.STAGES[1], [0, 0]),
                (ext.STAGES[1], [0, 2]), (ext.STAGES[1], range(17))):
            with self.subTest(stage=stage, blocks=blocks):
                with self.assertRaises(ValueError):
                    ext.identities(stage, blocks)

    def test_all_400_calls_reserved_once_and_forgery_rejected(self):
        allocation = self.bound()
        ledger = Path(allocation['run_root']) / 'supplement-detector-additional-ledger'
        root = Path(allocation['run_root'])
        def reserve(stage, blocks, out):
            return ext.reserve(ledger, root / out, allocation, stage, blocks, 'b' * 64)
        reserve(ext.STAGES[0], range(4), 'q')
        for start in range(0, 192, 16):
            reserve(ext.STAGES[1], range(start, start + 16), f'd{start}')
        self.assertEqual(sum(json.loads(p.read_text())['T']
                             for p in ledger.glob('reservation-*.json')), 400)
        with self.assertRaisesRegex(ValueError, 'already charged'):
            reserve(ext.STAGES[1], [0], 'retry')
        row = json.loads(next(ledger.glob('reservation-*.json')).read_text())
        row['identities'][0][1] = 999
        self.write('forged.json', row)
        (ledger / 'reservation-forged.json').write_text(json.dumps(row))
        with self.assertRaises(ValueError):
            reserve(ext.STAGES[1], [0], 'forged')

    def test_process_lock_held_across_batches(self):
        allocation = self.bound()
        with ext.execution_lock(allocation):
            with self.assertRaises(BlockingIOError):
                with ext.execution_lock(allocation):
                    self.fail('concurrent extension acquired execution lock')
        with ext.execution_lock(allocation):
            pass

    def test_run_wide_storage_counts_other_batches(self):
        allocation = self.bound()
        run_root = Path(allocation['run_root'])
        run_root.mkdir()
        (run_root / 'previous-batch').mkdir()
        (run_root / 'previous-batch' / 'raw').write_bytes(b'x' * 4096)
        self.assertEqual(ext.output_bytes(run_root), 4096)

    def test_stage_admission_must_share_deadline_and_root(self):
        allocation = self.bound()
        run_root = Path(allocation['run_root'])
        caches = [{'block': b} for b in range(4)]
        admission = {
            'schema': ext.ADMISSION_SCHEMA, 'status': 'admitted',
            'campaign_id': ext.CAMPAIGN_ID, 'stage': ext.STAGES[0],
            'allocation_path': allocation['_path'],
            'allocation_sha256': allocation['_sha256'],
            'caches': caches, 'detectors': list(ext.ADDITIONAL_IDS),
            'calls': {'F': 0, 'T': 16, 'E': 0},
            'deadline_unix': allocation['deadline_unix'],
            'max_output_bytes': ext.OUTPUT_CAP,
            'ledger_path': str(run_root / 'supplement-detector-additional-ledger'),
        }
        ref = self.write('admission.json', admission)
        args = SimpleNamespace(stage=ext.STAGES[0], admission=ref['path'],
                               deadline_unix=allocation['deadline_unix'],
                               max_output_bytes=ext.OUTPUT_CAP,
                               max_terminal_calls=16, out=run_root / 'q')
        ext.validate_stage_admission(args, allocation, caches)
        args.deadline_unix += 1
        with self.assertRaises((ValueError, TimeoutError)):
            ext.validate_stage_admission(args, allocation, caches)
        args.deadline_unix = allocation['deadline_unix']
        args.out = self.root / 'outside'
        with self.assertRaises(ValueError):
            ext.validate_stage_admission(args, allocation, caches)


class PipelineFixtureTests(AllocationFixture, unittest.TestCase):
    """Real short-code CPU terminals inside explicitly mocked CUDA/cache adapters."""

    def setUp(self):
        super().setUp()
        self.old_ids = [row['id'] for row in catalogue()]
        self.caches = [{'block': b, 'local_root': str(self.root)} for b in range(192)]
        old_qualification = self.write('old-qualification.json', {
            'stage': 'qualification', 'calls_attempted': 64, 'failures': [],
            'qualified_by_detector': {identifier: False for identifier in self.old_ids}})
        quote_contract = {
            'stage': 'quote', 'campaign_id': ext.CAMPAIGN_ID,
            'detectors': run.QUOTE_IDS, 'calls_reserved': {'F': 0, 'T': 2, 'E': 0}}
        quote_contract['config_sha256'] = run.config_hash(quote_contract)
        contract_ref = self.write('contract.json', quote_contract)
        summary_ref = self.write('summary.json', {'fixture': True})
        quote = self.write('quote.json', {
            'stage': 'quote', 'status': 'complete', 'exitcode': 0,
            'calls_attempted': 2, 'failures': [],
            'records': [{'identity': {'detector': identifier}} for identifier in run.QUOTE_IDS],
            'config_sha256': quote_contract['config_sha256']})
        selection = self.write('selection.json', {
            'selection': {'status': 'development_references_selected', 'references': ['baseline']},
            'batches': [{'config_sha256': 'fixture-config', 'summary_sha256': summary_ref['sha256'],
                         'contract_file_sha256': contract_ref['sha256']}]})
        self.allocation['references']['original_qualification_admission'] = self.write('original-q.json', {
            'stage': 'qualification', 'campaign_id': ext.CAMPAIGN_ID,
            'caches': self.caches[:4], 'detectors': self.old_ids, 'completed_quote': quote})
        self.allocation['references']['original_development_admission'] = self.write('original-d.json', {
            'stage': 'development', 'campaign_id': ext.CAMPAIGN_ID,
            'caches': self.caches, 'detectors': self.old_ids, 'baseline': 'baseline',
            'selection': selection, 'qualification': old_qualification})
        self.bound_allocation = self.bound()
        (self.root / 'code').mkdir()
        self.code = build_code(n=24, d_v=3, d_c=6, cache_dir=self.root / 'code')
        self.sequence = []

    def stage_args(self, stage, start=0, stop=4, qualification=None):
        allocation = self.bound_allocation
        run_root = Path(allocation['run_root'])
        caches = self.caches[start:stop]
        calls = 16 if stage == ext.STAGES[0] else len(caches) * 2
        admission = {
            'schema': ext.ADMISSION_SCHEMA, 'status': 'admitted',
            'campaign_id': ext.CAMPAIGN_ID, 'stage': stage,
            'allocation_path': allocation['_path'], 'allocation_sha256': allocation['_sha256'],
            'caches': caches, 'detectors': list(ext.ADDITIONAL_IDS),
            'calls': {'F': 0, 'T': calls, 'E': 0}, 'deadline_unix': allocation['deadline_unix'],
            'max_output_bytes': ext.OUTPUT_CAP,
            'ledger_path': str(run_root / 'supplement-detector-additional-ledger')}
        if qualification:
            admission['qualification'] = qualification
            admission['resource_projection'] = json.loads(Path(qualification['path']).read_text())['resource_projection']
        ref = self.write(f'{stage}-{start}.json', admission)
        return SimpleNamespace(stage=stage, device='cuda', admission=Path(ref['path']),
            deadline_unix=allocation['deadline_unix'], max_terminal_calls=calls,
            max_output_bytes=ext.OUTPUT_CAP, out=run_root / f'{stage}-{start}',
            allocation=Path(allocation['_path']), allocation_sha256=allocation['_sha256'],
            caches=json.dumps(caches), detectors=json.dumps(list(ext.ADDITIONAL_IDS)))

    def loader(self, spec, *, split='engineering', baseline=None):
        H = (1 + .1j) * np.eye(12) + .01 * np.roll(np.eye(12), 1, axis=1)
        data = dict(y_cancelled=H @ np.full(12, .5+.5j), H=H,
                    sigma2_terminal=np.array(.2), constellation=run.CONST)
        truth = dict(info=np.zeros(self.code['k'], dtype=np.uint8), coded=np.zeros(24, dtype=np.uint8))
        path = self.root / 'truth.npz'
        if not path.exists():
            np.savez_compressed(path, **truth)
        proof = dict(config_sha256='fixture-config', block=spec['block'],
            baseline=baseline or 'B0-p3-s1', split=split, spec=spec,
            terminal_path=str(path), truth_hashes={k:run.array_hash(v) for k,v in truth.items()},
            files={str(path): run.sha(path), str(self.root/'summary.json'): run.sha(self.root/'summary.json'),
                   str(self.root/'contract.json'): run.sha(self.root/'contract.json')},
            code_sha256={k:run.array_hash(self.code[k]) for k in ('G','H')})
        return data, proof

    def execute_fixture(self, args, *, fail_terminal=False, unstable=False):
        original_score = run.offline_score
        def cpu_terminal(*arguments, **kwargs):
            self.sequence.append('detect')
            self.assertEqual(len(arguments), 6)
            if fail_terminal:
                raise RuntimeError('injected terminal failure')
            kwargs['device'] = 'cpu'
            result = terminal(*arguments, **kwargs)
            if unstable:
                state = result['bp_message_state']
                state['mu_previous'] = state['mu_current'] + 1
                diagnostics = result['diagnostics']
                residual = float(np.linalg.norm(state['mu_current']-state['mu_previous']) /
                                 max(1., np.linalg.norm(state['mu_previous'])))
                diagnostics['mu_message_relative_residual'] = residual
                diagnostics['fixed_point_residual'] = max(residual, diagnostics['var_message_relative_residual'])
                diagnostics['converged'] = False
                diagnostics['bp_message_hashes'] = {k:run.array_hash(v) for k,v in state.items()}
                diagnostics['bp_message_norms'] = {k:float(np.linalg.norm(v)) for k,v in state.items()}
            return result
        def score(result, proof):
            self.assertEqual(self.sequence[-1], 'detect')
            self.sequence.append('score')
            return original_score(result, proof)
        with ExitStack() as stack:
            for name, value in [('is_available',True),('current_device',0),('max_memory_allocated',0)]:
                stack.enter_context(patch.object(run.torch.cuda,name,return_value=value))
            for name in ('synchronize','reset_peak_memory_stats','set_per_process_memory_fraction'):
                stack.enter_context(patch.object(run.torch.cuda,name))
            stack.enter_context(patch.object(run.torch,'set_num_threads'))
            stack.enter_context(patch.object(run.torch,'get_num_interop_threads',return_value=1))
            stack.enter_context(patch.object(run,'sources',return_value=self.source))
            stack.enter_context(patch.object(run,'load_cache',side_effect=self.loader))
            stack.enter_context(patch.object(run,'build_code',return_value=self.code))
            stack.enter_context(patch.object(run,'unchanged'))
            stack.enter_context(patch.object(run,'terminal',side_effect=cpu_terminal))
            stack.enter_context(patch.object(run,'offline_score',side_effect=score))
            return run.execute(args)

    def qualification_fixture(self):
        args = self.stage_args(ext.STAGES[0])
        self.assertIn(self.execute_fixture(args), (0, 1))
        path = args.out / 'summary.json'
        return args, {'path':str(path), 'sha256':run.sha(path)}

    def verify(self, ref):
        with patch.object(run, 'load_cache', side_effect=self.loader):
            return ext.verify_qualification(ref, self.bound_allocation)

    def test_real_short_code_messages_survive_runner_and_recompute(self):
        args, ref = self.qualification_fixture()
        qualified, records = self.verify(ref)
        self.assertEqual(set(qualified), set(ext.ADDITIONAL_IDS))
        self.assertEqual(len(records), 16)
        self.assertEqual(self.sequence, ['detect'] * 16)
        with np.load(records[0]['terminal']['path'], allow_pickle=False) as raw:
            self.assertGreater(raw['bp_message_mu_current'].size, 0)
            self.assertEqual(run.array_hash(raw['bp_message_mu_current']),
                             records[0]['diagnostics']['bp_message_hashes']['mu_current'])
        summary = json.loads(Path(ref['path']).read_text())
        summary['qualified_by_detector']['BP80'] = not qualified['BP80']
        Path(ref['path']).write_text(json.dumps(summary))
        ref['sha256'] = run.sha(ref['path'])
        with self.assertRaisesRegex(ValueError, 'flags differ'):
            self.verify(ref)

    def test_development_scores_only_after_terminal_and_never_uses_old_budget(self):
        _, ref = self.qualification_fixture()
        self.sequence.clear()
        args = self.stage_args(ext.STAGES[1], start=16, stop=18, qualification=ref)
        with patch.object(run, 'reserve_profile', side_effect=AssertionError('old budget')):
            self.assertEqual(self.execute_fixture(args), 0)
        self.assertEqual(self.sequence, ['detect','score'] * 4)
        summary = json.loads((args.out / 'summary.json').read_text())
        self.assertEqual(summary['calls_attempted'], 4)
        identities = [row['identity'] for row in summary['records']]
        self.assertEqual(sorted({row['block'] for row in identities}), [16, 17])
        self.assertEqual(sorted({row['cache'] for row in identities}), [16, 17])
        self.assertEqual(sorted({row['batch_index'] for row in identities}), [0, 1])
        self.assertTrue(all(row['cache'] == row['block'] for row in identities))
        self.assertTrue(all(row['error_counts']['FER'] == 0 for row in summary['records']))
        with self.assertRaisesRegex(ValueError, 'already charged'):
            retry = self.stage_args(ext.STAGES[1], start=16, stop=18, qualification=ref)
            retry.out = args.out.parent / 'retry'
            self.execute_fixture(retry)

    def test_qualification_failures_are_retained_and_block_development(self):
        args = self.stage_args(ext.STAGES[0])
        self.assertEqual(self.execute_fixture(args, fail_terminal=True), 1)
        summary = json.loads((args.out / 'summary.json').read_text())
        self.assertEqual(len(summary['failures']), 16)
        self.assertEqual(summary['status'], 'completed_with_failures')
        self.assertFalse(any(summary['qualified_by_detector'].values()))
        ref = {'path':str(args.out/'summary.json'), 'sha256':run.sha(args.out/'summary.json')}
        with self.assertRaises(ValueError):
            self.verify(ref)

    def test_unqualified_numerical_records_still_allow_registered_development(self):
        args = self.stage_args(ext.STAGES[0])
        self.assertEqual(self.execute_fixture(args, unstable=True), 1)
        ref = {'path':str(args.out/'summary.json'), 'sha256':run.sha(args.out/'summary.json')}
        qualified, records = self.verify(ref)
        self.assertEqual(qualified, {'BP80':False, 'BP160':False})
        development = self.stage_args(ext.STAGES[1], start=0, stop=1, qualification=ref)
        self.assertEqual(self.execute_fixture(development), 0)
        summary = json.loads((development.out/'summary.json').read_text())
        self.assertTrue(all(row['engineering_qualified'] is False for row in summary['records']))
        Path(records[0]['terminal']['path']).write_bytes(b'corrupted raw')
        with self.assertRaisesRegex(ValueError, 'raw content differs'):
            self.verify(ref)

    def test_self_consistent_wrong_source_is_rejected(self):
        args, ref = self.qualification_fixture()
        contract_path = args.out/'contract.json'
        contract = json.loads(contract_path.read_text())
        contract['source_sha256'] = {'other.py': 'b' * 64}
        contract['config_sha256'] = run.config_hash(contract)
        contract_path.write_text(json.dumps(contract))
        summary = json.loads(Path(ref['path']).read_text())
        summary['config_sha256'] = contract['config_sha256']
        for record in summary['records']:
            record['identity']['config_sha256'] = contract['config_sha256']
            call = args.out / f"call-{record['identity']['attempt']:03d}.json"
            saved = json.loads(call.read_text())
            saved['identity']['config_sha256'] = contract['config_sha256']
            call.write_text(json.dumps(saved))
        Path(ref['path']).write_text(json.dumps(summary))
        ref['sha256'] = run.sha(ref['path'])
        with self.assertRaises(ValueError):
            self.verify(ref)

    def test_rehashed_wrong_qualification_cache_is_not_admissible(self):
        args, ref = self.qualification_fixture()
        contract_path = args.out/'contract.json'
        contract = json.loads(contract_path.read_text())
        contract['caches'][0]['block'] = 31
        contract['config_sha256'] = run.config_hash(contract)
        contract_path.write_text(json.dumps(contract))
        summary = json.loads(Path(ref['path']).read_text())
        summary['config_sha256'] = contract['config_sha256']
        Path(ref['path']).write_text(json.dumps(summary))
        ref['sha256'] = run.sha(ref['path'])
        with self.assertRaisesRegex(ValueError, 'contract caches differ'):
            self.verify(ref)

    def test_removed_reservation_blocks_qualification_and_recharge(self):
        args, ref = self.qualification_fixture()
        contract = json.loads((args.out/'contract.json').read_text())
        Path(contract['ledger']['path']).unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.verify(ref)
        ledger = Path(self.bound_allocation['run_root'])/'supplement-detector-additional-ledger'
        with self.assertRaisesRegex(ValueError, 'lost or changed'):
            ext.reserve(ledger,args.out.parent/'retry',self.bound_allocation,
                        ext.STAGES[0],range(4),'b'*64)

    def test_bad_scope_rejected_before_any_terminal(self):
        for change in ({'detectors': '["BP80"]'}, {'allocation': None},
                       {'max_terminal_calls': 15}, {'caches': '[{}]'}):
            args = self.stage_args(ext.STAGES[0])
            for key, value in change.items():
                setattr(args, key, value)
            with self.assertRaises((ValueError, TypeError)):
                self.execute_fixture(args)
        self.assertEqual(self.sequence, [])

    def test_det01r_replays_closed_16t_from_a_new_allocation(self):
        args, ref = self.qualification_fixture()
        predecessor = {
            'schema': ext.ALLOCATION_SCHEMA,
            'status': 'allocated_not_runtime_admission',
        }
        pred = self.write('predecessor-allocation.json', predecessor)
        dual = self.write('dual.json', {
            'historical_frozen_verifier_status': 'FAIL',
            'corrected_revalidation_status': 'PASS',
            'rerun_performed': False,
            'qualification_bytes_modified': False,
            'do_not_rewrite_v2_verifier_as_pass': True,
        })
        split = self.write('split.json', {
            'only_changed_file': 'supplement_detectors.py',
            'only_changed_functions': ['qualification_pair'],
            'identical_execution_functions': True,
        })
        selection = self.write('selection-freeze.json', {
            'status': 'frozen_before_384T_and_before_any_BP_development_result',
            'h01_may_start_only_after_d1_freeze': True,
            'candidate_set': ['BP80', 'BP160'],
        })
        amendment = self.write('amendment.md', '# DET-01R\n')
        run_root = self.root / 'det01r-run'
        r1 = {
            'schema': ext.DET01R_ALLOCATION_SCHEMA,
            'status': 'allocated_not_runtime_admission',
            'protocol': ext.DET01R_PROTOCOL,
            'campaign_id': ext.CAMPAIGN_ID,
            'issue': 'DET-01R',
            'candidates': list(ext.ADDITIONAL_IDS),
            'qualification_T': 0, 'development_T': 384, 'total_T_cap': 384,
            'prior_qualification_T_charged': 16,
            'hard_wall_seconds': 3600, 'output_cap_bytes': ext.OUTPUT_CAP,
            'new_F': 0, 'new_E': 0, 'training': False, 'confirmation_access': False,
            'rerun_16T': False, 'rewrite_16T_bytes': False,
            'source_manifest': self.source,
            'admitted_unix': time.time(), 'deadline_unix': time.time() + 300,
            'run_root': str(run_root),
            'references': {
                'protocol_amendment': amendment,
                'execution_split': split,
                'dual_status': dual,
                'selection_freeze': selection,
                'historical_qualification': ref,
                'historical_contract': {
                    'path': str(args.out / 'contract.json'),
                    'sha256': run.sha(args.out / 'contract.json'),
                },
                'predecessor_allocation': pred,
                'original_qualification_admission': self.allocation['references']['original_qualification_admission'],
                'original_development_admission': self.allocation['references']['original_development_admission'],
            },
        }
        alloc_ref = self.write('det01r-allocation.json', r1)
        # The fixture 16T contract is bound to the old allocation, not pred.
        contract = json.loads((args.out / 'contract.json').read_text())
        contract['allocation_sha256'] = pred['sha256']
        contract['config_sha256'] = run.config_hash(contract)
        (args.out / 'contract.json').write_text(json.dumps(contract))
        summary = json.loads(Path(ref['path']).read_text())
        summary['config_sha256'] = contract['config_sha256']
        Path(ref['path']).write_text(json.dumps(summary))
        for record in summary['records']:
            record['identity']['config_sha256'] = contract['config_sha256']
            call = args.out / f"call-{record['identity']['attempt']:03d}.json"
            saved = json.loads(call.read_text())
            saved['identity']['config_sha256'] = contract['config_sha256']
            call.write_text(json.dumps(saved))
        Path(ref['path']).write_text(json.dumps(summary))
        ref['sha256'] = run.sha(ref['path'])
        r1['references']['historical_qualification'] = ref
        r1['references']['historical_contract'] = {
            'path': str(args.out / 'contract.json'),
            'sha256': run.sha(args.out / 'contract.json'),
        }
        alloc_ref = self.write('det01r-allocation.json', r1)
        reservation_path = Path(contract['ledger']['path'])
        reservation = json.loads(reservation_path.read_text())
        reservation['allocation_sha256'] = pred['sha256']
        reservation_path.write_text(json.dumps(reservation))
        contract['ledger']['sha256'] = run.sha(reservation_path)
        contract['config_sha256'] = run.config_hash(contract)
        (args.out / 'contract.json').write_text(json.dumps(contract))
        summary['config_sha256'] = contract['config_sha256']
        Path(ref['path']).write_text(json.dumps(summary))
        ref['sha256'] = run.sha(ref['path'])
        r1['references']['historical_qualification'] = ref
        r1['references']['historical_contract'] = {
            'path': str(args.out / 'contract.json'),
            'sha256': run.sha(args.out / 'contract.json'),
        }
        alloc_ref = self.write('det01r-allocation-final.json', r1)
        bound = ext.validate_det01r_allocation(alloc_ref['path'], alloc_ref['sha256'], self.source)
        with patch.object(run, 'load_cache', side_effect=self.loader):
            qualified, records = ext.verify_historical_qualification(ref, bound)
        self.assertEqual(qualified, {'BP80': True, 'BP160': True})
        self.assertEqual(len(records), 16)
        with self.assertRaises(ValueError):
            ext.verify_qualification(ref, bound)

    def test_common_storage_cap_rejects_before_detection(self):
        args = self.stage_args(ext.STAGES[0])
        with patch.object(ext, 'output_bytes', return_value=ext.OUTPUT_CAP-65536):
            with self.assertRaises(OSError):
                self.execute_fixture(args)
        self.assertEqual(self.sequence, [])


if __name__ == '__main__':
    unittest.main()
