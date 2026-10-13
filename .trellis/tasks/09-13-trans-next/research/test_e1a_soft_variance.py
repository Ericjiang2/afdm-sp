import importlib.util
from pathlib import Path
import unittest
import numpy as np
p=Path(__file__).with_name('e1a-soft-variance-v1.py');s=importlib.util.spec_from_file_location('variance_audit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class VarianceTest(unittest.TestCase):
 def args(self):
  rng=np.random.default_rng(761);H=rng.normal(size=(4,4))+1j*rng.normal(size=(4,4));d=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]);mu=d*np.array([1,.99,.9,.5]);v=.5-abs(mu)**2;v=np.maximum(v,0)
  return [d,mu,v,H,H,np.array([.1,.2j,-.3,.1j]),.1]
 def test_trace_and_cross(self):
  args=self.args();out=m.variance_metrics(*args);H=args[3];C=H@np.diag(args[2])@H.conj().T+.1*np.eye(4)
  self.assertAlmostEqual(out['metrics']['predicted_total_energy'],np.trace(C).real)
  self.assertAlmostEqual(out['metrics']['actual_total_energy'],np.linalg.norm(H@(args[0]-args[1])+args[5])**2)
 def test_bins_cover_boundaries(self):
  args=self.args();args[2]=np.array([0,.005,.05,.25]);out=m.variance_metrics(*args)
  self.assertEqual([b['count'] for b in out['metrics']['bins']],[1,1,1,1])
 def test_zero_prediction_reports_error(self):
  args=self.args();args[2]=np.zeros(4);out=m.variance_metrics(*args)
  self.assertIsNone(out['metrics']['error_to_variance']);self.assertGreater(out['metrics']['zero_variance_error_sum'],0)
 def test_negative_rejected(self):
  args=self.args();args[2][0]=-.1
  with self.assertRaises(ValueError):m.variance_metrics(*args)
if __name__=='__main__':unittest.main()
