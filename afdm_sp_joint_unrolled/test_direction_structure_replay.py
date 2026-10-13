"""Explicit wiring fixtures; these are not real N1024 structure evidence."""
import unittest
from unittest.mock import patch
import numpy as np
from afdm_sp_joint_unrolled.direction_structure_replay import run_arm

class ToySystem:
    k_max_cap=2
    def gen_h_daft(self,g,delays,dopplers):
        H=np.zeros((6,6),complex)
        ids=delays*5+dopplers+2
        for i,v in zip(ids,g):H[i,i]=v
        return H

class StructureReplayTests(unittest.TestCase):
    def test_shared_fit_input_and_terminal_routing(self):
        I=np.array([0,1,2,3]);L=np.array([[1,0],[.5j,0],[0,1],[0,.4j]],complex)
        pilot=np.ones(6,complex)*.5;data=np.ones(6,complex)*(.5+.5j)
        Htrue=np.eye(6,dtype=complex);noise=np.ones(6,complex)*.01
        s={'y':Htrue@(pilot+data)+np.sqrt(.1)*noise,'pilot':pilot,'data':data,'noise':noise,
           'Htrue':Htrue,'sigma2_terminal':np.array(.1),'sigma2_thermal':np.array(.1),
           'constellation':np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]),'info':np.zeros(3,int)}
        prepared={'I':I,'basis':L,'Phi_I':np.eye(6,dtype=complex)[:,:4]*.5,'snapshot':s}
        observed=[]
        def terminal(z,H,sigma,const,code,**kwargs):
            observed.append((z.copy(),H.copy(),sigma))
            return {'info_hat':np.zeros(3,int),'decoded':np.zeros(6,int)}
        for arm in ('free','group','link','sham'):
            events=[]
            with patch('afdm_sp_joint_unrolled.direction_structure_replay.terminal_decode',side_effect=terminal):
                result=run_arm(prepared,ToySystem(),{},arm,device='cpu',before_call=lambda *x:events.append(x))
            self.assertEqual(events,[('CE',arm),('terminal',arm)])
            self.assertEqual(result['atom_ids'],I.tolist())
            z,H,sigma=observed[-1]
            np.testing.assert_allclose(z,s['y']-H@pilot)
            self.assertEqual(sigma,.1)
            np.testing.assert_array_equal(H[4:,:],np.zeros((2,6)))
            self.assertFalse(result['candidate_eligible'])
            self.assertLess(result['residual']['relative_vector_closure'],1e-10)

if __name__=='__main__':unittest.main()
