"""Explicit CPU initializer driver, preserving default and observed-only inputs."""
import unittest
import numpy as np
import torch
from .classical_joint_unrolled import omp_sparse_torch
from .supplement_baselines import BaselineInitializer


class CPUSolverTests(unittest.TestCase):
    def test_explicit_gels_recovers_full_rank_support(self):
        rng=np.random.default_rng(43)
        a=rng.normal(size=(64,9))+1j*rng.normal(size=(64,9))
        a,_=np.linalg.qr(a)
        gains=np.zeros(9,dtype=complex);gains[[1,6]]=[1+.4j,.7-.2j]
        y=a@gains
        h,ids=omp_sparse_torch(torch.tensor(y),torch.tensor(a),2,lstsq_driver='gels')
        self.assertEqual(set(ids),{1,6})
        np.testing.assert_allclose(h.numpy(),gains,rtol=1e-12,atol=1e-12)
        with self.assertRaises(ValueError):omp_sparse_torch(torch.tensor(y),torch.tensor(a),2,lstsq_driver='unknown')

    def test_baseline_records_explicit_driver(self):
        rng=np.random.default_rng(15)
        a=rng.normal(size=(64,40))+1j*rng.normal(size=(64,40))
        y=rng.normal(size=64)+1j*rng.normal(size=64)
        estimator=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels')
        h,ids=estimator(torch.tensor(y),torch.tensor(a),40,torch.tensor(.2))
        self.assertEqual(estimator.record['lstsq_driver'],'gels')
        self.assertEqual(len(ids),24)
        self.assertTrue(torch.isfinite(h).all())


if __name__=='__main__':unittest.main()
