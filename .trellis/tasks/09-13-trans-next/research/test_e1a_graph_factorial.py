import importlib.util
from pathlib import Path
import unittest
import numpy as np

path = Path(__file__).with_name('e1a-graph-factorial-v1.py')
spec = importlib.util.spec_from_file_location('graph_factorial', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class GraphFactorialTest(unittest.TestCase):
    def inputs(self):
        H0 = np.array([[.3+.1j, 1e-6], [2e-5j, .4]], dtype=complex)
        H1 = np.array([[.2-.1j, .08j], [.05, .7]], dtype=complex)
        return H0, H1, np.abs(H0) >= 1e-4

    def test_reweights_only_original_domain(self):
        H0,H1,mask = self.inputs()
        v = m.factor_graph(H0,H1,mask)
        np.testing.assert_array_equal(v['G_REWEIGHT'], [[.2-.1j, 1e-6], [2e-5j, .7]])
        np.testing.assert_array_equal(v['G_REWEIGHT'][~mask],H0[~mask])

    def test_adds_outside_keeps_original_weights(self):
        H0,H1,mask = self.inputs()
        v = m.factor_graph(H0,H1,mask)
        np.testing.assert_array_equal(v['G_ADD'], [[.3+.1j, .08j], [.05, .4]])
        np.testing.assert_allclose(v['G_ADD']+v['G_REWEIGHT'],H0+H1,atol=1e-15)

    def test_original_edge_may_be_removed(self):
        H0,H1,mask = self.inputs()
        H1[0,0] = 1e-6
        v = m.factor_graph(H0,H1,mask)
        self.assertLess(abs(v['G_REWEIGHT'][0,0]),1e-4)
        self.assertGreater(abs(v['G_ADD'][0,0]),1e-4)

    def test_unchanged_endpoint_stays_exact(self):
        H0,_,mask = self.inputs()
        v = m.factor_graph(H0,H0,mask)
        for arm in m.ARMS:
            np.testing.assert_array_equal(v[arm],H0)
            self.assertIsNot(v[arm],H0)

    def test_bad_shape_nonfinite_nonboolean_rejected(self):
        H0,H1,mask = self.inputs()
        for a,b,c in [(H0[:-1],H1,mask),(H0,H1,mask.astype(int)),(H0,H1,mask[:-1])]:
            with self.assertRaises(ValueError):m.factor_graph(a,b,c)
        H1[0,0] = np.nan
        with self.assertRaises(ValueError):m.factor_graph(H0,H1,mask)


if __name__ == '__main__':
    unittest.main()
