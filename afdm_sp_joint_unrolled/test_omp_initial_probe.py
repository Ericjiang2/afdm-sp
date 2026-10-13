"""Independent, bounded contracts for the exploratory probe."""
import unittest
import numpy as np
import torch

from afdm_sp_joint_unrolled.omp_initial_probe import reference_support, support_quality, count_errors
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.analyze_omp_initial_probe import paired_statistics


class ProbeTests(unittest.TestCase):
    def test_equal_error_totals_still_record_bit_repair_and_harm(self):
        mask_a=np.zeros(2048,dtype=np.uint8);mask_a[0]=1
        mask_b=np.zeros(2048,dtype=np.uint8);mask_b[1]=1
        arms={name:dict(errors=1,error_mask_hex=np.packbits(mask).tobytes().hex())
              for name,mask in [('A',mask_a),('B',mask_b)]}
        rows=[dict(stages={'final_receiver':arms}) for _ in range(48)]
        indices=[(j,np.tile(np.arange(16),(10,1))) for j in (0,16,32)]
        result=paired_statistics(rows,'final_receiver','A','B',indices)
        self.assertEqual(result['delta_BER'],0)
        self.assertEqual(result['CI95_delta_BER'],[0,0])
        self.assertEqual(result['repaired_bits'],48)
        self.assertEqual(result['introduced_bits'],48)

    def test_reference_retains_capacity_and_separates_padding(self):
        padded,compact=reference_support([0,1,2,3],{1:2j,4:1j,5:0j},8)
        self.assertEqual(padded,[1,4,0,2])
        self.assertEqual(compact,[1,4])
        quality=support_quality([0,1,2,3],{1:2j,4:1j,5:0j})
        self.assertEqual(quality['missed_ids'],[4])
        self.assertEqual(quality['false_ids'],[0,2,3])
        self.assertAlmostEqual(quality['missed_coefficient_energy'],.2)

    def test_overbudget_truth_is_ranked_with_deterministic_ties(self):
        self.assertEqual(reference_support([0,1],{2:1,3:2,4:-2},5),([3,4],[3,4]))
        for raw,gains in [([0,0],{1:1}),([0],{5:1}),([0],{1:float('nan')})]:
            with self.assertRaises(ValueError):reference_support(raw,gains,5)

    def test_cancellation_is_merged_before_truth_labels(self):
        params=dict(taps=2,l_i=[0,0],k_real=[0,0],l_exp=[0,0,1],k_exp=[0,0,0],chan_coef_exp=[1,-1,.5j])
        ledger=merged_truth_ledger(params,1)
        self.assertEqual(ledger['K_true'],1)
        self.assertEqual(ledger['entries'][0]['above_threshold'],False)

    def test_ber_bit_order_and_mask(self):
        result=count_errors(np.array([1+1j,-1-1j]),np.array([0,0,0,1]))
        self.assertEqual(result['errors'],1)
        self.assertEqual(result['bits'],4)
        self.assertEqual(result['error_mask_hex'],'40')

    def test_oracle_matches_independent_generator_dense_ls(self):
        system=_make_config_a(32,2,2,10,4)
        k=system.k_max_cap
        pairs=[(0,0),(1,0),(2,1)]
        basis=np.column_stack([system.gen_h_daft(np.array([1.+0j]),np.array([l]),np.array([d])).reshape(-1)
                               for l,d in pairs])
        H=(basis@np.array([1+.2j,.3j,.1])).reshape(32,32)
        chosen=[0,2]
        fitted,_=project_channel_on_support(torch.from_numpy(H),
            torch.tensor([pairs[i][0] for i in chosen]),torch.tensor([pairs[i][1] for i in chosen]),
            system.c1,system.c2,k)
        independent=basis[:,chosen]@np.linalg.lstsq(basis[:,chosen],H.reshape(-1),rcond=1e-12)[0]
        np.testing.assert_allclose(fitted.numpy().reshape(-1),independent,rtol=1e-10,atol=1e-11)


if __name__=='__main__':unittest.main()
