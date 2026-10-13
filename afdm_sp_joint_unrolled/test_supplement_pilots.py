import unittest
import numpy as np
from .supplement_pilots import transform,cpp,propagate_cpp,candidates,select_pilots,waveform_metrics,paired_observations
class Tests(unittest.TestCase):
 def test_daft_dense_and_round_trip(self):
  n=np.arange(16);c1=5/32;c2=.002;x=np.exp(.4j*n)
  A=np.exp(2j*np.pi*c2*n*n)[:,None]*np.exp(-2j*np.pi*n[:,None]*n/16)/4*np.exp(2j*np.pi*c1*n*n)[None,:]
  np.testing.assert_allclose(transform(x,c1,c2),A@x,atol=2e-14)
  np.testing.assert_allclose(transform(x,c1,c2,inverse=True),A.conj().T@x,atol=2e-14)
  np.testing.assert_allclose(transform(transform(x,c1,c2,inverse=True),c1,c2),x,atol=2e-14)
 def test_cpp_fractional_path_against_analytic_chirped_tone(self):
  N=16;n=np.arange(N);c1=5/32;delay=3;nu=.35
  # IDAFT of a single tone: evaluate extension analytically at negative indices.
  s=np.exp(-2j*np.pi*c1*n*n)*np.exp(2j*np.pi*2*n/N)
  expected=np.exp(-2j*np.pi*c1*(n-delay)**2)*np.exp(2j*np.pi*2*(n-delay)/N)*np.exp(2j*np.pi*nu*n/N)
  out=propagate_cpp(s,c1,[delay],[nu],[1.],prefix_length=3)
  np.testing.assert_allclose(out,expected,atol=1e-13)
 def test_shared_observation_and_energy_no_normalization(self):
  N=16;n=np.arange(N);p0=np.exp(-1j*np.pi*n*n/N);cs,p2=candidates(N,p0);pilots=dict(p0=p0,p1=cs[2][1],p2=p2)
  data=.5*(np.ones(N)+1j*(-1.)**n);H=np.diag(np.arange(1,N+1)/N);noise=np.exp(.3j*n)
  obs,meta=paired_observations(H,data,noise,pilots,rho=.5,sigma2=.1)
  for name,p in pilots.items():
   np.testing.assert_allclose(obs[name]['y']-H@obs[name]['pilot'],H@data+np.sqrt(.1)*noise,atol=1e-14)
   s,extended,v=waveform_metrics(p,data,rho=.5,c1=5/32,c2=.002,prefix_length=3,papr_limit_db=12.,peak_power_limit=16.)
   self.assertAlmostEqual(v['payload_energy'],v['pilot_energy']+v['data_energy']+v['cross_energy'],places=12)
   np.testing.assert_array_equal(extended[3:],s)
  self.assertEqual(meta['normalization'],'none')
 def test_geometry_choice_deterministic_and_separate_control(self):
  N=16;n=np.arange(N);p0=np.exp(-1j*np.pi*n*n/N)
  a,meta=select_pilots(p0,c1=5/32,c2=.002,l_max=2,k_max=1)
  b,again=select_pilots(p0,c1=5/32,c2=.002,l_max=2,k_max=1)
  self.assertEqual(meta['selected_index'],again['selected_index']);self.assertEqual(len(meta['candidates']),8)
  # CPU complex kernels can differ by an ulp with array alignment. Persist actual hashes,
  # but require numerical geometry equivalence and bit-exact selected pilot arrays.
  np.testing.assert_allclose([r['max_coherence'] for r in meta['candidates']],
      [r['max_coherence'] for r in again['candidates']],rtol=1e-14,atol=1e-14)
  self.assertEqual([r['pilot_sha256'] for r in meta['candidates']],[r['pilot_sha256'] for r in again['candidates']])
  self.assertEqual(meta['selected_index'],min(range(8),key=lambda i:(meta['candidates'][i]['max_coherence'],i)))
  self.assertNotIn(meta['p2_sha256'],[x['pilot_sha256'] for x in meta['candidates']])
  for k in a:np.testing.assert_array_equal(a[k],b[k])
 def test_physical_cpp_matches_actual_integer_dictionary_and_channel(self):
  from .afdm_env import AFDMEnvMixin
  from .afdm_baselines import construct_sensing_matrix
  env=object.__new__(AFDMEnvMixin);env.N_total=16;env.c1=5/32;env.c2=.002
  n=np.arange(16);pilot=np.exp(.31j*n);delay=2;k=-1
  H=env.gen_h_daft(np.array([1.+0j]),np.array([delay]),np.array([k]))
  time_signal=transform(pilot,env.c1,env.c2,inverse=True)
  y=transform(propagate_cpp(time_signal,env.c1,[delay],[k],[1.],prefix_length=3),env.c1,env.c2)
  phi=construct_sensing_matrix(16,pilot,env.c1,env.c2,3,2)
  np.testing.assert_allclose(y,H@pilot,atol=1e-13)
  np.testing.assert_allclose(y,phi[:,delay*5+k+2],atol=1e-13)
 def test_invalid_paths_and_prefix(self):
  for d in ([-1],[1.5],[4]):
   with self.assertRaises(ValueError):propagate_cpp(np.ones(16),5/32,d,[.2],[1],prefix_length=3)
  with self.assertRaises(ValueError):cpp(np.ones(16),5/32,16)
if __name__=='__main__':unittest.main()
