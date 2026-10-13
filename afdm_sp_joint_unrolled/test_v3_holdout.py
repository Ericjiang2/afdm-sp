import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import dev_rng
from afdm_sp_joint_unrolled.v3_holdout import holdout_rng


class HoldoutIdentityTest(unittest.TestCase):
    def test_legacy_generator_default_bytes_preserved(self):
        system=SimpleNamespace(N_total=16,rho=.5,_zc_seq=np.ones(16,dtype=complex),
            generate_channel_matrix=lambda:(np.random.normal(size=(16,16)),None,{}))
        code={'n':32,'k':16}
        a=make_frame(system,code,30,1,8,uncoded=True,split=2)
        b=make_frame(system,code,30,1,8,uncoded=True,split=2,rng_factory=dev_rng)
        for k in ('y','H','noise','info','coded'):np.testing.assert_array_equal(a[k],b[k])

    def test_components_and_identities_do_not_share_streams(self):
        samples=[holdout_rng(r,i,c).bytes(64) for r in range(3) for i in range(128) for c in (1,2,3)]
        self.assertEqual(len(set(samples)),1152)
        self.assertEqual(holdout_rng(0,0,1).bytes(64),holdout_rng(0,0,1).bytes(64))
        with self.assertRaises(ValueError):holdout_rng(3,0,1)
        with self.assertRaises(ValueError):holdout_rng(0,128,1)


if __name__=='__main__':unittest.main()
