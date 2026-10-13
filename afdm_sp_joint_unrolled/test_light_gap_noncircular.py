"""Independent real-Gaussian likelihood and actual BP cavity contracts."""
import unittest
import tempfile
import numpy as np
import torch
from .mp_detect_bp_torch import mp_detect_bp_torch


class NoncircularTests(unittest.TestCase):
    def setUp(self):
        self.const=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        self.h=np.array([[1,.3+.2j,0],[.2j,1,.25],[.2,0,1]],dtype=complex)
        self.y=np.array([.4-.7j,.1+.7j,-.6+.1j])

    def test_information_metric_equals_real_two_dimensional_gaussian(self):
        from .mp_detect_bp_torch import _improper_natural
        mu=.2-.3j;v=.4;c=.12+.07j
        a,b,t=_improper_natural(torch.tensor(mu,dtype=torch.complex128),torch.tensor(v,dtype=torch.float64),torch.tensor(c,dtype=torch.complex128))
        log=-float(a)*abs(self.const)**2+(complex(b).conjugate()*self.const**2).real+2*(complex(t).conjugate()*self.const).real
        covariance=.5*np.array([[v+c.real,c.imag],[c.imag,v-c.real]])
        e=np.column_stack(((self.const-mu).real,(self.const-mu).imag))
        direct=-.5*np.einsum('ni,ij,nj->n',e,np.linalg.inv(covariance),e)
        np.testing.assert_allclose(log-log[0],direct-direct[0],atol=1e-12,rtol=1e-12)
        with self.assertRaises(ValueError):_improper_natural(torch.tensor(mu),torch.tensor(.1),torch.tensor(.2j))

    def test_zero_pseudovariance_reduces_to_same_circular_path(self):
        for temperature in (1.,2.):
            old=[];new=[]
            control=mp_detect_bp_torch(self.y,self.h,.2,self.const,return_soft=True,code_prior=np.zeros(6),
                message_temperature=temperature,message_observer=old.append)
            result=mp_detect_bp_torch(self.y,self.h,.2,self.const,return_soft=True,code_prior=np.zeros(6),
                message_temperature=temperature,message_observer=new.append,noncircular=True,pseudovariance_scale=0.)
            for a,b in zip(control,result):np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(old[0]['channel_llr'],new[0]['channel_llr'],rtol=1e-12,atol=1e-12)

    def test_scalar_likelihood_and_genuine_edge_cavities(self):
        observed=[]
        mp_detect_bp_torch(np.array([.3-.4j]),np.eye(1,dtype=complex),.2,self.const,return_soft=True,
            code_prior=np.zeros(2),noncircular=True,message_observer=observed.append)
        np.testing.assert_allclose(observed[0]['channel_llr'],[3.,-4.],atol=1e-12)
        events=[]
        mp_detect_bp_torch(self.y,self.h,.2,self.const,return_soft=True,code_prior=np.zeros(6),
            n_iter=3,noncircular=True,cavity_observer=events.append)
        self.assertEqual(len(events),3)
        for event in events:
            r=event['row'].numpy();h=event['h'].numpy();v=event['incoming_variance'].numpy();c=event['incoming_pseudovariance'].numpy()
            V=np.full(3,.2);C=np.zeros(3,dtype=complex)
            np.add.at(V,r,abs(h)**2*v);np.add.at(C,r,h**2*c)
            np.testing.assert_allclose(event['cavity_variance'],V[r]-abs(h)**2*v,atol=1e-12)
            np.testing.assert_allclose(event['cavity_pseudovariance'],C[r]-h**2*c,atol=1e-12)
            p=event['projection_probabilities'].numpy();mu=p@self.const
            np.testing.assert_allclose(event['projection_pseudovariance'],p@self.const**2-mu**2,atol=1e-12)
            self.assertTrue(np.all(abs(C[r]-h**2*c)<V[r]-abs(h)**2*v))

    def test_terminal_finite_marginal_demap_and_ldpc(self):
        from .direction_receiver import terminal_decode
        from .e1_ldpc import build_code
        with tempfile.TemporaryDirectory() as cache:
            code=build_code(n=32,d_v=2,d_c=4,seed=91,cache_dir=cache)
            y=np.linspace(-.5,.6,16)+1j*np.linspace(.7,-.2,16);h=np.eye(16,dtype=complex)
            old=terminal_decode(y,h,.2,self.const,code)
            result=terminal_decode(y,h,.2,self.const,code,bp_noncircular=True)
            np.testing.assert_allclose(result['raw_llr'],np.r_[2*y.real/.2,2*y.imag/.2],atol=1e-12)
            np.testing.assert_allclose(result['llr'],old['llr'],atol=1e-12)
            np.testing.assert_array_equal(result['decoded'],old['decoded'])
            self.assertIn('finite constellation',result['llr_statistic'])


if __name__=='__main__':unittest.main()
