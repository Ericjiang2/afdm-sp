import unittest
import numpy as np
import torch

from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics
from afdm_sp_joint_unrolled.test_projected_gls import independent_objective
from afdm_sp_joint_unrolled.v3_statistics import residual_decomposition


class StatisticsTests(unittest.TestCase):
    def test_strict_well_conditioned_decrease_and_residual_closure(self):
        rng=np.random.default_rng(772)
        for dtype,tol in ((np.complex128,1e-10),(np.complex64,1e-4)):
            z=lambda shape:(rng.normal(size=shape)+1j*rng.normal(size=shape)).astype(dtype)
            y=z(12);A=z((12,7));M=z((12,12));C=M@M.conj().T+12*np.eye(12,dtype=dtype)
            for support in ([],[0,1]):
                result=projected_add_statistics(*[torch.from_numpy(v) for v in (y,A,C)],support,[3])
                before=independent_objective(y.astype(complex),A.astype(complex),C.astype(complex),support)
                after=independent_objective(y.astype(complex),A.astype(complex),C.astype(complex),support+[3])
                self.assertLessEqual(abs(float(result['candidates'][0]['D'])-(before-after))/abs(before-after),tol)
            H=z((12,12));Hhat=H+.1*z((12,12));pilot=z(12);data=z(12);mean=data+.2*z(12)
            observation=H@(pilot+data)+.1*z(12)
            d=residual_decomposition(observation,H,Hhat,pilot,data,mean)
            self.assertLessEqual(d['relative_vector_closure'],tol)
            self.assertLessEqual(abs(d['energy_closure'])/max(d['residual_mean_square'],1),tol)

    def test_same_observation_feedback_can_cancel_noise_exactly(self):
        H=np.eye(4,dtype=complex);data=np.ones(4,dtype=complex);pilot=data*.5
        noise=np.arange(4)*(1+1j)*.1
        result=residual_decomposition(H@(pilot+data)+noise,H,H,pilot,data,data+noise)
        self.assertAlmostEqual(result['residual_mean_square'],0.)
        self.assertGreater(result['component_mean_squares']['noise'],0.)
        self.assertLess(result['cross_terms']['data:noise'],0.)


if __name__=='__main__':unittest.main()
