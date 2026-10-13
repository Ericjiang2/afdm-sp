"""Mock fixtures validate callback routing only, not receiver E2E performance."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.direction_cancel_receiver import CancellationTransform


class CallbackContractTests(unittest.TestCase):
    def test_single_terminal_and_copied_information_boundary(self):
        cfg=SimpleNamespace(N=2,rho=.5,dtype=torch.complex64,rdtype=torch.float32)
        output={'H_est':torch.eye(2,dtype=torch.complex64),'x_soft':torch.zeros(2,dtype=torch.complex64),
                'sigma2_final':torch.tensor(1.),'support_delays':torch.tensor([0]),
                'support_dopplers':torch.tensor([0]),'gains':torch.ones(1), 'capacity_trace':[]}
        class FixtureModel:
            def __call__(self,*args,**kwargs):return output
        model=FixtureModel();model.cfg=cfg
        receiver=ObservedReceiver.__new__(ObservedReceiver)
        receiver.model=model;receiver.code={};receiver.device=torch.device('cpu');receiver.sources={}
        y=np.ones(2,dtype=complex);pilot=np.zeros(2,dtype=complex)
        const=.5*np.array([1+1j,1-1j,-1+1j,-1-1j])
        captured={}
        def callback(**kwargs):
            captured.update(kwargs)
            kwargs['H'][:]=3
            return {'z':np.array([2.,4.]),'H':kwargs['H'],'sigma_out':2.,'diagnostics':{},'B':np.zeros((2,1))}
        with patch('afdm_sp_joint_unrolled.direction_receiver.validate_observed',return_value=(y,pilot,1.,const)), \
             patch('afdm_sp_joint_unrolled.direction_receiver.InitialEstimator',return_value=SimpleNamespace(record={})), \
             patch('afdm_sp_joint_unrolled.direction_receiver.terminal_decode',return_value={'graphs':[]}) as decode:
            result=receiver.run({},terminal_transform=callback)
        self.assertEqual(set(captured),{'y','pilot','H','x_soft','support','sigma_base'})
        decode.assert_called_once()
        np.testing.assert_array_equal(decode.call_args.args[0],[2.,4.])
        self.assertEqual(decode.call_args.args[2],2.)
        np.testing.assert_array_equal(result['H'],np.eye(2))
        self.assertEqual(result['sigma2_terminal_base'],1.)
        self.assertEqual(result['sigma2_terminal'],2.)

    def test_callback_support_and_signature_reject_truth(self):
        system=SimpleNamespace(N_total=4,c1=3/8,c2=0.,l_max_cap=1,k_max_cap=1)
        callback=CancellationTransform(system,'scalar')
        inputs=dict(y=np.ones(4),pilot=np.ones(4),H=np.eye(4),x_soft=np.zeros(4),sigma_base=1.)
        for support in ([0,0],[-1],[6],[.5]):
            with self.assertRaises(ValueError):callback(**inputs,support=support)
        with self.assertRaises(TypeError):callback(**inputs,support=[],Htrue=np.eye(4))
        result=callback(**inputs,support=[])
        self.assertEqual(result['B'].shape,(4,0))
        self.assertEqual(result['diagnostics']['truth_access'],'none')


if __name__=='__main__':unittest.main()
