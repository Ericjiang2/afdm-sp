"""Fixture unit contracts, not real BP/LDPC or A2 equivalence evidence."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import torch
from . import supplement_profile as profile


class ProfileContracts(unittest.TestCase):
    def args(self, **changes):
        value=dict(start=0,stop=1,snr=8,arms='["A2","B0","old-Bstar"]',
            prior=Path('prior.pt'),deadline_unix=time.time()+60,
            max_full_calls=3,max_terminal_calls=3,max_ce_calls=3)
        value.update(changes)
        return SimpleNamespace(**value)

    def test_budget_domains(self):
        self.assertEqual(profile.validate_args(self.args()),list(profile.ARMS))
        for changes in (dict(stop=33),dict(snr=9),dict(prior=None),dict(arms='["A2","A2"]'),
                        dict(max_full_calls=2),dict(max_ce_calls=25),dict(max_terminal_calls=0),
                        dict(deadline_unix=float('inf'))):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                profile.validate_args(self.args(**changes))

    def test_operator_failure_is_retained_and_patch_restored(self):
        module=SimpleNamespace(operation=Mock(side_effect=RuntimeError('expected')))
        original=module.operation
        timer=profile.OperatorProfile(torch.device('cpu'))
        timer.wrap(module,'operation','test')
        with self.assertRaises(RuntimeError): module.operation()
        timer.__exit__(None,None,None)
        self.assertIs(module.operation,original)
        self.assertEqual(timer.rows[0]['status'],'failed')
        self.assertGreaterEqual(timer.rows[0]['seconds'],0)

    def test_a2_uses_estimated_h0_and_fixed40_not_truth(self):
        model=Mock()
        model.cfg=SimpleNamespace(N=2,c1=0.,c2=0.,l_max=1,k_max=2,rho=.5)
        model.use_soft_decisions=True
        system=Mock()
        estimate=np.eye(2)*7
        system.gen_h_daft.return_value=estimate
        wrapper=profile.A2Model(model,system,Mock())
        y=torch.tensor([1+1j,2+0j]);p=torch.tensor([1+0j,1+0j])
        phi=np.eye(2,dtype=complex)
        wrapper.observed=dict(y=y.numpy().astype(np.complex128),pilot=p.numpy().astype(np.complex128))
        with patch.object(profile.afb,'construct_sensing_matrix',return_value=phi), \
             patch.object(profile.afb,'omp_sparse',return_value=(None,[0,1])) as omp, \
             patch.object(profile,'make_genie_lambda',return_value='scorer') as scorer:
            wrapper(y,p,torch.tensor(1.),torch.ones(4),initial_estimator=Mock(),enable_support_repair=False)
        self.assertEqual(omp.call_args.args[2],40)
        self.assertIs(scorer.call_args.args[0],estimate)
        model.cand_active_rel.set_refine_config.assert_called_once_with(2,96,True,2)
        kw=model.call_args.kwargs
        self.assertTrue(kw['enable_support_repair'])
        self.assertEqual((kw['active_support_cap'],kw['receiver_extension']),(40,0))
        self.assertNotIn('initial_estimator',kw)

    def test_shared_fte_limits_and_old_f_only_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            legacy=dict(max_full_calls=2,config_sha256='f'*64)
            profile.reserve(root/'legacy',legacy)
            contract=dict(max_full_calls=1,config_sha256='a'*64,
                          calls_reserved=dict(F=1,T=256,E=128))
            profile.reserve_profile(root/'first',contract)
            for kind in ('T','E'):
                second=dict(contract,calls_reserved=dict(F=1,T=0,E=0))
                second['calls_reserved'][kind]=1
                with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'cumulative'):
                    profile.reserve_profile(root/('overflow-'+kind),second)
            with self.assertRaises(FileExistsError):
                profile.reserve_profile(root/'first',dict(contract,calls_reserved=dict(F=1,T=0,E=0)))

    def test_legacy_profile_te_recovered_from_bound_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'old';out.mkdir()
            contract=dict(max_full_calls=3,calls_reserved=dict(F=3,T=9,E=6))
            digest=profile.hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
            contract.update(config_sha256=digest,ledger='legacy ledger')
            (out/'contract.json').write_text(json.dumps(contract))
            row=dict(out=str(out),max_full_calls=3,contract_sha256=digest)
            self.assertEqual(profile.reservation_calls(row),dict(F=3,T=9,E=6))
            contract['calls_reserved']['T']=10
            (out/'contract.json').write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError,'contract'):
                profile.reservation_calls(row)

    def test_error_score_rejects_broadcast_and_nonbinary(self):
        truth=dict(info=np.zeros(2,dtype=np.uint8),coded=np.zeros(4,dtype=np.uint8))
        value=dict(info_hat=np.zeros(2,dtype=np.uint8),decoded=np.zeros(4,dtype=np.uint8),
                   x_hard=np.ones(2,dtype=complex))
        self.assertEqual(profile.score_errors(value,truth)['FER'],0)
        for key,bad in [('info_hat',np.zeros((2,1))),('decoded',np.zeros((4,1))),
                        ('info_hat',np.array([0,2])),('x_hard',np.ones((2,1)))]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                profile.score_errors(dict(value,**{key:bad}),truth)

    def test_content_binding_detects_prior_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            args=SimpleNamespace(**{k:root/k for k in ('prior','protocol','checkpoint')})
            for path in vars(args).values():path.write_bytes(b'initial')
            contract={k+'_sha256':profile.sha(path) for k,path in vars(args).items()}
            contract['source_sha256']={'file':'hash'}
            with patch.object(profile,'sources',return_value={'file':'hash'}):
                profile.assert_content_unchanged(args,contract)
                args.prior.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'prior'):
                    profile.assert_content_unchanged(args,contract)

    def test_generation_failure_retains_identity_without_charging_full_call(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'run'
            args=self.args(out=out,arms='["B0"]',prior=None,device='cpu',
                           checkpoint=Path('checkpoint'),protocol=Path('protocol'))
            with patch.object(profile,'sha',return_value=profile.CHECKPOINT_HASH), \
                 patch.object(profile,'sources',return_value={}), \
                 patch.object(profile,'build_code',return_value={'G':np.eye(2),'H':np.eye(2)}), \
                 patch.object(profile,'SupplementData') as data, \
                 patch.object(profile,'_make_config_a'), \
                 patch.object(profile,'build_receiver'), \
                 patch.object(profile,'ObservedReceiver'):
                data.return_value.make_frame.side_effect=RuntimeError('generation failed')
                with self.assertRaisesRegex(RuntimeError,'generation failed'):
                    profile.execute(args)
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['active_attempt']['kind'],'generation')
            self.assertEqual(failure['active_attempt']['block'],0)
            self.assertEqual(failure['calls'],dict(F=0,T=0,E=0))
            self.assertTrue((out/'generation-000-started.json').exists())

    def test_source_mutation_inside_receiver_rejects_completed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'run'
            args=self.args(out=out,arms='["B0"]',prior=None,device='cpu',
                           checkpoint=Path('checkpoint'),protocol=Path('protocol'))
            frame=SimpleNamespace(metadata={'block':0,'input_hashes':{'y':'hash'}},observed={})
            with patch.object(profile,'sha',return_value=profile.CHECKPOINT_HASH), \
                 patch.object(profile,'sources',return_value={}) as source, \
                 patch.object(profile,'build_code',return_value={'G':np.eye(2),'H':np.eye(2)}), \
                 patch.object(profile,'SupplementData') as data, \
                 patch.object(profile,'_make_config_a'), \
                 patch.object(profile,'build_receiver'), \
                 patch.object(profile,'ObservedReceiver') as receiver:
                data.return_value.make_frame.return_value=frame
                def mutate(*a,**kw):
                    source.return_value={'changed':'hash'}
                    return {}
                receiver.return_value.run.side_effect=mutate
                with self.assertRaisesRegex(ValueError,'source snapshot changed'):
                    profile.execute(args)
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['calls']['F'],1)
            self.assertEqual(failure['active_attempt']['kind'],'F')
            self.assertFalse(list(out.glob('sample-*.json')))

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'run';out.mkdir()
            sentinel=out/'sentinel';sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):
                profile.execute(self.args(out=out))
            self.assertEqual(sentinel.read_text(),'keep')

    def test_validation_failure_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'run'
            with self.assertRaises(ValueError):
                profile.execute(self.args(out=out,max_full_calls=0))
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['calls'],dict(F=0,T=0,E=0))
            self.assertEqual(failure['exitcode'],1)
            self.assertFalse((out/'complete.json').exists())


if __name__=='__main__':
    unittest.main()
