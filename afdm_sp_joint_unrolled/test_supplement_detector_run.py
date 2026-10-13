"""Synthetic contract fixtures; no N1024 GPU timing claims."""
import json
from contextlib import ExitStack
import tempfile
import time
import signal
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from . import supplement_detector_run as run


class DetectorRunTests(unittest.TestCase):
    def args(self,**overrides):
        values=dict(stage='quote',device='cuda',admission=None,deadline_unix=time.time()+60,
            max_terminal_calls=2,max_output_bytes=32*1024*1024)
        values.update(overrides);return SimpleNamespace(**values)

    def test_cuda_current_index_reaches_allocator_terminal_and_contract(self):
        np=run.np;expected=run.torch.device('cuda',2)
        def cap(fraction,device):
            self.assertEqual(fraction,.25)
            self.assertEqual(device,expected)
            self.assertIsNotNone(device.index)
        def terminal(*args,device,**kwargs):
            self.assertEqual(device,expected)
            return dict({k:np.zeros(2) for k in ('mu','var','raw_llr','llr','x_hard','decoded','info_hat')},
                diagnostics={},terminal_CPU_seconds=0.,decode_ok=False)
        code={'G':np.eye(2),'H':np.eye(2)}
        data=dict(y_cancelled=np.zeros(2,dtype=complex),H=np.eye(2,dtype=complex),
            sigma2_terminal=np.array(1.),constellation=run.CONST)
        proof=dict(config_sha256='fixture',block=0,baseline='B0-p3-s1',
            code_sha256={k:run.array_hash(v) for k,v in code.items()})
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            args=self.args(out=Path(directory)/'out',caches='[{}]',detectors=json.dumps(run.QUOTE_IDS))
            for name,value in [('is_available',True),('current_device',2),('max_memory_allocated',0)]:
                stack.enter_context(patch.object(run.torch.cuda,name,return_value=value))
            allocator=stack.enter_context(patch.object(run.torch.cuda,'set_per_process_memory_fraction',side_effect=cap))
            for name in ('synchronize','reset_peak_memory_stats'):
                stack.enter_context(patch.object(run.torch.cuda,name))
            stack.enter_context(patch.object(run.torch,'set_num_threads'))
            stack.enter_context(patch.object(run.torch,'get_num_interop_threads',return_value=1))
            stack.enter_context(patch.object(run,'load_cache',return_value=(data,proof)))
            stack.enter_context(patch.object(run,'build_code',return_value=code))
            stack.enter_context(patch.object(run,'reserve_profile',return_value={'fixture':True}))
            stack.enter_context(patch.object(run,'unchanged'))
            calls=stack.enter_context(patch.object(run,'terminal',side_effect=terminal))
            self.assertEqual(run.execute(args),0)
            allocator.assert_called_once_with(.25,expected)
            self.assertEqual(calls.call_count,2)
            self.assertEqual(json.loads((args.out/'contract.json').read_text())['device'],'cuda:2')

    def test_exact_quote_budget(self):
        self.assertEqual(run.validate_request(self.args(),[{}],run.QUOTE_IDS),2)
        for args in (self.args(max_terminal_calls=3),self.args(device='cpu'),
                     self.args(deadline_unix=float('inf')),self.args(max_output_bytes=1)):
            with self.assertRaises(ValueError):run.validate_request(args,[{}],run.QUOTE_IDS)

    def test_quote_configuration_frozen(self):
        for caches,ids in (([{},{}],run.QUOTE_IDS),([{}],run.QUOTE_IDS[::-1]),([{}],run.QUOTE_IDS[:1])):
            with self.assertRaises(ValueError):run.validate_request(self.args(),caches,ids)

    def test_explicit_mapping_preserves_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            spec=dict(original_root='/data/old',local_root=directory)
            self.assertEqual(run.mapped_path(spec,'/data/old/sub/frame.json'),Path(directory).resolve()/'sub/frame.json')
            for path in ('/elsewhere/frame.json','/data/old/../outside','relative.json'):
                with self.assertRaises(ValueError):run.mapped_path(spec,path)

    def test_symlink_mapping_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'escape').symlink_to('/private/tmp',target_is_directory=True)
            with self.assertRaises(ValueError):run.mapped_path(dict(original_root='/data/old',local_root=directory),'/data/old/escape/x')

    def test_qualification_separate_admission_and_quote(self):
        with self.assertRaises(ValueError):run.validate_request(self.args(stage='qualification'),[{}],run.QUOTE_IDS)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);quote=root/'summary.json'
            contract=dict(stage='quote',campaign_id=run.CAMPAIGN_ID,detectors=run.QUOTE_IDS,calls_reserved={'F':0,'T':2,'E':0})
            contract['config_sha256']=run.config_hash(contract)
            (root/'contract.json').write_text(json.dumps(contract))
            quote.write_text(json.dumps(dict(stage='quote',status='complete',exitcode=0,calls_attempted=2,
                records=[{'identity':{'detector':i}} for i in run.QUOTE_IDS],config_sha256=contract['config_sha256'])))
            admission=root/'admission.json';value=dict(stage='qualification',campaign_id=run.CAMPAIGN_ID,
                caches=[{}],detectors=run.QUOTE_IDS,completed_quote={'path':str(quote),'sha256':run.sha(quote)})
            admission.write_text(json.dumps(value))
            args=self.args(stage='qualification',admission=admission,max_terminal_calls=4)
            self.assertEqual(run.validate_request(args,[{}],run.QUOTE_IDS),4)
            value['caches']=[{'different':True}];admission.write_text(json.dumps(value))
            with self.assertRaises(ValueError):run.validate_request(args,[{}],run.QUOTE_IDS)

    def test_development_not_admitted(self):
        with self.assertRaises(ValueError):run.validate_request(self.args(stage='development'),[{}],run.QUOTE_IDS)

    def test_cache_reads_observed_only_and_checks_hash(self):
        np=run.np
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();original='/data/synthetic'
            contract=dict(campaign_id=run.CAMPAIGN_ID,split='engineering',snr=8,start=0,stop=1,recipes=[{'id':'B0-p3-s1'}],
                source_sha256={'fake':'source'},protocol_sha256='fake',checkpoint_sha256='fake',code_sha256={'G':'fake','H':'fake'})
            contract['config_sha256']=run.config_hash(contract)
            (root/'contract.json').write_text(json.dumps(contract))
            arrays=dict(y=np.ones(1024,dtype=complex),H=np.eye(1024,dtype=complex),
                pilot=np.ones(1024,dtype=complex),sigma2_terminal=np.array(2.),
                constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            # No true H, info, or coded arrays: loader must not request them.
            raw=root/'terminal.npz';np.savez_compressed(raw,**arrays)
            h=run.array_hash(arrays['H'])
            row=dict(campaign_id=run.CAMPAIGN_ID,scenario='G0',schema='supplement-engineering-frame-v1',config_sha256=contract['config_sha256'],
                split='engineering',SNR=8,block_id=0,failure=None,truth_access_level='none',recipe=contract['recipes'][0],
                arm_id='B0-p3-s1',terminal={'path':original+'/terminal.npz','bytes':raw.stat().st_size,'sha256':run.sha(raw)},
                H_cancel_source={'sha256':h},H_data_source={'sha256':h},sigma_value=2.,
                input_hashes={k:run.array_hash(arrays[k]) for k in ('y','pilot')})
            row['metadata']=dict(split='engineering',block=0,snr_db=8,protocol_sha256=contract['protocol_sha256'],input_hashes=row['input_hashes'])
            row.update({k:contract[k] for k in ('source_sha256','protocol_sha256','checkpoint_sha256','code_sha256')})
            frame=root/'frame.json';frame.write_text(json.dumps(row))
            summary=dict(config_sha256=contract['config_sha256'],status='complete',exitcode=0,failures=[],calls_attempted=1,calls_completed=1,
                records=[{'path':original+'/frame.json','sha256':run.sha(frame)}])
            (root/'summary.json').write_text(json.dumps(summary))
            spec=dict(original_root=original,local_root=str(root),record=original+'/frame.json')
            data,proof=run.load_cache(spec)
            self.assertTrue(np.array_equal(data['y_cancelled'],np.zeros(1024)))
            self.assertEqual(float(data['sigma2_terminal']),2.)
            self.assertEqual(proof['truth_access'],'none')
            # Synthetic re-namespace fixture exercises design block191 and split rejection.
            contract.update(split='design',start=191,stop=192)
            contract['config_sha256']=run.config_hash(contract)
            row.update(split='design',block_id=191,schema='supplement-baseline-design-frame-v1',config_sha256=contract['config_sha256'])
            row['metadata'].update(split='design',block=191)
            (root/'contract.json').write_text(json.dumps(contract));frame.write_text(json.dumps(row))
            summary['config_sha256']=contract['config_sha256'];summary['records'][0]['sha256']=run.sha(frame)
            (root/'summary.json').write_text(json.dumps(summary))
            with self.assertRaises(ValueError):run.load_cache(spec)
            with self.assertRaises(ValueError):run.load_cache(spec,split='design')
            with self.assertRaises(ValueError):run.load_cache(spec,split='design',baseline='wrong-reference')
            data,proof=run.load_cache(spec,split='design',baseline='B0-p3-s1')
            self.assertEqual((proof['split'],proof['block']),('design',191))
            self.assertEqual(set(data),{'y','H','pilot','sigma2_terminal','constellation','y_cancelled'})
            raw.write_bytes(b'tampered')
            with self.assertRaises(ValueError):run.load_cache(spec)

    def test_existing_output_rejected_and_failure_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(out=Path(directory)/'out',caches='[{}]',detectors=json.dumps(run.QUOTE_IDS))
            previous_handler=signal.getsignal(signal.SIGALRM)
            with patch.object(run.torch,'set_num_threads'), patch.object(run.torch,'set_num_interop_threads'):
                with patch.object(run.torch.cuda,'is_available',return_value=False):
                    with self.assertRaisesRegex(ValueError,'CUDA unavailable'):run.execute(args)
            self.assertIs(signal.getsignal(signal.SIGALRM),previous_handler)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL)[0],0)
            failure=json.loads((args.out/'batch-failure.json').read_text())
            self.assertEqual(failure['status'],'failed')
            self.assertEqual(failure['calls_attempted'],0)
            with self.assertRaises(FileExistsError):run.execute(args)

    def test_source_change_explicit(self):
        with self.assertRaises(ValueError):run.unchanged({'source_sha256':{},'caches':[]})

    def test_qualification_requires_all_caches_for_at_least_one_detector(self):
        rows=[dict(cache=c,detector=d,result={'stable':False}) for c in (0,1) for d in ('a','b')]
        qualified,passed=run.qualification_summary(rows,['a','b'],2)
        self.assertFalse(passed)
        rows[0]['result']['stable']=True
        self.assertFalse(run.qualification_summary(rows,['a','b'],2)[1])
        rows[2]['result']['stable']=True
        qualified,passed=run.qualification_summary(rows,['a','b'],2)
        self.assertEqual(qualified,{'a':True,'b':False})
        self.assertTrue(passed)
        with self.assertRaises(ValueError):run.qualification_summary(rows[:-1],['a','b'],2)

    def test_real_baseline_cache_read_only_compatibility(self):
        root=Path(__file__).resolve().parent/'outputs_comprehensive_supplement_20260909/baseline-smoke-v1'
        if not (root/'summary.json').exists():self.skipTest('real cache absent')
        summary=json.loads((root/'summary.json').read_text())
        record=next(s['path'] for s in summary['records'] if s['path'].endswith('frame-000-B0-p3-s1.json'))
        data,proof=run.load_cache(dict(original_root=str(Path(record).parent),local_root=str(root),record=record))
        self.assertEqual((proof['block'],proof['baseline']),(0,'B0-p3-s1'))
        self.assertEqual(set(data),{'y','H','pilot','sigma2_terminal','constellation','y_cancelled'})
        run.np.testing.assert_array_equal(data['y_cancelled'],data['y']-data['H']@data['pilot'])

    def test_zero_F_two_T_reservation_recovers_legacy_profile_counts(self):
        profile=Path(__file__).resolve().parent/'outputs_comprehensive_supplement_20260909/profile-v1'
        if not (profile/'contract.json').exists():self.skipTest('real legacy profile absent')
        old=json.loads((profile/'contract.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);ledger=root/'supplement-engineering-ledger';ledger.mkdir()
            legacy={'campaign_id':run.CAMPAIGN_ID,'out':str(profile),
                'max_full_calls':3,'contract_sha256':old['config_sha256']}
            (ledger/'reservation-legacy.json').write_text(json.dumps(legacy))
            contract=dict(max_full_calls=0,calls_reserved={'F':0,'T':2,'E':0},config_sha256='fixture')
            run.reserve_profile(root/'quote',contract)
            run.reserve_profile(root/'rest',dict(contract,calls_reserved={'F':0,'T':251,'E':0}))
            with self.assertRaisesRegex(ValueError,'F128/T256/E128'):
                run.reserve_profile(root/'overflow',dict(contract,calls_reserved={'F':0,'T':1,'E':0}))


if __name__=='__main__':unittest.main()
