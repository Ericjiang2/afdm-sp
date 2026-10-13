"""Real tiny feedback CE and independent augmented least-squares contracts."""
import tempfile
import unittest
import numpy as np
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .test_supplement_feedback_adapter import tiny_adapter


class MomentCETests(unittest.TestCase):
    def setUp(self):
        self.cache=tempfile.TemporaryDirectory();self.addCleanup(self.cache.cleanup)
        self.code=build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=self.cache.name)
        rng=np.random.default_rng(817)
        self.observed=dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
            pilot=np.full(32,.5+0j),sigma2=.2,
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))

    def run_mode(self,mode,strength=1.,**kwargs):
        adapter=tiny_adapter(self.code);adapter.estimator.lstsq_driver='gels'
        return adapter.run(self.observed,audit=True,code_feedback=CodeFeedback(self.code,checkpoint=0),
                           dals_mode=mode,dals_strength=strength,**kwargs)

    def test_delayed_regularization_preserves_prefix_and_consumes_q(self):
        mean=self.run_mode('mean')
        full=self.run_mode('jsoft')
        explicit=self.run_mode('jsoft',dals_start_iteration=1)
        delayed=self.run_mode('jsoft',dals_start_iteration=2)
        for key in ('H','mu','var','llr','decoded','info_hat'):
            np.testing.assert_array_equal(explicit[key],full[key])
        first,last=delayed['dals']
        self.assertEqual(first['mode'],'mean');self.assertNotIn('Q',first)
        for key in ('A','mu','finite_variance','g_previous','g_solution'):
            np.testing.assert_array_equal(first[key],mean['dals'][0][key])
        self.assertEqual(last['mode'],'jsoft')
        self.assertGreater(float(np.trace(last['Q']).real),0.)
        a,y,old=last['A'],last['y'],last['g_previous'];k=a.shape[1]
        q=last['Q'];lam=float(last['regularization'])
        augmented=np.vstack((a,np.linalg.cholesky(q).conj().T,np.sqrt(lam)*np.eye(k)))
        target=np.concatenate((y,np.zeros(k),np.sqrt(lam)*old))
        np.testing.assert_allclose(last['g_solution'],np.linalg.lstsq(augmented,target,rcond=None)[0],atol=1e-10,rtol=1e-10)
        for start in (0,3,True,1.5):
            with self.assertRaises(ValueError):self.run_mode('jsoft',dals_start_iteration=start)
        with self.assertRaises(ValueError):self.run_mode('mean',dals_start_iteration=2)

    def test_actual_feedback_objectives_match_augmented_lstsq(self):
        first=[]
        for mode,strength in [('mean',1.),('jsoft',1.),('zero_ridge',.2),('proximal',.2)]:
            result=self.run_mode(mode,strength);states=result['dals'];self.assertEqual(len(states),2)
            first.append(states[0])
            for s in states:
                a,y,old=s['A'],s['y'],s['g_previous'];k=a.shape[1]
                q=s.get('Q',np.zeros((k,k),dtype=complex));lam=float(s['regularization'])
                eta=strength*float(np.vdot(a,a).real)/k
                if mode=='zero_ridge':np.testing.assert_allclose(q,eta*np.eye(k),atol=1e-12,rtol=1e-12)
                if mode=='proximal':self.assertAlmostEqual(lam,float(s['base_regularization'])+eta,places=12)
                if mode in ('mean','jsoft','zero_ridge'):self.assertEqual(lam,float(s['base_regularization']))
                w,u=np.linalg.eigh(q);self.assertGreaterEqual(float(w.min()),-1e-11)
                root=np.sqrt(np.maximum(0,w))[:,None]*u.conj().T
                augmented=np.vstack((a,root,np.sqrt(lam)*np.eye(k)))
                target=np.concatenate((y,np.zeros(k),np.sqrt(lam)*old))
                expected=np.linalg.lstsq(augmented,target,rcond=None)[0]
                np.testing.assert_allclose(s['g_solution'],expected,atol=1e-10,rtol=1e-10)
                self.assertEqual(s['moment_source'],'code_feedback.ce')
                self.assertFalse(s['oracle_mean'])
            self.assertTrue(np.isfinite(result['llr']).all())
        for s in first[1:]:
            np.testing.assert_array_equal(s['A'],first[0]['A'])
            np.testing.assert_array_equal(s['mu'],first[0]['mu'])
            np.testing.assert_array_equal(s['finite_variance'],first[0]['finite_variance'])

    def test_zero_strength_is_mean_and_invalid_controls_fail(self):
        mean=self.run_mode('mean')
        for mode in ('zero_ridge','proximal'):
            result=self.run_mode(mode,0.)
            for k in ('H','mu','var','llr','decoded','info_hat'):
                np.testing.assert_array_equal(result[k],mean[k])
        for mode,strength in [('bad',1.),('jsoft',.5),('mean',True),('zero_ridge',-1.),('proximal',float('nan'))]:
            with self.assertRaises(ValueError):self.run_mode(mode,strength)


if __name__=='__main__':unittest.main()
