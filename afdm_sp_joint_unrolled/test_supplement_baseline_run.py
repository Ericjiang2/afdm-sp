"""Unit fixtures only; not real baseline/receiver qualification."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from . import supplement_baseline_run as runner


class BaselineRunTests(unittest.TestCase):
    def args(self,out,**changes):
        value=dict(out=out,protocol=Path('p.json'),checkpoint=Path('checkpoint'),split='engineering',
            start=0,stop=1,snr=8,device='cpu',recipes='["B0-p0-s0.5","B0-p1-s0.5"]',
            max_full_calls=2,deadline_unix=time.time()+60,max_output_bytes=1024**3)
        value.update(changes);return SimpleNamespace(**value)

    def bind_a02_protocol(self,args,root):
        args.protocol=root/'data.json';args.protocol.write_text('{}')
        args.checkpoint=root/'checkpoint';args.checkpoint.write_bytes(b'checkpoint')
        value=dict(schema=runner.A02_PROTOCOL_SCHEMA,campaign_id=runner.CAMPAIGN_ID,
            stage=runner.A02_STAGE,split='design',block_start=0,block_stop=192,snrs=[8],
            recipe_ids=[row['id'] for row in runner.a02_catalogue()],total_F=1728,
            data_protocol_sha256=runner.sha(args.protocol),checkpoint_sha256=runner.sha(args.checkpoint),
            batch_policy=runner.A02_BATCH_POLICY)
        args.a02_protocol=root/'a02.json';args.a02_protocol.write_text(json.dumps(value))
        args.a02_protocol_sha256=runner.sha(args.a02_protocol);args.recipes=None
        return args

    def test_split_budget_and_storage_domains(self):
        a=self.args(Path('out'))
        self.assertEqual(len(runner.validate_args(a)[0]),2)
        for changes in (dict(split='confirm'),dict(stop=33),dict(snr=7),dict(max_full_calls=1),
                        dict(max_output_bytes=1),dict(recipes='["B0-p0-s0.5","B0-p0-s0.5"]')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                runner.validate_args(self.args(Path('out'),**changes))
        self.assertEqual(len(runner.validate_args(self.args(Path('out'),split='design',start=160,stop=176,
            max_full_calls=32,max_output_bytes=2*1024**3))[0]),2)

    def test_a02_requires_exact_nine_arm_same_block_batches(self):
        ids=[row['id'] for row in runner.a02_catalogue()]
        with tempfile.TemporaryDirectory() as d:
            args=self.bind_a02_protocol(self.args(Path('out'),stage=runner.A02_STAGE,split='design',
                start=7,stop=9,max_full_calls=18,max_output_bytes=1024**3),Path(d))
            recipes,_=runner.validate_args(args)
            self.assertEqual([row['id'] for row in recipes],ids)
            for changes in (dict(split='engineering'),dict(snr=7),dict(max_full_calls=19),
                            dict(recipes=json.dumps(ids))):
                with self.subTest(changes=changes),self.assertRaises(ValueError):
                    runner.validate_args(SimpleNamespace(**dict(vars(args),**changes)))
            with self.assertRaises(ValueError):
                runner.validate_args(SimpleNamespace(**dict(vars(args),a02_protocol_sha256='0'*64)))
            with self.assertRaises(ValueError):
                runner.validate_args(self.args(Path('out'),stage=runner.BASE_STAGE,split='design',
                    recipes=json.dumps(ids),max_full_calls=9))

    def test_shared_design_cap_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);c=dict(max_full_calls=7679,config_sha256='a'*64,start=0,stop=191,
                recipes=[{'id':str(i)} for i in range(40)])
            runner.reserve_design(root/'first',c)
            with self.assertRaises(ValueError):runner.reserve_design(root/'second',dict(c,max_full_calls=2,start=191,stop=192,recipes=[{'id':'0'},{'id':'1'}]))
            with self.assertRaisesRegex(ValueError,'already reserved'):
                runner.reserve_design(root/'duplicate',dict(c,max_full_calls=40,start=0,stop=1))
            runner.reserve_design(root/'last',dict(c,max_full_calls=1,start=191,stop=192,recipes=[{'id':'0'}]))

    def test_a02_cuda_allocator_cap_is_applied_and_cpu_base_unchanged(self):
        with patch.object(runner.torch.cuda,'set_per_process_memory_fraction') as setter:
            device=runner.torch.device('cuda:0')
            self.assertEqual(runner.configure_a02_allocator(device,runner.A02_STAGE),.25)
            setter.assert_called_once_with(.25,device)
            setter.reset_mock()
            self.assertIsNone(runner.configure_a02_allocator(runner.torch.device('cpu'),runner.A02_STAGE))
            self.assertIsNone(runner.configure_a02_allocator(device,runner.BASE_STAGE))
            setter.assert_not_called()

    def test_a02_rejects_duplicate_prior_ledger_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            contract=dict(stage=runner.A02_STAGE,split='design',start=0,stop=1,
                          recipes=runner.a02_catalogue(),max_full_calls=9,config_sha256='a'*64,
                          source_sha256={},checkpoint_sha256='c',protocol_sha256='p',
                          a02_protocol_sha256='a')
            ledger=Path(runner.reserve_a02(root/'first',contract))
            path=next(ledger.glob('reservation-*.json'))
            prior=json.loads(path.read_text());prior['identities'].append(prior['identities'][0])
            path.write_text(json.dumps(prior))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                runner.reserve_a02(root/'second',dict(contract,start=1,stop=2,config_sha256='b'*64))

    def test_a02_has_independent_exact_identity_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);recipes=runner.a02_catalogue()
            contract=dict(stage=runner.A02_STAGE,split='design',start=0,stop=1,
                          max_full_calls=9,config_sha256='a'*64,recipes=recipes,
                          source_sha256={'s':'1'},checkpoint_sha256='c',protocol_sha256='p',
                          a02_protocol_sha256='a')
            ledger=runner.reserve_a02(root/'first',contract)
            self.assertEqual(Path(ledger).name,'supplement-a02-development-ledger')
            row=json.loads(next(Path(ledger).glob('reservation-*.json')).read_text())
            self.assertEqual(row['calls_reserved'],{'F':9,'T':0,'E':0})
            self.assertEqual(len(row['identities']),9)
            with self.assertRaisesRegex(ValueError,'already reserved'):
                runner.reserve_a02(root/'duplicate',contract)
            runner.reserve_a02(root/'second',dict(contract,start=1,stop=2,config_sha256='b'*64))
            self.assertFalse((root/'supplement-baseline-design-ledger').exists())

    def fixture(self):
        obs=dict(y=np.ones(2,complex),pilot=np.zeros(2,complex),sigma2=np.array(1.),
                 constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        truth=dict(info=np.zeros(2,np.uint8),coded=np.zeros(4,np.uint8))
        meta=dict(split='engineering',block=0,snr_db=8,protocol_sha256=runner.CHECKPOINT_HASH,input_hashes={k:runner.array_hash(obs[k]) for k in ('y','pilot')})
        result=dict(H=np.eye(2,dtype=complex),x_soft=np.ones(2,complex),gains=np.ones(1,complex),
            support=[2],sigma2=1.,sigma2_terminal=1.,mu=np.ones(2,complex),var=np.ones(2),
            llr=np.ones(4),decoded=np.zeros(4,np.uint8),info_hat=np.zeros(2,np.uint8),
            x_hard=np.ones(2,complex),decode_ok=True,seconds=.1,initial_estimator={'converged':True},
            baseline_eligible=True,capacity_trace=[],graphs=[])
        return SimpleNamespace(observed=obs,_truth=truth,metadata=meta),result

    def test_complete_terminal_snapshot_exclusive_and_shape(self):
        frame,result=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'terminal.npz';record=runner.terminal_snapshot(p,frame,result)
            with np.load(p) as raw:
                for key in ('H','x_soft','gains','support','sigma2','mu','var','llr','decoded','info_hat','x_hard'):
                    self.assertIn(key,raw)
            self.assertEqual(record['bytes'],p.stat().st_size)
            runner.terminal_snapshot(Path(d)/'empty-support.npz',frame,
                dict(result,support=[],gains=np.zeros(0,dtype=complex)))
            with self.assertRaises(FileExistsError):runner.terminal_snapshot(p,frame,result)
            with self.assertRaises(ValueError):
                runner.terminal_snapshot(Path(d)/'bad.npz',frame,dict(result,H=np.ones((2,1))))

    def test_failure_kept_and_other_recipe_completes(self):
        frame,result=self.fixture();seen=[]
        class FakeReceiver:
            def __init__(self,model,code,identifier,**kw):self.identifier=identifier
            def run(self,observed,**kw):
                self_outer.assertIs(observed,frame.observed)
                seen.append(self.identifier)
                if self.identifier=='B0-p0-s0.5':raise RuntimeError('fixture algorithm failure')
                return result
        self_outer=self
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'batch'
            with patch.object(runner,'sha',return_value=runner.CHECKPOINT_HASH), \
                 patch.object(runner,'sources',return_value={}), \
                 patch.object(runner,'build_code',return_value={'G':np.eye(2),'H':np.eye(2)}), \
                 patch.object(runner,'SupplementData') as data,patch.object(runner,'_make_config_a'), \
                 patch.object(runner,'build_receiver'),patch.object(runner,'BaselineReceiver',FakeReceiver), \
                 patch.object(runner,'assert_content_unchanged'):
                data.return_value.make_frame.return_value=frame
                self.assertEqual(runner.execute(self.args(out)),1)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(set(seen),{'B0-p0-s0.5','B0-p1-s0.5'})
            self.assertEqual(summary['status'],'completed_with_failures')
            self.assertEqual((summary['calls_attempted'],summary['calls_completed']),(2,1))
            self.assertEqual(len(summary['failures']),1)
            self.assertEqual(summary['missing_or_failed_identities'],[dict(block=0,arm_id='B0-p0-s0.5',split='engineering')])
            failure=json.loads(next(out.glob('failure-*.json')).read_text())
            self.assertIsNone(failure['FER'])
            self.assertEqual(failure['identity']['arm_id'],'B0-p0-s0.5')
            with self.assertRaises(FileExistsError):runner.execute(self.args(out))

    def test_a02_execute_runs_all_nine_on_one_design_frame_and_keeps_raw_terminal(self):
        frame,result=self.fixture();frame.metadata.update(split='design',block=0)
        ids=[row['id'] for row in runner.a02_catalogue()];seen=[]
        class FakeReceiver:
            def __init__(self,model,code,identifier,**kwargs):self.identifier=identifier
            def run(self,observed,**kwargs):
                self_outer.assertIs(observed,frame.observed);seen.append(self.identifier)
                detail={'converged':False,'query_count':3243 if self.identifier=='A02-reference' else 73,
                        'query_limit':3243 if self.identifier=='A02-reference' else 73,'fallback':None}
                return dict(result,baseline_stationary=False,
                    deployment_eligible=False if self.identifier=='A02-reference' else None,
                    channel_refit={'diagnostics':detail})
        self_outer=self
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'a02'
            args=self.bind_a02_protocol(self.args(out,stage=runner.A02_STAGE,split='design',
                                                  max_full_calls=9),Path(d))
            frame.metadata['protocol_sha256']=runner.sha(args.protocol)
            checkpoint_hash=runner.sha(args.checkpoint)
            with patch.object(runner,'CHECKPOINT_HASH',checkpoint_hash), \
                 patch.object(runner,'sources',return_value={}), \
                 patch.object(runner,'build_code',return_value={'G':np.eye(2),'H':np.eye(2)}), \
                 patch.object(runner,'SupplementData') as data,patch.object(runner,'_make_config_a'), \
                 patch.object(runner,'build_receiver'),patch.object(runner,'BaselineReceiver',FakeReceiver), \
                 patch.object(runner,'assert_content_unchanged'), \
                 patch.object(runner,'reserve_a02',return_value='/a02-ledger'):
                data.return_value.make_frame.return_value=frame
                self.assertEqual(runner.execute(args),0)
            self.assertEqual(set(seen),set(ids));self.assertEqual(len(seen),9)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual((summary['calls_attempted'],summary['calls_completed']),(9,9))
            self.assertEqual(summary['reservation_ledger'],'/a02-ledger')
            self.assertEqual(len(list(out.glob('terminal-*.npz'))),9)
            reference=json.loads(next(out.glob('frame-*-A02-reference.json')).read_text())
            self.assertFalse(reference['deployment_eligible'])
            self.assertEqual(reference['channel_refit']['query_count'],3243)
            self.assertIsNone(reference['channel_refit']['fallback'])

    def test_design_record_retains_real_block_not_engineering_alias(self):
        frame,result=self.fixture();frame.metadata.update(split='design',block=170)
        c=dict(config_sha256='c',source_sha256={},checkpoint_sha256='k',code_sha256={},device='cpu')
        recipe=runner.recipe_by_id('B0-p1-s0.5')
        row=runner.make_record(frame,result,recipe,c,.1,.1,0)
        self.assertEqual((row['split'],row['block_id']),('design',170))
        self.assertEqual(row['FER'],0)
        self.assertNotIn('development_stage',row);self.assertNotIn('deployment_eligible',row)
        with self.assertRaises(ValueError):
            runner.make_record(frame,dict(result,info_hat=np.zeros((2,1))),recipe,c,.1,.1,0)

    def test_a02_record_retains_reference_audit_and_nondeployment(self):
        frame,result=self.fixture();frame.metadata.update(split='design',block=11)
        result.update(baseline_stationary=False,deployment_eligible=False,
            channel_refit={'diagnostics':{'converged':False,'reference_unconverged':True,
                'query_count':3243,'query_limit':3243,'fallback':None}})
        contract=dict(stage=runner.A02_STAGE,config_sha256='c',source_sha256={},
                      checkpoint_sha256='k',code_sha256={},device='cpu')
        recipe=runner.recipe_by_id('A02-reference')
        row=runner.make_record(frame,result,recipe,contract,.1,.1,0)
        self.assertEqual(row['schema'],'supplement-A02-development-frame-v1')
        self.assertFalse(row['deployment_eligible']);self.assertFalse(row['baseline_stationary'])
        self.assertEqual(row['channel_refit']['query_count'],3243)
        self.assertIsNone(row['channel_refit']['fallback'])
        self.assertEqual(row['offline_truth_access'],'evaluation_only')
        with self.assertRaisesRegex(ValueError,'reference'):
            runner.make_record(frame,dict(result,deployment_eligible=True),recipe,contract,.1,.1,0)
        with self.assertRaisesRegex(ValueError,'refit audit'):
            runner.make_record(frame,dict(result,channel_refit={'diagnostics':{'converged':False}}),
                               recipe,contract,.1,.1,0)

    def test_storage_rejects_before_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'failure.json'
            with self.assertRaisesRegex(OSError,'storage budget'):
                runner.publish_bounded(path,{'error':'x'*1000},root,100)
            self.assertFalse(path.exists())
            self.assertEqual(runner.output_bytes(root),0)
            runner.publish_bounded(path,{'error':'kept'},root,100)
            self.assertLessEqual(runner.output_bytes(root),100)

    def test_snapshot_rejects_invalid_variance_and_bits(self):
        frame,result=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            for change in [dict(sigma2_terminal=-1),dict(var=np.zeros(2)),dict(decoded=np.full(4,2))]:
                with self.assertRaisesRegex(ValueError,'variance or bit'):
                    runner.terminal_snapshot(Path(d)/'bad.npz',frame,dict(result,**change))
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_frame_identity_is_checked_before_use(self):
        frame,_=self.fixture()
        runner.validate_frame_identity(frame,'engineering',0,runner.CHECKPOINT_HASH)
        for split,block,digest in [('design',0,runner.CHECKPOINT_HASH),
                                   ('engineering',1,runner.CHECKPOINT_HASH),('engineering',0,'wrong')]:
            with self.assertRaisesRegex(ValueError,'identity/input'):
                runner.validate_frame_identity(frame,split,block,digest)
        frame.observed['y'][0]+=1
        with self.assertRaisesRegex(ValueError,'identity/input'):
            runner.validate_frame_identity(frame,'engineering',0,runner.CHECKPOINT_HASH)


if __name__=='__main__':unittest.main()
