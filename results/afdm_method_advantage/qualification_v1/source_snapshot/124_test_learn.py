"""Learning contracts; no held-out model selection or hidden probability repair."""
import unittest

import numpy as np
import torch


class LearningTests(unittest.TestCase):
    def test_registered_capacity_and_derivative_units(self):
        from experiments.afdm_structured_inference_20261003.learn import SharedPotential,IndependentHeads,predict,V
        torch.manual_seed(7);model=SharedPotential();x=torch.randn(3,33,dtype=torch.float64)*.2
        self.assertEqual(sum(p.numel() for p in model.parameters()),1121)
        self.assertEqual(sum(p.numel() for p in IndependentHeads().parameters()),1116)
        mean,response,cov=predict(model,x,covariance=True)
        eps=2e-5;direction=torch.zeros_like(x);direction[:,:4]=torch.as_tensor(V)/4
        plus=predict(model,x+eps*direction)[0].detach().numpy()
        minus=predict(model,x-eps*direction)[0].detach().numpy()
        np.testing.assert_allclose((plus-minus)/(2*eps),response.detach().numpy(),rtol=1e-7,atol=1e-10)
        self.assertGreaterEqual(np.linalg.eigvalsh(cov.detach().numpy()).min(),-1e-12)
        self.assertEqual(mean.shape,(3,8))

    def test_backward_through_mixed_derivative(self):
        from experiments.afdm_structured_inference_20261003.learn import SharedPotential,predict
        torch.manual_seed(8);model=SharedPotential();x=torch.randn(4,33,dtype=torch.float64)
        m,r,_=predict(model,x,training=True);loss=((m-.1)**2).mean()+((r-.03)**2).mean();loss.backward()
        self.assertTrue(torch.isfinite(model.hidden.weight.grad).all())
        self.assertGreater(float(model.hidden.weight.grad.norm()),0)

    def test_meanfield_legal_prior_limit_and_response(self):
        from experiments.afdm_structured_inference_20261003.learn import meanfield_prediction
        xi=np.linspace(-.3,.7,8)[None,:];b=np.linspace(.5,1.2,8)[None,:];d=np.linspace(-.1,.4,8)[None,:]
        m,r=meanfield_prediction(xi,b,d,0.)
        np.testing.assert_allclose(m,.5*np.tanh(xi/2));np.testing.assert_array_equal(r,0)
        alpha=.6;eps=2e-5;m,r=meanfield_prediction(xi,b,d,alpha)
        plus=meanfield_prediction(xi,b+eps*d,d,alpha)[0]
        minus=meanfield_prediction(xi,b-eps*d,d,alpha)[0]
        np.testing.assert_allclose((plus-minus)/(2*eps),r,atol=1e-10)
        self.assertTrue(np.all(abs(m)<.5))

    def test_transform_preserves_physics_and_teacher_probability(self):
        from experiments.afdm_structured_inference_20261003.learn import transform_case
        from experiments.afdm_structured_inference_20261003.potential import make_bilinear_case,finite_potential
        case=make_bilinear_case('general',center=.83,stride=5.3);xi=np.linspace(-.2,.3,8);eta=np.linspace(-.5,.4,4)
        old=finite_potential(case['z'],case['f'],case['log_prior'],eta,xi,.7)
        for kind in ['path_permutation','joint_phase']:
            changed,source=transform_case(case,xi,kind)
            new=finite_potential(changed['z'],changed['f'],changed['log_prior'],eta,source,.7)
            np.testing.assert_allclose(changed['f'],case['f'],atol=1e-14)
            np.testing.assert_allclose(changed['z']@source,case['z']@xi,atol=1e-14)
            np.testing.assert_allclose(new['probabilities'],old['probabilities'],atol=1e-14)

    def test_invalid_probability_invalidates_whole_cohort(self):
        from experiments.afdm_structured_inference_20261003.learn import score_cohort
        from experiments.afdm_structured_inference_20261003.potential import make_bilinear_case
        states=make_bilinear_case()['z'];means=np.zeros((2,8));response=np.zeros_like(means)
        probability=np.full((2,len(states)),1/len(states));support=np.stack([states,states])
        _,proper=score_cohort(means,response,means,response,probability,support)
        self.assertIsNotNone(proper)
        bad=means.copy();bad[0,2]=.6
        metrics,proper=score_cohort(bad,response,means,response,probability,support)
        self.assertIsNone(proper)
        np.testing.assert_array_equal(metrics['support_invalid'],[1.,0.])


if __name__=='__main__':
    unittest.main()
