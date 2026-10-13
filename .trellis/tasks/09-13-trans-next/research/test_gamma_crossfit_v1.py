"""Focused contracts for the bounded Gamma offline scorer."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

PATH=Path(__file__).with_name('gamma_crossfit_v1.py')
SPEC=importlib.util.spec_from_file_location('gamma_crossfit_v1',PATH)
gamma=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gamma)


class GammaCrossfitContract(unittest.TestCase):
    def test_fold_rejects_target_even_if_other_fifteen_present(self):
        rng=np.random.default_rng(3)
        errors={j:rng.normal(size=6)+1j*rng.normal(size=6)
                for j in range(1,16)}
        accepted=gamma.fold(errors,0)
        self.assertEqual(accepted['channels'],tuple(range(1,16)))
        self.assertLessEqual(accepted['rank'],14)
        with self.assertRaisesRegex(ValueError,'leaked'):
            gamma.fold({0:np.zeros(6),**errors},0)
        with self.assertRaisesRegex(ValueError,'leaked'):
            gamma.fold({j:v for j,v in errors.items() if j!=15},0)

    def test_candidate_six_scalars_rebuild_reported_three_terms(self):
        n=13;c1=3/(2*n);c2=.01
        operator=gamma.layout(n,1,1,c1,c2)
        rng=np.random.default_rng(7)
        p=rng.normal(size=n)+1j*rng.normal(size=n)
        mu=rng.normal(size=n)+1j*rng.normal(size=n)
        mu[2]=.11+0j
        m=rng.normal(size=6)+1j*rng.normal(size=6)
        U=(rng.normal(size=(6,3))+1j*rng.normal(size=(6,3)))/4
        y=rng.normal(size=n)+1j*rng.normal(size=n)
        mean,Z=gamma.baseline_action(p+mu,operator,m,U)
        L,logdet=gamma.factor_covariance(Z,.1)
        row=gamma.candidate_pair(y,p,mu,m,U,operator,.1,2,(mean,Z,L,logdet))
        s=row['scalar_terms']
        self.assertEqual(row['candidate_plus'],[.5,.5])
        self.assertEqual(row['candidate_minus'],[-.5,.5])
        self.assertEqual(row['score_calls']['frozen_C_mu'],0)
        self.assertEqual(row['score_calls']['candidate_C'],2)
        self.assertAlmostEqual(row['delta_frozen_covariance_mean'],
            s['fixed_q_plus']-s['fixed_q_minus'],places=11)
        self.assertAlmostEqual(row['delta_inverse_covariance_change'],
            (s['q_plus']-s['fixed_q_plus'])-(s['q_minus']-s['fixed_q_minus']),places=11)
        self.assertAlmostEqual(row['delta_logdet_change'],
            s['logdet_plus']-s['logdet_minus'],places=11)
        self.assertAlmostEqual(row['delta_total_NLL'],
            (s['q_plus']+s['logdet_plus'])-(s['q_minus']+s['logdet_minus']),places=11)


if __name__=='__main__':unittest.main()
