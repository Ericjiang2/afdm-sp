"""Schedule accounting must not enable the full graph audit in deployment."""
import unittest
from unittest.mock import patch
import numpy as np
import torch
from . import test_terminal_prior_receiver as fixtures
from .supplement_feedback_schedule import UniformBPSchedule
from .mp_detect_bp_torch import mp_detect_bp_torch
from . import representation_ledger
from .light_gap_receiver_run import run_arm, NUMERIC_FIELDS, receiver_resources
from . import classical_joint_unrolled as joint
from .direction_receiver import terminal_decode
from .trans_next_stop_run import same_state


class ScheduleGraphCostTests(unittest.TestCase):
    setUp = fixtures.TerminalPriorReceiverTests.setUp
    feedback = fixtures.TerminalPriorReceiverTests.feedback

    def test_audit_false_never_calls_graph_ledger_and_preserves_numerics(self):
        for graph in (None, 'integer'):
            options=dict(bp_schedule=UniformBPSchedule(12),outer_bp_graph=graph,terminal_check_prior='retain')
            observed=self.receiver.run(self.observed,audit=True,code_feedback=self.feedback(),**options)
            with patch.object(representation_ledger,'actual_bp_graph',side_effect=AssertionError('graph audit ran')):
                plain=self.receiver.run(self.observed,audit=False,code_feedback=self.feedback(),**options)
            for field in ('H','x_soft','support','gains','mu','var','llr','decoded','info_hat','x_hard'):
                np.testing.assert_array_equal(plain[field],observed[field])
            self.assertEqual(plain['graphs'],[])
            self.assertEqual(plain['bp_schedule'],observed['bp_schedule'])
            self.assertEqual(len(plain['bp_schedule']['calls']),3)

    def test_edge_counter_exact_empty_and_thresholded_dense_sparse(self):
        const=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        for H in (torch.zeros((0,0),dtype=torch.complex64),torch.zeros((2,2),dtype=torch.complex64),
                  torch.tensor([[.5,.25],[0.,1.]],dtype=torch.complex64)):
            for matrix in (H,H.to_sparse()):
                counts=[];y=torch.ones(H.shape[0],dtype=torch.complex64)
                expected=mp_detect_bp_torch(y,matrix,.2,const,threshold=.5,return_soft=True)
                actual=mp_detect_bp_torch(y,matrix,.2,const,threshold=.5,return_soft=True,edge_count_observer=counts.append)
                self.assertEqual(counts,[int(torch.count_nonzero(H.abs()>=.5))])
                for a,b in zip(actual,expected):self.assertTrue(torch.equal(a,b))

    def test_invalid_edge_counter_rejected(self):
        with self.assertRaises(ValueError):
            mp_detect_bp_torch(np.ones(2,complex),np.eye(2),.2,self.observed['constellation'],edge_count_observer=True)

    def test_public_runner_without_audit_or_message_retention_is_exact(self):
        arm=dict(name='REFERENCE',receiver=dict(terminal_check_prior='retain',outer_bp_graph='integer'),
                 feedback=dict(retain_messages=True,stop_on_valid_codeword=True))
        observed=run_arm(self.receiver,self.code,self.observed,arm)
        arm['feedback']['retain_messages']=False
        with patch.object(representation_ledger,'actual_bp_graph',side_effect=AssertionError('graph audit ran')):
            plain=run_arm(self.receiver,self.code,self.observed,arm,audit=False)
        for field in NUMERIC_FIELDS:np.testing.assert_array_equal(plain[field],observed[field])
        self.assertEqual(plain['graphs'],[])
        self.assertEqual(plain['bp_schedule'],observed['bp_schedule'])
        with self.assertRaises(ValueError):run_arm(self.receiver,self.code,self.observed,arm,audit='off')

    def test_actual_resource_counts_do_not_depend_on_audit_arrays(self):
        for graph in (None, 'integer'):
            options=dict(bp_schedule=UniformBPSchedule(12),outer_bp_graph=graph,
                         terminal_check_prior='retain')
            audited=self.receiver.run(self.observed,audit=True,code_feedback=self.feedback(),**options)
            with patch.object(joint,'soft_gain_update',wraps=joint.soft_gain_update) as solve:
                plain=self.receiver.run(self.observed,audit=False,code_feedback=self.feedback(),**options)
            self.assertEqual(plain['dals'],[])
            counts=receiver_resources(plain)
            self.assertEqual(counts['CE_solves'],solve.call_count)
            self.assertEqual(counts['CE_solves'],2)
            self.assertEqual(counts,receiver_resources(audited))

    def test_terminal_edge_counter_observes_empty_and_nonempty_actual_graph(self):
        for H in (np.zeros((32,32),complex),np.eye(32,dtype=complex)):
            counts=[]
            args=(self.observed['y'],H,.2,self.observed['constellation'],self.code)
            expected=terminal_decode(*args,code_prior=np.zeros(64))
            actual=terminal_decode(*args,code_prior=np.zeros(64),edge_count_observer=counts.append)
            same_state(actual,expected)
            self.assertEqual(counts,[int(np.count_nonzero(abs(H)>=1e-4))])

    def test_actual_early_stop_has_no_ce_or_terminal_counts(self):
        rng=np.random.default_rng(5)
        observed=dict(self.observed,y=rng.normal(size=32)+1j*rng.normal(size=32))
        value=self.receiver.run(observed,audit=False,code_feedback=self.feedback(stop_on_valid_codeword=True),
            terminal_check_prior='retain',bp_schedule=UniformBPSchedule(12))
        self.assertFalse(value['terminal_executed'])
        counts=receiver_resources(value)
        self.assertEqual(counts['CE_solves'],0)
        self.assertEqual(counts['terminal_BP_calls'],0)
        self.assertEqual(counts['terminal_BP_iterations'],0)
        self.assertEqual(value['bp_schedule']['final_bp_edges'],0)


if __name__ == '__main__':
    unittest.main()
