import unittest
from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger, match_physical_slots, stage_losses


class RepresentationLedgerTests(unittest.TestCase):
    def test_complex_cancellation_and_outside_dictionary_survive_truth_record(self):
        p=dict(taps=3,l_i=[0,1,2],k_real=[0.,.5,1.],l_exp=[0,0,1],k_exp=[0,0,3],chan_coef_exp=[1+2j,-1-2j,2j])
        r=merged_truth_ledger(p,2)
        import json
        json.dumps(r,allow_nan=False)
        self.assertEqual((r['P_phys'],r['K_emit'],r['K_unique_merged'],r['K_true']),(3,3,2,1))
        self.assertEqual(r['K_true_in_receiver_doppler_domain'],0)
        self.assertIsNone(r['entries'][1]['column'])
        self.assertIsNone(r['physical_matching']['recall'])

    def test_one_to_one_and_explicit_collision_denominator(self):
        r=match_physical_slots([[0,0],[0,0],[1,1],[2,2]],[[1,1]])
        self.assertEqual(r['colliding_truth_slots'],[0,1])
        self.assertEqual(r['identifiable_denominator'],2)
        self.assertEqual(r['matches'],[(2,0)])
        self.assertEqual(r['recall'],.5)

    def test_unestimated_physical_slots_still_report_collisions(self):
        r=match_physical_slots([[0,0],[0,0],[1,1]])
        self.assertIsNone(r['recall'])
        self.assertEqual(r['colliding_truth_slots'],[0,1])

    def test_actual_graph_threshold_boundary_and_observer_cannot_modify_detector(self):
        import torch
        from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
        H=torch.tensor([[.5,.25],[0.,1.]],dtype=torch.complex64)
        y=torch.tensor([1.,-1.],dtype=torch.complex64)
        c=torch.tensor([1.,-1.],dtype=torch.complex64)
        records=[]
        def observe(record):
            records.append(record.copy())
            record['row_degrees']=[999,999]  # detached summary, never detector state
        off=mp_detect_bp_torch(y,H,.1,c,n_iter=2,threshold=.5,return_soft=True)
        on=mp_detect_bp_torch(y,H,.1,c,n_iter=2,threshold=.5,return_soft=True,graph_observer=observe)
        for a,b in zip(off,on):self.assertTrue(torch.equal(a,b))
        self.assertEqual(records[0]['dtype'],'torch.complex128')
        self.assertEqual(records[0]['edges'],2)
        self.assertEqual(records[0]['row_degrees'],[1,1])
        self.assertEqual(records[0]['column_degrees'],[1,1])
        self.assertEqual(records[0]['discarded_squared_frobenius'],.0625)
        self.assertAlmostEqual(records[0]['threshold_loss'],.0625/1.3125)
        empty=[]
        mp_detect_bp_torch(y,torch.zeros_like(H),.1,c,graph_observer=empty.append)
        self.assertEqual(empty[0]['edges'],0)
        self.assertIsNone(empty[0]['threshold_loss'])

    def test_runner_import_bound_final_bp_forwards_graph_callback(self):
        import numpy as np
        from afdm_sp_joint_unrolled import budgeted_support_eval as runner
        records=[]
        runner.final_bp(np.ones(2,dtype=complex),np.eye(2,dtype=complex),.1,
            np.array([1.,-1.],dtype=complex),n_iter=2,return_soft=True,graph_observer=records.append)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['edges'],2)

    def test_independent_generator_projection_and_empty_support(self):
        import numpy as np
        from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
        from afdm_sp_joint_unrolled.representation_ledger import representation_error
        system=_make_config_a(128,2,8,10,4)
        np.random.seed(2026090612)
        H,_,params=system.generate_channel_matrix()
        r=representation_error(system,params,H,[0,1,2,7],system.k_max_cap,dense_reference=True,H_actual=H)
        self.assertLess(r['dense_reference']['projection_difference_norm'],1e-10)
        self.assertEqual(r['dense_reference']['rank'],4)
        self.assertEqual(r['actual_channel_error_squared'],0.)
        empty=representation_error(system,params,H,[],system.k_max_cap,dense_reference=True)
        self.assertAlmostEqual(empty['E_repr'],1.)

    def test_active_truth_does_not_count_as_candidate_generation_miss(self):
        events=[dict(stage='pool',candidate_ids=[2,3]),dict(stage='union',selected_ids=[2]),
                dict(stage='final_prune',pruned_ids=[1,2])]
        import numpy as np, json
        r=stage_losses(np.array([1,2,4]),events,[3],raw_ids=[1])
        json.dumps(r,allow_nan=False)
        self.assertEqual(r['truth_not_in_pool'],[4])
        self.assertEqual(r['selected_then_pruned'],[2])
        self.assertEqual(r['initially_true_then_pruned'],[1])


if __name__=='__main__':unittest.main()
