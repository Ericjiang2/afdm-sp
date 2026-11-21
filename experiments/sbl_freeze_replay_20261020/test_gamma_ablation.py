"""Synthetic matrix and stub orchestration contracts; no real receiver calls."""
import copy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np
import gamma_ablation as g
import test_gram_cohort as old_test

block = g.module('__gamma_test_block', 'gram_block.py')


class GammaMatrixTest(unittest.TestCase):
    def test_only_gamma_offdiagonals_removed_and_full_data_gram_retained(self):
        B = np.array([[1.,1.],[1.,2.],[2.,1.]], complex)
        Y = np.array([1.,2.,4.], complex)
        Gamma = np.array([[3.,.5j],[-.5j,3.]])
        physical = NS(projected_variance=lambda:Gamma, daft=lambda x:x)
        facade = g.DiagonalGamma(physical)
        self.assertIs(facade.daft(Y),Y)
        actual, detail = block.solve_gain(B,Y,facade.projected_variance(),.1,'full')
        reference = B.conj().T@B+np.diag(np.diag(Gamma))+.2*np.eye(2)
        np.testing.assert_array_equal(detail['Q'],reference)
        self.assertEqual(detail['Q'][0,1],(B.conj().T@B)[0,1])
        self.assertNotEqual(detail['Q'][0,1],0)
        _, original = block.solve_gain(B,Y,Gamma,.1,'full')
        np.testing.assert_allclose(original['Q']-detail['Q'],Gamma-np.diag(np.diag(Gamma)))
        np.testing.assert_allclose(actual,np.linalg.solve(reference,B.conj().T@Y))
        for diagonal in (np.zeros((2,2)),np.diag([2.,3.])):
            physical.projected_variance=lambda:diagonal
            full,_=block.solve_gain(B,Y,diagonal,.1,'full')
            reduced,_=block.solve_gain(B,Y,facade.projected_variance(),.1,'full')
            np.testing.assert_array_equal(full,reduced)

    def test_invalid_original_gamma_cannot_be_hidden(self):
        for gamma in (np.array([[1.,2.],[0.,1.]]),np.array([[1.,np.nan],[np.nan,1.]]),
                      np.array([[1.,2.],[2.,1.]])):
            with self.assertRaises(ValueError):
                g.DiagonalGamma(NS(projected_variance=lambda:gamma)).projected_variance()
        for gamma in (np.full((2,2),np.nan),np.array([[1.,2.],[0.,1.]])):
            with self.assertRaises(ValueError): block.solve_gain(np.eye(2),np.ones(2),gamma,.1,'full')


class GammaProcessTest(unittest.TestCase):
    def setUp(self):
        self.fixture=old_test.GramCohortTest(); self.fixture.setUp(); f=self.fixture
        self.full=f.process(); self.assertEqual(self.full['status'],'ok')
        f.calls=f.decode_calls=0

    def process(self,gate=False):
        f=self.fixture
        return g.process_key(f.ctx,f.helper,f.block,None,None,f.meta,f.obs,np.zeros(2),f.truth,
            f.three[g.cohort.KEY],f.run2[g.cohort.KEY],self.full,gate=gate)

    def test_main_gate_counts_and_producer_consumer_contract(self):
        agg=g.module('__gamma_consumer_test','aggregate_gamma_ablation.py');f=self.fixture;k=g.cohort.KEY
        for gate,receivers,decoders in ((False,2,2),(True,6,4)):
            f.calls=f.decode_calls=0
            row=self.process(gate)
            self.assertEqual(row['status'],'ok',row.get('error'))
            self.assertEqual((f.calls,f.decode_calls),(receivers,decoders))
            agg.validate([row],{k:f.three[k]},{k:f.run2[k]},{k:self.full},gate=gate)
            self.assertEqual(set(row['arms']['L-diag']),{'full','gamma_diag'} if gate else {'gamma_diag'})
            changed=copy.deepcopy(row);changed['arms']['L-diag']['gamma_diag']['trace'][0]['gain_variance']=.1
            with self.assertRaises(ValueError): agg.validate([changed],{k:f.three[k]},{k:f.run2[k]},{k:self.full},gate=gate)

    def test_fail_closed_on_observation_or_decoder_drift_and_retain_attempt(self):
        f=self.fixture;self.full['observation_sha256']['y']='corrupted'
        row=self.process(); self.assertEqual(row['status'],'error');self.assertEqual(f.calls,0)
        self.full['observation_sha256']['y']=f.helper.aggregate.array_sha(f.obs['y'])
        f.fail_at=2
        row=self.process();self.assertEqual(row['status'],'error')
        self.assertEqual((row['receiver_calls'],row['decoder_calls']),(2,1))
        self.assertEqual(row['attempts'][-1]['status'],'error')
        self.assertIn('fixture receiver failure',row['error'])
        f.fail_at=None;f.calls=0
        self.full['arms']['L-diag']['full']['decoded_sha256']='changed'
        row=self.process(gate=True);self.assertEqual(row['status'],'error')
        self.assertIn('full replay drift',row['error'])


if __name__=='__main__': unittest.main()
