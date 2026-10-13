"""Independent small-matrix checks against explicit AFDM atoms and dense C."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import gamma_crossfit_v1 as gamma
import physical_transfer_model_v1 as physical


def dense_atoms(operator):
    n=operator['n']; d=len(operator['delays'])
    basis=np.zeros((d,n,n),np.complex128)
    for j in range(d):
        for i in range(n):
            basis[j,operator['rows'][i,j],i]=operator['phase'][i,j]
    return basis


def dense_score(y,mean,Z,sigma2):
    covariance=sigma2*np.eye(len(y),dtype=np.complex128)+Z@Z.conj().T
    sign,logdet=np.linalg.slogdet(covariance)
    assert np.isclose(sign,1.)
    residual=y-mean
    return float(np.vdot(residual,np.linalg.solve(covariance,residual)).real),float(logdet)


class IndependentGammaAlgebra(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(20260915)
        n,lmax,w=13,2,1
        c1=(2*w+1)/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
        self.operator=gamma.layout(n,lmax,w,c1,c2)
        self.basis=dense_atoms(self.operator)

    def complex_vector(self,size):
        return self.rng.normal(size=size)+1j*self.rng.normal(size=size)

    def test_projection_and_gain_embedding_match_explicit_atoms(self):
        op=self.operator; n=op['n'];d=len(op['delays'])
        c1=(2*op['w']+1)/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
        for j in (0,3,7):
            cpp=physical.cpp_channel_matrix(n,c1,c2,
                np.array([op['delays'][j]]),np.array([op['dopplers'][j]]),
                np.array([1.+0j]),prefix_length=3)
            np.testing.assert_allclose(self.basis[j],cpp,atol=4e-14,rtol=0)
        truth=self.complex_vector(d)
        H=np.einsum('j,jmn->mn',truth,self.basis)
        # Outside all represented offsets: projection must ignore this tail.
        tail=np.zeros_like(H);tail[9,0]=.3-.2j;H+=tail
        projected,info=gamma.project_full(H,op)
        np.testing.assert_allclose(projected,truth,atol=3e-15)
        self.assertAlmostEqual(info['tail_frobenius_squared'],abs(tail[9,0])**2,places=11)
        ids=np.array([0,3,7]);gains=self.complex_vector(3)
        x=self.complex_vector(n)
        A=np.stack([self.basis[j]@x for j in ids],axis=1)
        state=dict(support_delays=op['delays'][ids],
                   support_dopplers=op['dopplers'][ids],g_solution=gains,A=A)
        embedded,metadata=gamma.embed_gain(state,op)
        np.testing.assert_allclose(embedded[ids],gains)
        self.assertEqual(metadata['atom_ids'],ids.tolist())

    def test_candidate_update_and_woodbury_against_dense_covariance(self):
        op=self.operator;n=op['n'];d=len(op['delays'])
        pilot=self.complex_vector(n);mu=.3*self.complex_vector(n)
        m=self.complex_vector(d);U=.1*self.complex_vector((d,15))
        # Force centered training-like factor: its 15 columns sum to zero.
        U-=U.mean(axis=1,keepdims=True)
        y=self.complex_vector(n);sigma2=.07;index=3
        D=lambda x: np.stack([atom@x for atom in self.basis],axis=1)
        mean0,Z0=gamma.baseline_action(pilot+mu,op,m,U)
        np.testing.assert_allclose(mean0,D(pilot+mu)@m,atol=3e-14)
        np.testing.assert_allclose(Z0,D(pilot+mu)@U,atol=3e-14)
        L0,logdet0=gamma.factor_covariance(Z0,sigma2)
        dense0=dense_score(y,mean0,Z0,sigma2)
        self.assertAlmostEqual(logdet0,dense0[1],places=10)
        self.assertAlmostEqual(gamma.quadratic_from_factor(y,mean0,Z0,sigma2,L0),dense0[0],places=10)
        pair=gamma.candidate_pair(y,pilot,mu,m,U,op,sigma2,index,
                                  baseline=(mean0,Z0,L0,logdet0))
        vals={}
        for sign in (1,-1):
            imag=.5 if mu[index].imag>=0 else -.5
            candidate=sign*.5+1j*imag
            x=pilot+mu.copy();x[index]+=candidate-mu[index]
            direct_mean,direct_Z=D(x)@m,D(x)@U
            updated_mean,updated_Z=gamma.updated_action(mean0,Z0,op,m,U,index,candidate-mu[index])
            np.testing.assert_allclose(updated_mean,direct_mean,atol=3e-14)
            np.testing.assert_allclose(updated_Z,direct_Z,atol=3e-14)
            vals[sign]=dense_score(y,direct_mean,direct_Z,sigma2)
        direct_delta=sum(vals[1])-sum(vals[-1])
        self.assertAlmostEqual(pair['delta_total_NLL'],direct_delta,places=9)
        self.assertAlmostEqual(pair['delta_frozen_covariance_mean']+
                               pair['delta_inverse_covariance_change']+
                               pair['delta_logdet_change'],direct_delta,places=9)
        self.assertEqual(pair['score_calls']['candidate_C'],2)
        self.assertEqual(pair['score_calls']['frozen_C_mu'],0)

    def test_crossfit_factor_uses_conjugate_covariance_and_excludes_target(self):
        d=len(self.operator['delays'])
        errors={b:self.complex_vector(d) for b in range(1,16)}
        result=gamma.fold(errors,0)
        self.assertEqual(result['channels'],tuple(range(1,16)))
        self.assertLessEqual(result['rank'],14)
        reference=np.cov(np.stack(list(errors.values())),rowvar=False,ddof=1)
        np.testing.assert_allclose(result['U']@result['U'].conj().T,
                                   reference,atol=3e-14)
        with self.assertRaises(ValueError):
            gamma.fold({**errors,0:self.complex_vector(d)},0)


if __name__=='__main__': unittest.main()
