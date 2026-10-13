import importlib.util
from pathlib import Path
import unittest
import numpy as np
p=Path(__file__).with_name('e1a-residual-target-v1.py')
s=importlib.util.spec_from_file_location('residual_target',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DecompositionTest(unittest.TestCase):
 def inputs(self):
  rng=np.random.default_rng(417)
  def z(shape):return rng.normal(size=shape)+1j*rng.normal(size=shape)
  H=z((7,7));Hc=z((7,7));p=z(7);d=z(7);mu=z(7);noise=z(7);A=z((7,3));g=z(3)
  return [H@(p+d)+noise,H,Hc,p,d,mu,noise,A,g]
 def test_terms_and_all_cross_terms(self):
  y,H,Hc,p,d,mu,n,A,g=self.inputs();v=m.decompose(y,H,Hc,p,d,mu,n,A,g)
  np.testing.assert_allclose(v['residual'],v['terms'].sum(axis=0),atol=1e-12)
  np.testing.assert_allclose(v['terms'][0],H@p-Hc@p,atol=1e-12)
  np.testing.assert_allclose(v['terms'][1],H@mu-Hc@mu,atol=1e-12)
  np.testing.assert_allclose(v['terms'][2],H@d-H@mu,atol=1e-12)
  cross=sum(2*np.vdot(v['terms'][i],v['terms'][j]).real for i in range(6) for j in range(i+1,6))
  self.assertAlmostEqual(v['metrics']['all_cross_energy'],cross,places=10)
  self.assertGreater(abs(cross),1)
 def test_zero_target_is_explicit(self):
  args=self.inputs();args[2]=args[1].copy();v=m.decompose(*args)
  self.assertEqual(v['metrics']['pilot_error_energy'],0)
  self.assertIsNone(v['metrics']['residual_squared_complex_correlation'])
  self.assertIsNone(v['metrics']['residual_energy_over_pilot_error'])
 def test_recording_defect_preserved_and_large_rejected(self):
  args=self.inputs();args[0]=args[0]+1e-8;v=m.decompose(*args)
  self.assertGreater(v['metrics']['terms']['saved_rounding']['energy'],0)
  args[0]=args[0]+.01
  with self.assertRaises(ValueError):m.decompose(*args)
 def test_nonfinite_rejected(self):
  args=self.inputs();args[5][0]=np.nan
  with self.assertRaises(ValueError):m.decompose(*args)
 def test_exact_discrete_posterior_noise_cross_covariance(self):
  import itertools
  symbols=[.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]
  data=np.array(list(itertools.product(symbols,repeat=2)))
  H=np.array([[1,.2+.1j],[-.1j,.8]]);pilot=np.array([.5,.5j])
  y=H@(pilot+data[0])+np.array([.1+.05j,-.15+.02j]);sigma2=.4
  noise=y-(data+pilot)@H.T
  weights=np.exp(-np.sum(abs(noise)**2,axis=1)/sigma2);weights/=weights.sum()
  mu=weights@data;nmean=weights@noise;dc=data-mu;nc=noise-nmean
  V=np.einsum('k,ki,kj->ij',weights,dc,dc.conj())
  Cn=np.einsum('k,ki,kj->ij',weights,nc,nc.conj())
  Hd=dc@H.T;cross=np.einsum('k,ki,kj->ij',weights,Hd,nc.conj())
  np.testing.assert_allclose(nmean,y-H@(pilot+mu),atol=1e-12)
  np.testing.assert_allclose(Cn,H@V@H.conj().T,atol=1e-12)
  np.testing.assert_allclose(cross,-Cn,atol=1e-12)
  np.testing.assert_allclose(Hd+noise,np.broadcast_to(nmean,noise.shape),atol=1e-12)
  self.assertGreater(np.linalg.norm(Cn-sigma2*np.eye(2)),.01)
if __name__=='__main__':unittest.main()
