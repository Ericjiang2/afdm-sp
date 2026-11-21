"""Stub pipeline contracts; these tests never fit SBL or run a real receiver."""
import copy
from types import SimpleNamespace as NS
import unittest
import numpy as np
import fresh_cohort as f
import test_gram_cohort as old_test


def fixture():
    old=old_test.GramCohortTest();old.setUp()
    helper,ctx=old.helper,old.ctx
    oldd=helper.replay.oldd
    oldd.sha=old_test.digest;oldd.bit_loss=lambda llr,coded:.2
    helper.e3d.gd=NS(score=lambda *args:0,bits_sha=lambda value:old_test.digest(np.asarray(value,np.uint8)))
    helper.e3d.crb=NS(channel_nmse=lambda *args:.1)
    helper.e3d.truth_paths=lambda t:{}
    helper.e3d.p1ctx=NS(p1_driver=NS(pair_fingerprint=lambda truth:(123,'gains','info','noise')))
    ctx.native.decoder_messages=lambda code,llr,maxiter:dict(decoded=np.zeros(4,np.uint8),iterations=2,
        raw_check_extrinsic=np.array([.1,-.2,.3,-.4]),raw_app=np.zeros(4))
    ctx.native.scalar_joint_orig=ctx.native.scalar_joint
    calls=[]
    def scalar(*args,**kw):
        calls.append(dict(mode=kw['gain_mode'],prior=None if kw['prior'] is None else kw['prior'].copy()))
        return ctx.native.scalar_joint_orig(*args,**kw)
    ctx.native.scalar_joint=scalar
    helper.e3d.sbl=NS(MAX_ITER=100)
    helper.e3d.sbl.sbl_em=lambda B,Y,**kw:dict(mu=np.ones(1,complex),gamma=np.ones(1),iterations=100,converged=False,
        n_start=1,n_final=1,beta=1.,jitter_events=0)
    def original(c,obs,ch,prior):
        det=c.native.scalar_joint(obs['y'],obs['pilot'],ch,obs['sigma2'],prior=prior,gain_mode='fixed')
        dec=c.native.decoder_messages(c.code,det['extrinsic'],maxiter=50)
        return det,dec,.01,.02
    helper.e3d.detect_decode=original
    def pipeline(c,cache,grid,obs,data,truth,meta,variants,max_iter):
        fits=[]
        fit=helper.e3d.sbl.sbl_em(np.ones((2,1)),np.ones(2),beta0=1.,Gamma=None)
        channel=NS(n=2,p=1,gains=np.array([1.+0j]),delays=np.array([1]),dopplers=np.array([.25]))
        _,dec,_,_=helper.e3d.detect_decode(c,obs,channel,None)
        prior=np.clip(dec['raw_check_extrinsic'],-20,20)
        result=dict(meta,sigma2=obs['sigma2'],round1=dict(info_errors=0,decoded_sha256=helper.e3d.gd.bits_sha(dec['decoded']),ldpc_iters=2,syndrome=0),
            stage1=dict(n_candidates=1,iterations=100,converged=False,n_final=1,beta=1.,jitter_events=0,atoms=[[1,.25,1.]],nmse=.1),
            variants={},seconds=dict(stage1_screen=.01,stage1_sbl=.1,round1_detect=.01,round1_decode=.02,stage2_screen=.02,total=.5))
        for name in variants:
            helper.e3d.sbl.sbl_em(np.ones((2,1)),np.ones(2),beta0=1.,Gamma=1. if name=='L-diag' else np.eye(1),max_iter=max_iter)
            det,dec,td,tc=helper.e3d.detect_decode(c,obs,channel,prior)
            result['variants'][name]=dict(n_atoms=1,atoms=[[1,.25,1.]],sbl=dict(max_iter=100,iterations=100,converged=False,jitter_events=0),
                decoded_sha256=helper.e3d.gd.bits_sha(dec['decoded']),info_errors=0,fer=0,ldpc_iters=2,seconds=dict(sbl=.1,detect=td,decode=tc))
        return result
    helper.e3d.process_key=pipeline
    meta=dict(scenario='U',rho_permille=300,snr_centi_db=700,frame=2000000)
    obs=old.obs;truth=old.truth
    generation=dict(scenario='U',frame=meta['frame'],seconds=.01,info_sha256='info',coded_sha256=helper.e3d.gd.bits_sha(truth['coded']),noise_sha256='noise',channel_seed=123)
    return old,helper,ctx,calls,meta,obs,truth,generation


def process(parts,meta=None):
    old,helper,ctx,calls,m,obs,truth,gen=parts
    m=m if meta is None else meta
    gen=dict(gen,scenario=m['scenario'],frame=m['frame'])
    # The immutable block is a stub here; no physical receiver execution.
    return f.process_key(ctx,helper,old.block,None,None,None,None,m,obs,np.zeros(2),truth,gen)


class FreshProcessTest(unittest.TestCase):
    def test_exact_three_arms_counts_shared_prior_and_scoring_without_redecode(self):
        parts=fixture();row=process(parts)
        self.assertEqual(row['status'],'ok',row.get('error'))
        self.assertEqual((row['sbl_calls'],row['receiver_calls'],row['decoder_calls']),(3,4,4))
        self.assertEqual(set(row['arms']),set(f.ARMS))
        self.assertEqual(row['pipeline']['variants']['L-diag']['pipeline_return_mode'],'full')
        self.assertEqual(row['pipeline']['variants']['L-cov']['pipeline_return_mode'],'joint')
        self.assertEqual([x['mode'] for x in parts[3]],['fixed','joint'])
        np.testing.assert_array_equal(parts[3][1]['prior'],row['round1_receipt']['check_prior'])
        agg=f.module('__fresh_test_consumer','aggregate_fresh_cohort.py')
        agg.validate([row],expected={f.gamma.oldagg.key(row)})
        # Patches are scoped: genuine outer functions are restored after a key.
        self.assertEqual(parts[1].e3d.detect_decode.__name__,'original')

    def test_balanced_order_and_no_extra_native_weak_mode(self):
        for sc in ('U','G'):
            for snr in (700,800):
                orders=[f.cov_order(dict(scenario=sc,snr_centi_db=snr,frame=frame)) for frame in f.FRAMES]
                self.assertEqual(orders.count(('full','joint')),25)
                self.assertEqual(orders.count(('joint','full')),25)
        row=process(fixture(),dict(scenario='U',rho_permille=300,snr_centi_db=700,frame=2000001))
        self.assertEqual([x.get('mode') for x in row['attempts'][1:]],['full','joint','full'])

    def test_old_gate_checks_upstream_prior_and_terminal_outcomes(self):
        row=process(fixture(),dict(scenario='U',rho_permille=300,snr_centi_db=700,frame=9100))
        prior=np.asarray(row['round1_receipt']['check_prior']);h0=row['upstream']['L-diag']['h0']
        old=dict(prior=prior.tolist(),h0=h0,h20=h0,support=row['upstream']['L-diag']['support'],
            input_sha256=dict(prior=old_test.digest(prior),h0=old_test.digest(np.array([1.+0j])),h20=old_test.digest(np.array([1.+0j]))))
        three=dict(round1=row['pipeline']['round1'],three_mode=copy.deepcopy(row['upstream']))
        joint=row['arms'][f.CONTROL]
        three['three_mode']['L-cov']['modes']={'joint':dict(
            **{k:joint[k] for k in ('decoded_sha256','info_errors','fer','ldpc_iters','extrinsic_bit_logloss')},
            trajectory=[dict(h=joint['final_gains'],channel_nmse=joint['nmse_final'],data_mse=joint['data_mse_final'],symbol_variance=joint['symbol_variance_final'])])}
        full=dict(observation_sha256={k:row['input_sha256'][k] for k in ('y','pilot')},
            arms={v:{'full':row['arms'][v+'/full']} for v in f.V})
        self.assertTrue(f.validate_gate(row,three,old,full))
        changed=copy.deepcopy(row);changed['upstream']['L-cov']['h0'][0][0]+=.1
        with self.assertRaises(AssertionError): f.validate_gate(changed,three,old,full)
        changed=copy.deepcopy(row);changed['arms']['L-diag/full']['decoded_sha256']='changed'
        with self.assertRaises(AssertionError): f.validate_gate(changed,three,old,full)

    def test_sbl_failure_retained_and_downstream_not_executed(self):
        parts=fixture()
        def fail(*args,**kwargs):raise RuntimeError('synthetic SBL failure')
        parts[1].e3d.sbl.sbl_em=fail
        row=process(parts)
        self.assertEqual(row['status'],'error')
        self.assertEqual((row['sbl_calls'],row['receiver_calls'],row['decoder_calls']),(1,0,0))
        self.assertEqual(row['sbl_fits'][0]['status'],'error')
        self.assertIn('synthetic SBL failure',row['error'])

    def test_changed_check_prior_rejected_before_terminal_call(self):
        parts=fixture();original=parts[1].e3d.process_key
        def corrupt(*args,**kw):
            active=parts[1].e3d.detect_decode
            def wrapped(c,obs,ch,prior):
                return active(c,obs,ch,None if prior is None else prior+1)
            parts[1].e3d.detect_decode=wrapped
            return original(*args,**kw)
        parts[1].e3d.process_key=corrupt
        row=process(parts)
        self.assertEqual(row['status'],'error')
        self.assertEqual((row['sbl_calls'],row['receiver_calls'],row['decoder_calls']),(2,1,1))
        self.assertIn('stage2 prior changed',row['error'])


if __name__=='__main__':unittest.main()
