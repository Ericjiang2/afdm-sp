"""Algebra and orchestration contracts only; no scientific receiver runs."""
import ast
import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
import numpy as np
import uniform_gamma as g
from test_gram_cohort import GramCohortTest

block = g.module('__uniform_test_block', 'gram_block.py')
probe = g.module('__uniform_test_probe', 'gram_block_probe.py')


def physical_kernel():
    # Load actual frozen pure NumPy covariance functions without importing its
    # unrelated SciPy optimizer (not available in the local test runtime).
    path = g.HERE.parent/'sp_afdm_frozen_20260920/src/physical.py'
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('dkernel','projected_variance')]
    namespace = {'np':np}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
    return NS(projected_variance=namespace['projected_variance'], daft=lambda x,*a:x)


def diagnostic():
    return dict(original_min_eigenvalue=0., uniform_min_eigenvalue=0., identity_absolute=0.,
                identity_scale=1., identity_relative=0., gamma_projected_variance_calls=2, actual_gamma_fft_count=2)


class UniformMatrixTest(unittest.TestCase):
    def test_dense_same_delay_geometry_distinct_from_diagonal_gamma(self):
        fixture, v, original = probe.gamma_fixture(); physical = physical_kernel()
        facade = g.UniformGamma(physical)
        uniform = facade.projected_variance(v,fixture['delays'],fixture['dopplers'],fixture['c1'])
        atoms = probe.rep.dense_atoms(fixture)
        dense = np.einsum('prk,qrk,k->pq',atoms.conj(),atoms,np.full(32,v.mean()))
        np.testing.assert_allclose(uniform,dense,rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(uniform,original*(fixture['delays'][:,None]==fixture['delays'][None,:]),atol=1e-12)
        self.assertGreater(abs(uniform[0,1]),.1)
        self.assertGreater(np.linalg.norm(uniform-np.diag(np.diag(original))),.1)
        self.assertGreater(np.linalg.norm(original-uniform),1e-3)
        B=np.array([[1.,1.,2.],[1.,2.,1.],[2.,1.,1.]],complex)
        _,detail=block.solve_gain(B,np.ones(3),uniform,.1,'full')
        np.testing.assert_array_equal(detail['Q'],B.conj().T@B+uniform+.3*np.eye(3))
        self.assertEqual(detail['Q'][0,2],(B.conj().T@B)[0,2])
        value=np.ones(3);self.assertIs(facade.daft(value),value)

    def test_zero_uniform_tiny_and_all_unique_delays(self):
        physical=physical_kernel();delays=np.array([1,1,3]);nu=np.array([.25,-.45,.7])
        for v in (np.zeros(32),np.full(32,.3),np.linspace(1e-15,2e-15,32)):
            facade=g.UniformGamma(physical)
            actual=facade.projected_variance(v,delays,nu,5/64)
            expected=physical.projected_variance(np.full(32,v.mean()),delays,nu,5/64)
            np.testing.assert_array_equal(actual,expected)
            self.assertLessEqual(facade.diagnostics[0]['identity_relative'],g.cohort.RTOL)
        unique=g.UniformGamma(physical).projected_variance(np.linspace(.1,.8,32),[1,2,3],nu,5/64)
        np.testing.assert_allclose(unique,np.eye(3)*14.4,atol=1e-12)

    def test_original_invalid_covariance_is_rejected_before_projection(self):
        invalid=(np.array([[1.,2.],[2.,1.]]),np.array([[1.,2.],[0.,1.]]),np.array([[1.,np.nan],[np.nan,1.]]),np.eye(3))
        for original in invalid:
            calls=[]
            def kernel(*args):
                calls.append(1)
                return original if len(calls)==1 else np.eye(2)
            with self.subTest(original=original),self.assertRaises(ValueError):
                g.UniformGamma(NS(projected_variance=kernel)).projected_variance(np.ones(4),[0,1],[0.,.2],.1)
            self.assertEqual(len(calls),1)
        calls=[]
        def invalid_uniform(*args):
            calls.append(1);return np.eye(2) if len(calls)==1 else np.array([[1.,2.],[2.,1.]])
        with self.assertRaises(ValueError):g.UniformGamma(NS(projected_variance=invalid_uniform)).projected_variance(np.ones(4),[0,1],[0.,.2],.1)

    def test_input_and_zero_scale_identity_fail_closed(self):
        physical=physical_kernel()
        for v,d,n in (([],[0],[0]),([1.,-1.],[0],[0]),([1.,np.nan],[0],[0]),([1.,2.],[.5],[0]),
                      ([1.,2.],[2],[0]),([1.,2.],[0],[np.nan]),([1.,2.],[0,1],[0])):
            with self.subTest(v=v,d=d),self.assertRaises(ValueError):g.UniformGamma(physical).projected_variance(v,d,n,.1)
        calls=[]
        def mismatch(v,*args):
            calls.append(1);return np.eye(1)*2e-12 if len(calls)%2==0 else np.zeros((1,1))
        with self.assertRaises(AssertionError):g.UniformGamma(NS(projected_variance=mismatch)).projected_variance(np.zeros(4),[0],[0],.1)


class UniformProcessTest(unittest.TestCase):
    def setUp(self):
        self.f=GramCohortTest();self.f.setUp();f=self.f
        self.full=f.process();self.assertEqual(self.full['status'],'ok')
        self.diag=dict(full_row_sha256=g.oldagg.row_sha(self.full))
        f.calls=f.decode_calls=0
        frozen=f.block.scalar_point
        def detector(*args,**kwargs):
            if isinstance(kwargs['physical'],g.UniformGamma):
                for _ in range(20):kwargs['physical'].projected_variance(np.ones(2),[1],[.25],.1)
            return frozen(*args,**kwargs)
        self.block=NS(scalar_point=detector)
        self.physical=NS(projected_variance=lambda v,*args:np.array([[sum(v)]],complex))

    def process(self,gate=False):
        f=self.f;k=g.cohort.KEY
        return g.process_key(f.ctx,f.helper,self.block,None,self.physical,f.meta,f.obs,np.zeros(2),f.truth,
                             f.three[k],f.run2[k],self.full,self.diag,gate=gate)

    def test_counts_observer_and_actual_compute(self):
        consumer=g.module('__uniform_process_consumer','aggregate_uniform_gamma.py');k=g.cohort.KEY
        for gate,receivers,decoders in ((False,2,2),(True,6,4)):
            self.f.calls=self.f.decode_calls=0
            row=self.process(gate);self.assertEqual(row['status'],'ok',row.get('error'))
            self.assertEqual((self.f.calls,self.f.decode_calls),(receivers,decoders))
            consumer.validate([row],{k:self.f.three[k]},{k:self.f.run2[k]},{k:self.full},{k:self.diag},gate)
            score=row['arms']['L-diag']['uniform_gamma']
            self.assertEqual((score['fft_count'],score['logical_fft_count'],score['actual_fft_count']),(61,61,81))
            self.assertEqual(row['sbl_calls'],0)

    def test_drift_failure_and_attempt_retention(self):
        self.f.fail_at=2;row=self.process()
        self.assertEqual(row['status'],'error');self.assertEqual(row['attempts'][-1]['status'],'error')
        self.assertEqual((row['receiver_calls'],row['decoder_calls']),(2,1))
        self.f.fail_at=None;self.full['arms']['L-diag']['full']['decoded_sha256']='drift'
        self.diag['full_row_sha256']=g.oldagg.row_sha(self.full)
        row=self.process(True);self.assertEqual(row['status'],'error');self.assertIn('full replay drift',row['error'])

    def test_actual_path_and_commit_validation_before_loading_receiver(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'gamma_ablation.py';path.write_text(Path(g.gamma.__file__).read_text())
            with self.assertRaisesRegex(ValueError,'actual source path'):g.actual_sources({'gamma':NS(__file__=path)})
        with self.assertRaisesRegex(ValueError,'full producing commit'):g.run(NS(producing_commit='1234'))


if __name__=='__main__':unittest.main()
