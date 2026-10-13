"""The COO representation must reuse every numerical BP message path."""
import unittest
from unittest.mock import patch
import numpy as np
import torch
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch as bp


class SparseBPTests(unittest.TestCase):
    def setUp(self):
        self.H = torch.tensor([[.8+.1j, .2-.1j, 0], [0, .6-.2j, .15j],
                               [.1, 0, 1.1+.1j]], dtype=torch.complex64)
        self.y = torch.tensor([.6+.2j, -.4+.1j, .1-.5j], dtype=torch.complex64)
        self.const = torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        self.prior = torch.tensor([.2, -.4, .6, -.3, .7, -.9])

    def equal(self, a, b):
        if isinstance(a, torch.Tensor):
            self.assertEqual(a.dtype, b.dtype)
            self.assertTrue(torch.equal(a, b))
        elif isinstance(a, np.ndarray):
            np.testing.assert_array_equal(a, b)
        elif isinstance(a, dict):
            self.assertEqual(set(a), set(b))
            for k in a:
                if k != 'graph_observer_seconds': self.equal(a[k], b[k])
        elif isinstance(a, (list, tuple)):
            self.assertEqual(len(a), len(b))
            for x, y in zip(a, b): self.equal(x, y)
        else:
            self.assertEqual(a, b)

    def compare(self, H=None, **kwargs):
        H = self.H if H is None else H
        dense_graph, sparse_graph, dense_msg, sparse_msg = [], [], [], []
        common = dict(n_iter=3, return_soft=True, **kwargs)
        if common.get('code_prior') is not None:
            common['message_observer'] = dense_msg.append
        dense = bp(self.y, H, .2, self.const, graph_observer=dense_graph.append, **common)
        if common.get('code_prior') is not None:
            common['message_observer'] = sparse_msg.append
        sparse = bp(self.y, H.to_sparse(), .2, self.const, graph_observer=sparse_graph.append, **common)
        self.equal(dense, sparse)
        self.equal(dense_graph, sparse_graph)
        self.equal(dense_msg, sparse_msg)

    def test_gaussian_soft_and_graph_exact_for_both_dtypes(self):
        for dtype in (torch.complex64, torch.complex128):
            with self.subTest(dtype=dtype): self.compare(self.H.to(dtype))

    def test_explicit_prior_channel_and_qpsk_projection_exact(self):
        for prior in (torch.zeros(6), self.prior):
            for projection in (None, 'qpsk_tanh'):
                with self.subTest(projection=projection, prior=prior.tolist()):
                    self.compare(code_prior=prior, edge_projection=projection, message_temperature=2.)

    def test_noncircular_cavity_exact(self):
        for use_pseudo in (False, True):
            records = []
            outputs = []
            for H in (self.H, self.H.to_sparse()):
                cavity = []
                outputs.append(bp(self.y, H, .2, self.const, n_iter=3, return_soft=True,
                    code_prior=self.prior, noncircular=use_pseudo, cavity_observer=cavity.append))
                records.append(cavity)
            self.equal(outputs[0], outputs[1]);self.equal(records[0], records[1])

    def test_empty_graph_threshold_boundary_and_explicit_zero_storage(self):
        self.compare(torch.zeros_like(self.H), code_prior=self.prior)
        self.compare(threshold=float(abs(complex(self.H[0, 0]))))
        indices = torch.tensor([[0, 1, 2], [0, 1, 2]])
        values = torch.tensor([0., .5, 1.], dtype=torch.complex64)
        H = torch.sparse_coo_tensor(indices, values, (3, 3)).coalesce()
        self.equal(bp(self.y, H, .2, self.const), bp(self.y, H.to_dense(), .2, self.const))

    def test_empty_dimension_and_numpy_return(self):
        for soft in (False, True):
            y=np.empty(0,dtype=complex);H=torch.zeros((0,0),dtype=torch.complex64)
            self.equal(bp(y,H,.2,self.const,return_soft=soft),
                       bp(y,H.to_sparse(),.2,self.const,return_soft=soft))
        self.equal(bp(self.y.numpy(),self.H,.2,self.const,return_soft=True),
                   bp(self.y.numpy(),self.H.to_sparse(),.2,self.const,return_soft=True))

    def test_convergence_messages_exact(self):
        records=[]
        for H in (self.H,self.H.to_sparse()):
            capture=[];bp(self.y,H,.2,self.const,n_iter=3,convergence_observer=capture.append)
            records.append(capture)
        self.equal(*records)

    def test_sparse_without_graph_observer_never_materializes_dense(self):
        H=self.H.to_sparse()
        with patch.object(torch.Tensor, 'to_dense', side_effect=AssertionError('dense allocation')):
            bp(self.y,H,.2,self.const,n_iter=3,code_prior=self.prior,return_soft=True)

    def test_invalid_sparse_layout_shape_and_values_rejected(self):
        indices=torch.tensor([[0,0],[0,0]])
        bad=[self.H.to_sparse_csr(),
             torch.sparse_coo_tensor(indices,torch.ones(2,dtype=torch.complex64),(3,3)),
             torch.zeros((3,2),dtype=torch.complex64).to_sparse(),
             torch.sparse_coo_tensor(torch.tensor([[0],[0]]),torch.tensor([complex('nan')]),(3,3)).coalesce(),
             torch.sparse_coo_tensor(torch.tensor([[0,0],[1,0]]),torch.ones(2),(3,3),is_coalesced=True),
             torch.sparse_coo_tensor(torch.tensor([[3],[0]]),torch.ones(1),(3,3),is_coalesced=True)]
        for H in bad:
            with self.subTest(layout=H.layout,shape=H.shape), self.assertRaises(ValueError):
                bp(self.y,H,.2,self.const)

    def test_nonpositive_or_invalid_sparse_threshold_rejected(self):
        for threshold in (0.,-1.,float('nan'),float('inf'),True,1j):
            with self.subTest(threshold=threshold),self.assertRaises(ValueError):
                bp(self.y,self.H.to_sparse(),.2,self.const,threshold=threshold)


if __name__ == '__main__':
    unittest.main()
