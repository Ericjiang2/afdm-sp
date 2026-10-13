import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import logsumexp

from experiments.afdm_shared_channel_20261004 import common
from experiments.afdm_shared_channel_20261004.probability import (
    outside_cavity, exact_scores, conditional_scores, mm_scores, normalized,
    block_extrinsic, fourth_checks, log_bit_prior, PHYSICAL, dense_operators)
from experiments.afdm_shared_channel_20261004.quadrature import gaussian_nodes, sphere_nodes
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior


class ProbabilityContracts(unittest.TestCase):
    def setUp(self):
        self.n = 2
        self.ops = dense_operators(PHYSICAL.Channel(2,.17,.03,[0,1],[.2,-.3],[1,1]))
        self.pilot = np.array([.3+.1j,-.2+.4j])
        self.y = np.array([.7-.3j,.1+.4j])
        self.incoming = np.array([.7,-.6,.2,.8])
        self.noise = .7

    def test_analytic_block_equals_independent_global_enumeration(self):
        words,bits = enumerate_qpsk(2)
        posterior = exact_posterior(self.y,self.ops,self.pilot,words,[0,0],np.eye(2)/2,self.noise)
        for block in ([0],[0,1]):
            score,local,local_bits = exact_scores(self.y,self.ops,self.pilot,block,self.incoming,self.noise,mean=[0,0],covariance=np.eye(2)/2)
            outside = np.setdiff1d(np.arange(2),block)
            weights = log_bit_prior(bits[:,np.r_[outside,outside+2]],self.incoming[np.r_[outside,outside+2]])
            expected = []
            for word in local:
                mask = np.all(words[:,block]==word,axis=1)
                expected.append(logsumexp(posterior.log_likelihood[mask]+weights[mask]))
            np.testing.assert_allclose(score,expected,atol=1e-13)
            self.assertAlmostEqual(normalized(score,local_bits)['probability'].sum(),1.)

    def test_known_h_mixture_equals_mm_including_improper_cavity(self):
        h = np.array([.7+.2j,-.3+.1j])
        local,_ = enumerate_qpsk(1)
        _,m,v = outside_cavity(2,[0],self.incoming)
        self.assertNotEqual(v[1,1],v[3,3])
        mix = conditional_scores(self.y,self.ops,self.pilot,local,m,v,[0],self.noise,h[None,:],np.ones(1))
        mm = mm_scores(self.y,self.ops,self.pilot,local,m,v,[0],self.noise,h,np.zeros((2,2)))
        np.testing.assert_allclose(mix,mm,atol=1e-12)

    def test_no_outside_gaussian_gain_has_analytic_base(self):
        local,_ = enumerate_qpsk(2)
        ops = self.ops[:1]
        score,_,_ = exact_scores(self.y,ops,self.pilot,[0,1],self.incoming,1.5,mean=[0],covariance=[[1]])
        _,m,v = outside_cavity(2,[0,1],self.incoming)
        mm = mm_scores(self.y,ops,self.pilot,local,m,v,[0,1],1.5,np.zeros(1),np.eye(1))
        nodes,weights = gaussian_nodes([0],[[1]],25)
        mix = conditional_scores(self.y,ops,self.pilot,local,m,v,[0,1],1.5,nodes,weights)
        np.testing.assert_allclose(score,mm,atol=1e-12)
        np.testing.assert_allclose(score,mix,atol=3e-7)

    def test_known_h_no_outside_all_three_equal_direct_density(self):
        h = np.array([.4+.3j,-.2+.1j]); block=[0,1]
        scores,words,_ = exact_scores(self.y,self.ops,self.pilot,block,self.incoming,self.noise,mean=h,covariance=np.zeros((2,2)))
        response = np.einsum('p,pij,kj->ki',h,self.ops,self.pilot+words)
        expected = -2*np.log(np.pi*self.noise)-np.sum(abs(self.y-response)**2,axis=1)/self.noise
        np.testing.assert_allclose(scores,expected,atol=1e-12)

    def test_target_own_factor_excluded_from_global_and_bit_messages(self):
        block=[0,1]
        score,_,bits = exact_scores(self.y,self.ops,self.pilot,block,self.incoming,self.noise,mean=[0,0],covariance=np.eye(2)/2)
        original = block_extrinsic(score,bits,self.incoming)
        for j in range(4):
            changed=self.incoming.copy(); changed[j]+=9
            changed_score,_,_ = exact_scores(self.y,self.ops,self.pilot,block,changed,self.noise,mean=[0,0],covariance=np.eye(2)/2)
            np.testing.assert_array_equal(score,changed_score)
            self.assertEqual(original[j],block_extrinsic(changed_score,bits,changed)[j])
        # An outside factor is a legal input and must actually influence the message.
        base,_,_ = exact_scores(self.y,self.ops,self.pilot,[0],self.incoming,self.noise,mean=[0,0],covariance=np.eye(2)/2)
        changed=self.incoming.copy(); changed[1]+=4
        other,_,_ = exact_scores(self.y,self.ops,self.pilot,[0],changed,self.noise,mean=[0,0],covariance=np.eye(2)/2)
        self.assertGreater(np.max(abs(base-other)),.01)

    def test_fourth_moments_and_normalized_counterexamples(self):
        rows=fourth_checks()
        self.assertLess(max(r['quadrature_error'] for r in rows),1e-10)
        self.assertTrue(all(r['difference']>=-1e-12 for r in rows if r['prior']=='Gaussian'))
        self.assertTrue(any(r['difference']<-.01 for r in rows if r['prior']=='normalized'))
        r=next(r for r in rows if r['prior']=='normalized' and r['p']==1 and r['kind']=='random_scale')
        self.assertAlmostEqual(r['difference'],0.)

    def test_covariance_matches_full_qpsk_second_moment(self):
        # Independent quadrature of gain/data second moments checks the covariance object.
        nodes,weights=sphere_nodes(2,1.,5)
        words,bits=enumerate_qpsk(2)
        word=words[0,:1]; mask=words[:,0]==word[0]
        selected=words[mask]
        cavity_weights=np.exp(log_bit_prior(bits[mask][:,[1,3]],self.incoming[[1,3]]))
        responses=np.einsum('tp,pij,kj->tki',nodes,self.ops,self.pilot+selected)
        second=np.einsum('t,k,tki,tkj->ij',weights,cavity_weights,responses,responses.conj())
        _,m,v=outside_cavity(2,[0],self.incoming)
        x=self.pilot+m; x[0]+=word[0]
        b=np.einsum('pij,j->ip',self.ops,x)
        co=v[:2,:2]+v[2:,2:]
        expected=b@b.conj().T/2+sum(op@co@op.conj().T for op in self.ops)/2
        np.testing.assert_allclose(second,expected,atol=1e-12)


class RunnerContracts(unittest.TestCase):
    def test_registration_precedes_work_and_failure_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'run_contract.json').write_text(json.dumps(dict(output_limit_bytes=1000000)))
            def fail(output):
                record=json.loads((output/'registration.json').read_text())
                self.assertEqual(record['_config']['seed'],[1])
                self.assertIn('deadline_utc',record)
                raise RuntimeError('deliberate contract failure')
            with patch.object(common,'ARTIFACT',root):
                with self.assertRaisesRegex(RuntimeError,'deliberate'):
                    common.run('fixture',dict(seed=[1]),[],fail,wall_seconds=10)
                attempt=json.loads((root/'execution/fixture/attempt.json').read_text())
                self.assertEqual(attempt['status'],'invalid_partial')
                with self.assertRaises(FileExistsError):
                    common.run('fixture',dict(seed=[1]),[],fail)


if __name__=='__main__': unittest.main()
