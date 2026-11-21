"""Synthetic contracts only; receiver stubs are not scientific simulations."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('__gram_cohort_test', Path(__file__).with_name('gram_cohort.py'))
g = importlib.util.module_from_spec(spec);spec.loader.exec_module(g)


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def row_digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()


def deep_equal(a, b):
    if type(a) is not type(b):return ['type']
    if isinstance(a, dict):return [] if set(a)==set(b) and all(not deep_equal(a[k], b[k]) for k in a) else ['dict']
    if isinstance(a, list):return [] if len(a)==len(b) and all(not deep_equal(x,y) for x,y in zip(a,b)) else ['list']
    return [] if np.array_equal(a,b) else ['value']


class GramCohortTest(unittest.TestCase):
    def setUp(self):
        self.prior = np.zeros(4)
        self.sha = digest(self.prior)
        score = dict(info_errors=0, fer=0, decoded_sha256='0'*64, ldpc_iters=2, extrinsic_bit_logloss=.2,
                     nmse_final=.1, data_mse_final=.3, symbol_variance_final=.4)
        terminal = dict(h=[[1., 0.]], channel_nmse=.1, data_mse=.3, symbol_variance=.4)
        mode = {k:score[k] for k in ('info_errors','fer','decoded_sha256','ldpc_iters','extrinsic_bit_logloss')}
        mode['trajectory'] = [copy.deepcopy(terminal) for _ in range(21)]
        self.three, self.run2 = {}, {}
        for key in g.EXPECTED:
            sc,rho,snr,frame = key
            meta = dict(scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=frame)
            saved = dict(support=dict(delays=[1],dopplers=[.25]),h0=[[1.,0.]],prior_sha256=self.sha,
                         modes={m:copy.deepcopy(mode) for m in ('fixed','point','joint')})
            self.three[key] = dict(meta, three_mode={v:copy.deepcopy(saved) for v in g.VARIANTS})
            self.run2[key] = dict(meta, support=saved['support'], h0=saved['h0'], h20=saved['h0'],
                                 input_sha256=dict(prior=self.sha, h0='fixture', h20='fixture'),prior=self.prior.tolist())
        self.calls, self.decode_calls, self.fail_at = 0, 0, None

        def detector(y,pilot,c,noise,record_states=True,gain_mode=None,gain_block=None,**kwargs):
            self.calls += 1
            if self.calls == self.fail_at:raise RuntimeError('fixture receiver failure')
            block = gain_block in ('full','diag')
            det = dict(extrinsic=np.ones(4),app=np.ones(4),mu=np.zeros(2,complex),variance=np.ones(2),
                       gains=c.gains.copy(),gain_variance=np.zeros(c.p),iterations=20,fft_count=61 if block else 41,
                       trace=[dict(iteration=i,gain_variance=0.,fft_count=3 if block else 2) for i in range(20)])
            if record_states:det['states']=[dict(h=c.gains.copy(),mu=np.zeros(2),v=np.ones(2),s=np.zeros(2),vh=0.) for _ in range(20)]
            if block:
                det.update(gain_solve_calls=20,covariance_solve_calls=20,gamma_fft_count=20,native_symbol_fft_count=41,
                    gain_blocks=[dict(iteration=i,alpha=noise*c.p,gamma_fft_count=1,normal_relative_residual=0.,
                        covariance_relative_residual=0.,seconds=.01*self.calls,solve_seconds=.001*self.calls,
                        covariance=np.eye(c.p)) for i in range(20)])
            return det

        def scorer(*args):
            self.decode_calls += 1
            return dict(score,detect_seconds=args[-1],decode_seconds=.001)

        key_of = lambda r:(r['scenario'],r['rho_permille'],r['snr_centi_db'],r['frame'])
        channel = lambda ctx,n,delays,dopplers,h:NS(n=n,p=len(h),gains=np.asarray(h,complex))
        complex_array = lambda pairs:np.asarray(pairs)[:,0]+1j*np.asarray(pairs)[:,1]
        self.helper = NS(e3d=NS(key_of=key_of,make_channel=channel,e3_lib=NS(deep_equal=deep_equal)),
            aggregate=NS(array_sha=digest,row_sha=row_digest,restore_inputs=lambda row:(np.array([1.+0j]),np.array(row['prior'])),
                         load_reference=lambda path:(self.run2,dict(identity=dict(old_raw_sha256={'fixture':'hash'})))),
            replay=NS(complex_array=complex_array,score_arm=scorer,oldd=NS(pairs=lambda h:np.stack([h.real,h.imag],axis=-1).tolist())),
            qualify_sources=lambda ctx,receipt:None)
        self.trajectory = NS(load=lambda *args:(list(self.three.values()),dict(raw_sha256={'fixture':'hash'}),{}))
        self.ctx = NS(code=None,encode=lambda code,info:np.zeros(4,dtype=int),system=NS(rho=.3),native=NS(scalar_joint=detector))
        self.block = NS(scalar_point=detector)
        self.meta = {k:self.three[g.KEY][k] for k in ('scenario','rho_permille','snr_centi_db','frame')}
        self.obs = dict(y=np.ones(2),pilot=np.ones(2),sigma2=.2)
        self.truth = dict(info=np.zeros(2),coded=np.zeros(4,dtype=int))

    def test_references_and_both_variant_prior_gates(self):
        args = NS(three_rows=Path('/fixture/run1'),old_rows=Path('/fixture/run2'))
        three,run2,receipt = g.load_references(args,self.ctx,self.helper,self.trajectory)
        self.assertEqual(len(three),200)
        self.assertEqual(set(receipt),{'three','run2'})
        self.assertEqual(self.calls,0)
        self.three[g.KEY]['three_mode']['L-cov']['prior_sha256']='corrupted'
        with self.assertRaisesRegex(ValueError,'variant prior'):
            g.load_references(args,self.ctx,self.helper,self.trajectory)
        self.assertEqual(self.calls,0)

    def test_reference_coverage_and_raw_binding_fail(self):
        args = NS(three_rows=Path('/fixture/run1'),old_rows=Path('/fixture/run2'))
        removed = self.run2.pop(g.KEY)
        with self.assertRaises(ValueError):g.load_references(args,self.ctx,self.helper,self.trajectory)
        self.run2[g.KEY]=removed
        self.trajectory.load=lambda *args:(list(self.three.values()),dict(raw_sha256={'wrong':'hash'}),{})
        with self.assertRaisesRegex(ValueError,'raw binding'):
            g.load_references(args,self.ctx,self.helper,self.trajectory)

    def test_rotation_is_balanced_without_outcomes(self):
        counts=np.zeros((10,10),int)
        for row in self.three.values():
            order=g.arm_order(row)
            self.assertEqual(set(order),set(g.ARMS))
            for position,arm in enumerate(order):counts[position,g.ARMS.index(arm)]+=1
        np.testing.assert_array_equal(counts,np.full((10,10),20))

    def process(self,gate=False):
        return g.process_key(self.ctx,self.helper,self.block,None,None,self.meta,self.obs,np.zeros(2),self.truth,
                             self.three[g.KEY],self.run2[g.KEY],gate=gate)

    def test_main_and_gate_actual_call_counts_and_compact_schema(self):
        row=self.process(gate=True)
        self.assertEqual(row['status'],'ok',row.get('error'))
        self.assertEqual((row['receiver_calls'],row['decoder_calls']),(10,10))
        self.assertEqual((row['gate_receiver_calls'],self.calls,self.decode_calls),(6,16,10))
        self.assertTrue(row['observer_parity'])
        self.assertTrue(row['old_baseline_replay'])
        self.assertEqual(len(row['attempts']),10)
        self.assertTrue(all(a['status']=='ok' for a in row['attempts']))
        self.assertNotIn('covariance',row['arms']['L-diag']['full']['block_diagnostics'][0])
        self.assertNotIn('states',row['arms']['L-diag']['full'])
        json.dumps(row,allow_nan=False)
        # Exercise the actual producer/consumer boundary, not a second fixture schema.
        spec=importlib.util.spec_from_file_location('__cohort_consumer_test',Path(__file__).with_name('aggregate_gram_cohort.py'))
        aggregate=importlib.util.module_from_spec(spec);spec.loader.exec_module(aggregate)
        aggregate.validate([row],{g.KEY:self.three[g.KEY]},{g.KEY:self.run2[g.KEY]})

    def test_failed_attempt_is_retained_and_stops_remaining_calls(self):
        self.fail_at=2
        row=self.process()
        self.assertEqual(row['status'],'error')
        self.assertEqual((row['receiver_calls'],row['decoder_calls']),(2,1))
        self.assertEqual(row['attempts'][-1]['status'],'error')
        self.assertIsNotNone(row['attempts'][-1]['detect_seconds'])
        self.assertIn('fixture receiver failure',row['error'])
        json.dumps(row,allow_nan=False)

    def test_baseline_score_and_state_rejection(self):
        row=self.process()
        score=row['arms']['L-diag']['point']
        saved=self.three[g.KEY]['three_mode']['L-diag']['modes']['point']
        for field,value in (('decoded_sha256','wrong'),('extrinsic_bit_logloss',.5),('final_gains',[[2.,0.]])):
            corrupted=copy.deepcopy(score);corrupted[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):g.validate_baseline(corrupted,saved)
        corrupted=copy.deepcopy(score);corrupted['nmse_final']=float('nan')
        with self.assertRaises(ValueError):g.validate_score(corrupted)
        det=self.ctx.native.scalar_joint(None,None,NS(p=1,gains=np.ones(1)),.2,gain_mode='point')
        det['states'][0]['vh']=.1
        with self.assertRaises(ValueError):g.validate_detection(det,'point',NS(gains=np.ones(1)),.2)


if __name__=='__main__':unittest.main()
