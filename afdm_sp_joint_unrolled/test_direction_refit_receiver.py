"""Mock routing contracts only; real receiver validation is a separate gate."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver

class RefitRoutingTests(unittest.TestCase):
    def fixture(self):
        cfg=SimpleNamespace(N=2,rho=.5,dtype=torch.complex64,rdtype=torch.float32)
        output={'H_est':torch.eye(2,dtype=torch.complex64),'x_soft':torch.zeros(2,dtype=torch.complex64),
                'sigma2_final':torch.tensor(1.),'support_delays':torch.tensor([0]),
                'support_dopplers':torch.tensor([0]),'gains':torch.ones(1), 'capacity_trace':[]}
        class Model:
            def __call__(self,*args,**kwargs): return output
        model=Model(); model.cfg=cfg
        r=ObservedReceiver.__new__(ObservedReceiver)
        r.model=model;r.code={};r.device=torch.device('cpu');r.sources={}
        return r,output

    def run_fixture(self,callback):
        r,o=self.fixture(); const=.5*np.array([1+1j,1-1j,-1+1j,-1-1j])
        with patch('afdm_sp_joint_unrolled.direction_receiver.validate_observed',return_value=(np.ones(2,complex),np.full(2,.5,complex),1.,const)), \
             patch('afdm_sp_joint_unrolled.direction_receiver.InitialEstimator',return_value=SimpleNamespace(record={})), \
             patch('afdm_sp_joint_unrolled.direction_receiver.terminal_decode',return_value={'graphs':[]}) as terminal:
            result=r.run({},channel_refit=callback)
        return result,o,terminal

    def test_refit_consumed_once_and_parent_state_preserved(self):
        seen={}
        def callback(**kwargs):
            seen.update({k:v.copy() if isinstance(v,np.ndarray) else v for k,v in kwargs.items()})
            kwargs['H'][:]=7;kwargs['gains'][:]=9
            return {'H':2*np.eye(2,dtype=complex),'gains':np.array([2+0j]),'diagnostics':{'arm':'fixture'}}
        result,original,terminal=self.run_fixture(callback)
        self.assertEqual(set(seen),{'y','pilot','H','x_soft','support','gains','sigma_base'})
        terminal.assert_called_once()
        np.testing.assert_array_equal(terminal.call_args.args[0],np.zeros(2))
        np.testing.assert_array_equal(terminal.call_args.args[1],2*np.eye(2))
        np.testing.assert_array_equal(result['H'],2*np.eye(2))
        np.testing.assert_array_equal(result['gains'],[2])
        np.testing.assert_array_equal(result['channel_refit']['H_before'],np.eye(2))
        np.testing.assert_array_equal(result['channel_refit']['gains_before'],[1])
        np.testing.assert_array_equal(original['H_est'].numpy(),np.eye(2))
        self.assertEqual(result['sigma2_terminal'],1.)
        self.assertEqual(result['support'],[2])

    def test_bad_refit_rejected(self):
        for payload in ({'H':np.eye(2),'gains':np.ones(2),'diagnostics':{}},
                        {'H':np.full((2,2),np.nan),'gains':np.ones(1),'diagnostics':{}},
                        {'H':np.eye(2),'gains':np.ones(1),'diagnostics':{},'truth':1}):
            with self.assertRaises(ValueError): self.run_fixture(lambda **kwargs:payload)

if __name__=='__main__':unittest.main()
