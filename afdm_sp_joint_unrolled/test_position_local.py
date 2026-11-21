import unittest
import numpy as np
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import fit_local_physical_cluster, physical_cluster_weights
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix

class PositionLocalTests(unittest.TestCase):
    def test_observed_reachable_offsets_improve_with_exact_fit_cap(self):
        system=_make_config_a(128,2,8,10,4)
        delays=np.arange(8);centers=np.zeros(8)
        params=dict(taps=8,l_i=delays,k_real=np.full(8,.25))
        pilot=np.sqrt(system.rho)*system._zc_seq
        Phi=construct_sensing_matrix(128,pilot,system.c1,system.c2,system.l_max_cap,system.k_max_cap)
        gains=np.exp(1j*np.arange(8))
        y=Phi@physical_cluster_weights(system,params)@gains
        H,result=fit_local_physical_cluster(system,delays,centers,Phi,y)
        self.assertEqual(result['fit_count'],33)
        self.assertLess(result['pilot_residual_squared'],result['trace'][0]['fit']['pilot_residual_squared'])
        self.assertTrue(any(x!=0 for x in result['locations']))
        self.assertEqual(result['stop_reason'],'registered_sweeps_exhausted')
        self.assertTrue(np.isfinite(H).all())
        # Truth is outside the local API: altering this unused source cannot change it.
        params['k_real']=np.full(8,-.49)
        H2,result2=fit_local_physical_cluster(system,delays,centers,Phi,y)
        np.testing.assert_array_equal(H,H2)
        self.assertEqual(result['trace'],result2['trace'])
        self.assertTrue(all(e['after']<=e['before'] for e in result['trace'][1:]))
        import json
        json.dumps(result,allow_nan=False)

    def test_clipped_ties_and_collisions_preserve_slots_and_budget(self):
        system=_make_config_a(128,2,8,10,4)
        Phi=construct_sensing_matrix(128,np.sqrt(system.rho)*system._zc_seq,system.c1,system.c2,system.l_max_cap,system.k_max_cap)
        centers=np.full(8,system.k_max_cap)
        _,r=fit_local_physical_cluster(system,np.zeros(8),centers,Phi,np.zeros(128,dtype=complex))
        self.assertEqual(r['fit_count'],17)
        self.assertEqual(r['locations'],centers.tolist())
        self.assertTrue(r['rank_deficient'])
        self.assertEqual(r['physical_slots'],8)
        self.assertTrue(all(not x['accepted'] for x in r['trace'][1:]))
        with self.assertRaisesRegex(ValueError,'fit 1/33 failed'):
            fit_local_physical_cluster(system,np.zeros(8),centers,np.zeros_like(Phi),np.zeros(128))

if __name__=='__main__':unittest.main()
