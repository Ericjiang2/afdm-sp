"""Synthetic development runner contracts; no N1024 receiver execution."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import time
import json
import numpy as np
from unittest.mock import patch
from . import supplement_feedback_run as r


class FeedbackRunTests(unittest.TestCase):
    def test_exact_domain_and_schedule(self):
        keys=set()
        for b in range(0,192,16):keys.update(r.identities(b,b+16))
        self.assertEqual(len(keys),3456)
        self.assertEqual({r.bp_count(a) for a in ('I0','I2')},{20})
        self.assertEqual({r.bp_count(a) for a in r.ARMS if a not in ('I0','I2')},{12})
        for start,stop in ((0,17),(-1,1),(191,193),(2,2)):
            with self.assertRaises(ValueError):r.identities(start,stop)

    def test_ledger_duplicate_binding_and_full_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=Path(directory)
            for b in range(0,192,16):
                ids=r.identities(b,b+16)
                c=dict(campaign_id=r.CAMPAIGN_ID,identities=ids,max_full_calls=len(ids),
                    calls_reserved={'F':len(ids),'T':0,'E':0},bindings={'synthetic':'fixed'},config_sha256=str(b))
                r.reserve(ledger,c)
            with self.assertRaises(ValueError):r.reserve(ledger,c)
            self.assertEqual(len(list(ledger.glob('reservation-*.json'))),12)
            c=dict(c,bindings={'synthetic':'changed'},config_sha256='new')
            with self.assertRaises(ValueError):r.reserve(ledger,c)

    def test_protocol_binds_quote_and_both_checkpoint_results(self):
        digest='a'*64
        protocol=r._expected_protocol(digest)
        quote=dict(status='complete',attempted_F=72,selected={'1':12,'4':None},
            scope='two engineering blocks; instrumented complete F; no FER-based selection or COST02 inference')
        self.assertEqual(r.validate_protocol(protocol,quote,digest),protocol)
        for mutation in (
                lambda p,q:p.update(checkpoint=4),
                lambda p,q:p.update(extra='undeclared'),
                lambda p,q:q['selected'].update({'4':12}),
                lambda p,q:q.update(attempted_F=71)):
            p=dict(protocol);p['arms']=list(protocol['arms']);p['snrs']=list(protocol['snrs']);p['bp_counts']=dict(protocol['bp_counts'])
            q=dict(quote);q['selected']=dict(quote['selected'])
            mutation(p,q)
            with self.assertRaises(ValueError):r.validate_protocol(p,q,digest)

    def test_limits_are_exact_and_finite(self):
        count=len(r.identities(0,1));base=dict(start=0,stop=1,max_full_calls=count,
            threads=1,deadline_unix=time.time()+60,max_output_bytes=count*r.PER_TERMINAL_BYTES+32*1024**2,
            device='cpu')
        ids,estimated=r.validate_args(SimpleNamespace(**base))
        self.assertEqual(len(ids),18);self.assertEqual(estimated,base['max_output_bytes'])
        for key,value in (('threads',2),('max_full_calls',17),('deadline_unix',float('inf')),
                          ('max_output_bytes',1),('device','')):
            changed=dict(base);changed[key]=value
            with self.assertRaises(ValueError):r.validate_args(SimpleNamespace(**changed))

    def test_dense_audit_arrays_are_hashed_not_serialized(self):
        matrix=np.arange(12,dtype=np.float64).reshape(3,4)
        compact=r.compact_audit({'CE':[{'A':matrix,'iteration':1}]})
        saved=compact['CE'][0]['A']
        self.assertEqual(saved,{'array_sha256':r.array_hash(matrix),'dtype':'float64','shape':[3,4]})
        self.assertNotIn(matrix.tolist(),compact['CE'])
        with self.assertRaises(ValueError):r.compact_audit(np.array([np.nan]))

    def test_arm_controllers_keep_legal_and_oracle_interfaces_separate(self):
        code={'n':4}
        symbols=np.array([.5+.5j,.5-.5j])
        self.assertIsNone(r._controller(code,'I0'))
        self.assertEqual(r._controller(code,'Irealloc').control,'zero')
        self.assertEqual(r._controller(code,'Isham').control,'fixed_sham')
        self.assertEqual(r._controller(code,'I1').control,'legal')
        for arm in ('I2','I2realloc'):
            controller=r._controller(code,arm,symbols)
            self.assertEqual(controller.tag,arm)
            self.assertEqual(controller.feedback is not None,arm=='I2realloc')

    def test_legal_controller_construction_never_reads_truth(self):
        class RejectTruth:
            def __getitem__(self,key):
                raise AssertionError('legal path read truth')
        truth=RejectTruth();code={'n':4}
        for arm in ('I0','Irealloc','Isham','I1'):
            # This is the exact caller branch: truth is indexed only in the oracle arm.
            controller=(r._controller(code,arm,truth['data']) if arm in ('I2','I2realloc')
                        else r._controller(code,arm))
            self.assertEqual(controller is None,arm=='I0')
        with self.assertRaisesRegex(ValueError,'true-symbol'):
            r._controller(code,'I2')

    def test_complete_consumer_audit_is_required(self):
        def result(arm):
            count=r.bp_count(arm)
            feedback=[]
            if arm in ('Irealloc','Isham','I1','I2realloc'):
                feedback=([{'stage':'detector_consume'} for _ in range(10)]+
                          [{'stage':'CE_consume'} for _ in range(9)]+[{'stage':'decoder'}])
            value=dict(bp_schedule={'outer_iterations':10,'outer_bp_iterations':count,
                    'final_bp_iterations':20,'final_ldpc_maxiter':50,
                    'calls':[{'outer_iter':i,'requested_iterations':count} for i in range(10)]},
                dals=[{} for _ in range(9)],
                graphs=[{'stage':'outer_bp'} for _ in range(10)]+[{'stage':'final_bp'}],
                support_trace=[],capacity_trace={},initial_estimator={})
            if arm not in ('I0','I2'):value['code_feedback_records']=feedback
            if arm in ('I2','I2realloc'):
                value.update(truth_access_level='true_symbols_oracle',diagnostic_consumption_records=[
                    {'tag':arm,'status':'consumed','checkpoint':1,'outer_iter':2,
                     'truth_access':'true_symbols_oracle'}])
            return value
        for arm in r.ARMS:r.validate_result_audit(result(arm),arm)
        broken=result('I1');broken['dals'].pop()
        with self.assertRaisesRegex(ValueError,'nine'):r.validate_result_audit(broken,'I1')
        broken=result('I2');broken['diagnostic_consumption_records'][0]['outer_iter']=3
        with self.assertRaisesRegex(ValueError,'oracle'):r.validate_result_audit(broken,'I2')
        broken=result('I0');broken['graphs'].pop()
        with self.assertRaisesRegex(ValueError,'graph'):r.validate_result_audit(broken,'I0')

    def test_execute_interrupt_preserves_started_identity_in_batch_failure(self):
        class InterruptReceiver:
            entered=False
            def run(self,*args,**kwargs):
                self.entered=True
                raise KeyboardInterrupt()
            def run_diagnostic(self,*args,**kwargs):raise KeyboardInterrupt()
        class RejectTruth:
            def __getitem__(self,key):raise AssertionError('legal execute path read truth')
        class FakeData:
            def make_frame(self,*args,**kwargs):
                return SimpleNamespace(metadata={'input_hashes':{}},_truth=RejectTruth(),observed={})
        class I0First:
            def shuffle(self,items):items.sort(key=lambda identity:identity[2]!='I0')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);development=root/'development.json';quote=root/'quote.json'
            development.write_text(json.dumps(r._expected_protocol('q')))
            quote.write_text(json.dumps({'status':'complete','attempted_F':72,
                'selected':{'1':12,'4':None},
                'scope':'two engineering blocks; instrumented complete F; no FER-based selection or COST02 inference'}))
            count=len(r.identities(0,1));args=SimpleNamespace(protocol=root/'data.json',
                development_protocol=development,quote=quote,checkpoint=root/'checkpoint.pt',
                out=root/'out',start=0,stop=1,max_full_calls=count,
                max_output_bytes=count*r.PER_TERMINAL_BYTES+32*1024**2,
                threads=1,deadline_unix=time.time()+60,device='cpu')
            bindings={'files':{'protocol':'p','development_protocol':'d','quote':'q',
                               'checkpoint':r.CHECKPOINT_HASH},'source_sha256':{}}
            disk=SimpleNamespace(free=10**12)
            fake_code={'n':4,'G':np.zeros((1,1),dtype=np.uint8),'H':np.zeros((1,1),dtype=np.uint8)}
            receiver=InterruptReceiver()
            with patch.object(r,'_bindings',return_value=bindings), \
                 patch.object(r,'assert_unchanged'), \
                 patch.object(r.shutil,'disk_usage',return_value=disk), \
                 patch.object(r,'build_code',return_value=fake_code), \
                 patch.object(r,'_make_config_a',return_value=object()), \
                 patch.object(r,'SupplementData',return_value=FakeData()), \
                 patch.object(r,'campaign_rng',return_value=I0First()), \
                 patch('afdm_sp_joint_unrolled.budgeted_support_eval.build_receiver',return_value=object()), \
                 patch.object(r,'BaselineReceiver',return_value=receiver):
                with self.assertRaises(KeyboardInterrupt):r.execute(args)
            failure=json.loads((args.out/'batch-failure.json').read_text())
            started=json.loads((args.out/f"call-{failure['calls_attempted']:05d}-started.json").read_text())
            self.assertEqual(failure['active_identity'],started['identity'])
            self.assertEqual(started['identity'],[0,7,'I0'])
            self.assertEqual(failure['exception'],'KeyboardInterrupt')
            self.assertTrue(receiver.entered)
            self.assertEqual(failure['calls_attempted'],1)
            self.assertEqual(failure['calls_completed'],0)


if __name__=='__main__':unittest.main()
