"""Independent full-coordinate fits and real tiny receiver exchange consumers."""
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
import torch
from .light_gap_support_exchange import select_exchange, prune_support_memory, CodeSupportExchange
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .test_supplement_feedback_adapter import tiny_adapter


def independent_fit(a,y,ids,old_ids,old,lam,gamma):
    q=a.shape[1];embed=np.eye(q)[:,ids];center=np.zeros(q,dtype=complex);center[old_ids]=old
    aug=np.vstack((a[:,ids],np.sqrt(gamma)*np.eye(len(ids)),np.sqrt(lam)*embed))
    target=np.concatenate((y,np.zeros(len(ids)),np.sqrt(lam)*center))
    gains=np.linalg.lstsq(aug,target,rcond=None)[0]
    objective=float(np.vdot(aug@gains-target,aug@gains-target).real)
    return gains,objective


class ExchangeTests(unittest.TestCase):
    def test_every_complete_action_and_schur_match_independent_augmented_fit(self):
        rng=np.random.default_rng(8172);a=rng.normal(size=(12,7))+1j*rng.normal(size=(12,7))
        pilot=rng.normal(size=(12,7))+1j*rng.normal(size=(12,7));y=2*a[:,5]+.2*a[:,0]
        support=[0,1,3];previous=np.array([.3+1j,1.+.3j,-.6j]);lam=7.;variance=np.full(12,.04)
        for nomination in ['code','pilot']:
            r=select_exchange(torch.tensor(a),torch.tensor(pilot),torch.tensor(y),support,
                torch.tensor(previous),torch.tensor(variance),torch.tensor(lam),nomination=nomination,candidate_count=4)
            _,baseline=independent_fit(a,y,support,support,previous,lam,variance.sum())
            self.assertAlmostEqual(float(r['baseline_objective']),baseline,places=9)
            matrix=a if nomination=='code' else pilot;gam=variance.sum() if nomination=='code' else 0.
            _,nom_base=independent_fit(matrix,y,support,support,previous,lam,gam)
            for j,atom in enumerate(r['inactive_ids']):
                _,added=independent_fit(matrix,y,support+[atom],support,previous,lam,gam)
                self.assertAlmostEqual(float(r['nomination_scores'][j]),nom_base-added,places=9)
            for j,(add,drop,position) in enumerate(r['actions']):
                ids=list(support);ids[position]=add
                gains,obj=independent_fit(a,y,ids,support,previous,lam,variance.sum())
                np.testing.assert_allclose(r['action_gains'][j],gains,rtol=1e-10,atol=1e-10)
                self.assertAlmostEqual(float(r['action_objectives'][j]),obj,places=9)
                self.assertGreater(lam*abs(previous[position])**2,.1)
            self.assertTrue(r['accepted']);self.assertEqual(len(r['selected_ids']),3)
            self.assertLess(float(r['selected_objective']),baseline)

    def test_rejection_preserves_state_and_memory_removes_dropped_shift(self):
        a=torch.eye(5,dtype=torch.complex128);old=torch.zeros(2,dtype=a.dtype)
        r=select_exchange(a,a,torch.zeros(5,dtype=a.dtype),[0,1],old,torch.ones(5),torch.tensor(1.),candidate_count=2)
        self.assertFalse(r['accepted']);self.assertEqual(r['selected_ids'],[0,1]);self.assertTrue(torch.equal(old,r['mapped_previous']))
        h=torch.arange(64).reshape(8,8).to(torch.complex128);out=prune_support_memory(h,[2,4],1)
        for row in range(8):
            for col in range(8):self.assertEqual(out[row,col],h[row,col] if (row-col)%8 in [1,3] else 0)
        for bad in [dict(candidate_count=0),dict(iteration=True),dict(nomination='truth')]:
            with self.assertRaises(ValueError):CodeSupportExchange(**bad)
        with self.assertRaises(ValueError):CodeSupportExchange().begin(SimpleNamespace(N=4,l_max=2,k_max=1),(1,2),1)

    def test_real_tiny_adapter_and_bp_consume_committed_state(self):
        with tempfile.TemporaryDirectory() as cache:
            code=build_code(n=128,d_v=2,d_c=4,seed=91,cache_dir=cache)
            adapter=tiny_adapter(code);cfg=adapter.receiver.model.cfg;cfg.N=64;cfg.c1=5/128
            adapter.estimator.lstsq_driver='gels'
            rng=np.random.default_rng(623)
            observed=dict(y=rng.normal(size=64)+1j*rng.normal(size=64),pilot=np.full(64,.5+0j),sigma2=.2,
                constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            controller=CodeSupportExchange(iteration=1,candidate_count=3,retain_states=True)
            result=adapter.run(observed,audit=True,code_feedback=CodeFeedback(code,checkpoint=0),
                dals_mode='jsoft',ce_support_exchange=controller)
            r=result['support_exchange'];ce=result['dals'][0]
            self.assertTrue(r['accepted']);self.assertEqual(len(r['support_before']),len(r['selected_ids']))
            self.assertEqual(r['selected_ids'],(ce['support_delays']*5+ce['support_dopplers']+2).tolist())
            np.testing.assert_array_equal(r['consumed_gains'],ce['g_solution'])
            np.testing.assert_allclose(r['selected_gains'],ce['g_solution'],rtol=1e-11,atol=1e-11)
            expected=prune_support_memory(torch.tensor(ce['H']),r['selected_ids'],2).numpy()
            np.testing.assert_array_equal(r['pruned_memory'],expected)
            dropped=set(r['support_before'])-set(r['selected_ids'])
            cols=np.arange(64)
            for atom in dropped:np.testing.assert_array_equal(r['consumed_H'][(cols+atom-2)%64,cols],0)
            self.assertTrue(np.isfinite(result['llr']).all());self.assertEqual(len(result['decoded']),128)
            with self.assertRaises(ValueError):adapter.run(observed,dals_mode='jsoft',ce_support_exchange=CodeSupportExchange(iteration=1))
            with self.assertRaises(ValueError):adapter.run(observed,code_feedback=CodeFeedback(code,checkpoint=0),ce_support_exchange=CodeSupportExchange(iteration=1))


if __name__=='__main__':unittest.main()
