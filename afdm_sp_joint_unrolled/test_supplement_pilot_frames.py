import unittest
import numpy as np
from types import MappingProxyType
from .direction_data import CampaignFrame
from .budgeted_support_diagnostics import array_hash
from .supplement_pilots import candidates
from .supplement_pilot_frames import pilot_frames
class Tests(unittest.TestCase):
 def fixture(self):
  N=16;n=np.arange(N);p0=np.exp(-1j*np.pi*n*n/N);cs,p2=candidates(N,p0)
  pilots=dict(p0=p0,p1=cs[3][1],p2=p2);data=.5*(np.ones(N)+1j*(-1.)**n)
  truth=dict(H=np.eye(N,dtype=complex),data=data,noise=np.exp(.2j*n),info=np.zeros(N,dtype=np.uint8),coded=np.zeros(2*N,dtype=np.uint8))
  obs=dict(y=truth['H']@(np.sqrt(.5)*p0+data)+np.sqrt(.1)*truth['noise'],pilot=np.sqrt(.5)*p0,sigma2=np.array(.1),constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
  meta=dict(scenario='G0',input_hashes={k:array_hash(v) for k,v in dict(truth,**obs).items()})
  return CampaignFrame(MappingProxyType(obs),meta,truth),pilots
 def test_three_observed_boundaries_and_original_not_mutated(self):
  f,p=self.fixture();old=dict(f.metadata['input_hashes']);frames=pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3)
  self.assertEqual(f.metadata['input_hashes'],old)
  for name,g in frames.items():
   self.assertEqual(set(g.observed),{'y','pilot','sigma2','constellation'})
   self.assertEqual(g.metadata['pilot_id'],name);self.assertIs(g._truth,f._truth)
   self.assertFalse(g.observed['y'].flags.writeable)
   for k in ('H','data','noise','info','coded'):self.assertEqual(g.metadata['input_hashes'][k],old[k])
   self.assertEqual(g.metadata['input_hashes']['y'],array_hash(g.observed['y']))
 def test_bad_common_data_and_wrong_p0_rejected(self):
  f,p=self.fixture();f._truth['noise'][0]+=1
  with self.assertRaises(ValueError):pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3)
  f,p=self.fixture();p['p0']=p['p2']
  with self.assertRaises(ValueError):pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3)
 def test_power_failure_retained(self):
  f,p=self.fixture();frames=pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3,peak_power_limit=.01)
  self.assertEqual(len(frames),3)
  self.assertTrue(all(not g.metadata['power']['passes_declared_simulation_power_gate'] for g in frames.values()))
 def test_counterexample_generator_and_original_p0_lineage(self):
  for scenario in ('integer','overlap'):
   with self.subTest(scenario=scenario):
    f,p=self.fixture();f.metadata.update(scenario=scenario,generator='truncated_daft')
    frames=pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3,preserve_original_p0=True)
    for g in frames.values():
     self.assertEqual(g.metadata['scenario'],scenario)
     self.assertEqual(g.metadata['generator'],'truncated_daft')
     for k in ('H','data','noise','info','coded'):
      self.assertEqual(g.metadata['input_hashes'][k],f.metadata['input_hashes'][k])
    for k,v in f.observed.items():np.testing.assert_array_equal(frames['p0'].observed[k],v)
    self.assertEqual(frames['p0'].metadata['input_hashes']['y'],f.metadata['input_hashes']['y'])
 def test_unknown_or_physical_generator_is_not_relabelled(self):
  for scenario,generator in (('integer',None),('G0','physical_cpp_untruncated'),
                             ('G1','physical_cpp_untruncated'),('overlap','unknown')):
   with self.subTest(scenario=scenario,generator=generator):
    f,p=self.fixture();f.metadata.update(scenario=scenario,generator=generator)
    with self.assertRaises(ValueError):pilot_frames(f,p,c1=5/32,c2=.002,prefix_length=3)
if __name__=='__main__':unittest.main()
