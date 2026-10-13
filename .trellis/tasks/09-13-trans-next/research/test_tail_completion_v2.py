import importlib.util
import pathlib
import sys
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
CE_SOURCE = REPO/'afdm_sp_joint_unrolled/outputs_ce_state_20260915/source-v4'
sys.path.insert(0,str(CE_SOURCE if CE_SOURCE.exists() else REPO))
SPEC = importlib.util.spec_from_file_location('tail_completion_v2', HERE/'tail_completion_v2.py')
tail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tail)


class TailCompletionContractTests(unittest.TestCase):
    def test_production_cpp_daFT_bin_sign_and_delay_phase(self):
        from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
        from afdm_sp_joint_unrolled.supplement_pilots import propagate_cpp, transform
        n, l, centre, kappa = 31, 3, 1, .3
        c1, c2 = tail.STRIDE/(2*n), 1.9751241797117955e-7
        H = physical_channel_matrix(n,c1,c2,[l],[centre+kappa],[1+0j],prefix_length=7)
        rng=np.random.default_rng(202609150701)
        x=rng.normal(size=n)+1j*rng.normal(size=n)
        direct=transform(propagate_cpp(transform(x,c1,c2,inverse=True),c1,[l],
                                        [centre+kappa],[1+0j],prefix_length=7),c1,c2)
        np.testing.assert_allclose(H@x,direct,rtol=1e-12,atol=1e-12)
        atoms=tuple((l,k) for k in (centre-1,centre,centre+1))
        projected=tail.direct_projection(H,n,c1,c2,atoms)
        r=np.array([-1,0,1])
        fft=np.fft.fft(np.exp(2j*np.pi*kappa*np.arange(n)/n))/n
        np.testing.assert_allclose(projected,fft[r%n],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(tail.positive_fft_coefficient(n,r,np.array([kappa]))[0],
                                   projected,rtol=1e-12,atol=1e-12)
        # Explicitly catch centre±1 sign reversal: these complex values differ.
        self.assertGreater(abs(projected[0]-projected[2]),.1)
        rebuilt=tail.atom_action(n,c1,c2,atoms,projected,x)
        self.assertLess(np.linalg.norm(rebuilt-H@x)/np.linalg.norm(H@x),.65)

    def test_selected_S24_tail_disjoint_and_mixed_oracle_fallback(self):
        delays=np.array([3]*4+[4]*3+[10]*3+[11]*3+[12]*3+[13]*3+[14]*3+[15]*2)
        dopplers=np.array([-1,0,1,2, -2,0,1, -2,-1,0, -1,0,1,
                           -2,0,2, -1,1,2, -2,0,1, -2,2])
        self.assertEqual(len(delays),24)
        S,T=tail.support_and_tail(delays,dopplers,n=31)
        self.assertFalse(set(S)&set(T))
        self.assertTrue(all(l in set(delays) and -5<=k<=5 for l,k in T))
        z=np.ones(24,dtype=complex)
        actual=tail.actual_centres(S,z)
        self.assertEqual(actual[3],-1)
        mixed,counts=tail.mixed_true_centres(S,actual,[3,4,4,10],[1.3,.4,.6,-1.2])
        self.assertEqual(mixed[3],1)
        self.assertEqual(mixed[4],actual[4])  # multi-path fallback, no truth gating
        self.assertEqual(mixed[11],actual[11])  # false delay still completed
        self.assertEqual(counts['unique'],2)
        self.assertEqual(counts['multi'],1)
        self.assertEqual(counts['missing'],5)
        out=tail.completed_tail(S,T,z,actual,n=31)
        self.assertEqual(out.shape,(len(T),))
        self.assertTrue(np.isfinite(out).all())
        np.testing.assert_array_equal(z,np.ones(24))  # original actual S unchanged

    def test_alias_gram_dense_H_risk_and_same_core_baseline(self):
        n,c1,c2=31,tail.STRIDE/(2*31),.0001
        S=((1,5),(2,0))  # same output row shift, distinct delay phase
        T=((1,4),(2,-1))
        rng=np.random.default_rng(1007)
        x=rng.normal(size=n)+1j*rng.normal(size=n)
        from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
        H=physical_channel_matrix(n,c1,c2,[1,2],[1.3,-.4],[1+.2j,.6-.3j],prefix_length=7)
        truth=tail.direct_projection(H,n,c1,c2,S+T)
        expected=tail.physical_fft_coefficients(n,S+T,[1,2],[1.3,-.4],[1+.2j,.6-.3j])
        np.testing.assert_allclose(truth,expected,atol=1e-12,rtol=1e-12)
        # Build dense U through its complete action on each standard basis.
        U=[np.column_stack([tail.atom_action(n,c1,c2,(a,),(1+0j,),np.eye(n)[j])
                             for j in range(n)]) for a in S+T]
        gram=np.array([[np.vdot(u,v)/n for v in U] for u in U])
        np.testing.assert_allclose(gram,np.eye(4),atol=1e-12,rtol=1e-12)
        z=np.array([.7+.1j,.4-.5j])
        zh=np.array([.2-.1j,-.3+.2j])
        scores=tail.score_pair(float(np.vdot(H,H).real),H@x,x,n,c1,c2,S,T,truth,z,zh)
        H0=sum(g*u for g,u in zip(z,U[:2]))
        H1=H0+sum(g*u for g,u in zip(zh,U[2:]))
        self.assertAlmostEqual(scores['H_NMSE_baseline'],np.linalg.norm(H-H0)**2/np.linalg.norm(H)**2,places=12)
        self.assertAlmostEqual(scores['H_NMSE_completed'],np.linalg.norm(H-H1)**2/np.linalg.norm(H)**2,places=12)
        self.assertAlmostEqual(scores['response_NMSE_baseline'],np.linalg.norm((H-H0)@x)**2/np.linalg.norm(H@x)**2,places=12)
        self.assertAlmostEqual(scores['response_NMSE_completed'],np.linalg.norm((H-H1)@x)**2/np.linalg.norm(H@x)**2,places=12)
        self.assertAlmostEqual(scores['H_delta'],scores['H_NMSE_completed']-scores['H_NMSE_baseline'],places=12)


if __name__=='__main__':
    unittest.main()
