"""Campaign contracts and real toy numerical checks; no N1024 receiver run."""
import hashlib
import copy
import json
import itertools
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from afdm_sp_joint_unrolled.direction_data import (
    CampaignData, campaign_rng, validate_observed, CODE_HASH)
from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
from afdm_sp_joint_unrolled.e1_ldpc import (
    build_code, encode, qpsk_map, demap_llr, decode_llr, extract_info)
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch

PROTOCOL = Path(__file__).resolve().parents[1]/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/campaign-protocol.json'


def exact_qpsk_llr(y,H,sigma2,constellation):
    """Independent exhaustive likelihood, uniform prior, all I bits then Q bits."""
    symbols = np.array(list(itertools.product(constellation,repeat=H.shape[1])))
    logw = -np.sum(abs(y[None,:]-symbols@H.T)**2,axis=1)/sigma2
    bits = np.concatenate((symbols.real<0,symbols.imag<0),axis=1)
    def logsum(v):
        m = np.max(v)
        return m+np.log(np.exp(v-m).sum())
    return np.array([logsum(logw[~bits[:,i]])-logsum(logw[bits[:,i]])
                     for i in range(2*H.shape[1])])


def dense_likelihood_bp_audit():
    """Small exact-vs-approximate raw report for the NUM-01 evidence writer."""
    const=np.array([1+1j,1-1j,-1+1j,-1-1j])/2
    H=np.array([[1.,.2j],[.15,1.-.1j]])
    y=H@const[[0,3]]+np.array([.03-.08j,.04+.02j])
    sigma=.2
    exact=exact_qpsk_llr(y,H,sigma,const)
    hard,mu,var=mp_detect_bp_torch(y,H,sigma,const,device='cpu',return_soft=True,return_numpy=True)
    _,rot_mu,rot_var=mp_detect_bp_torch(1j*y,1j*H,sigma,const,
                                     device='cpu',return_soft=True,return_numpy=True)
    llr=demap_llr(mu,var,.5)
    rotated=demap_llr(rot_mu,rot_var,.5)
    complex_json=lambda a:{'real':a.real.tolist(),'imag':a.imag.tolist()}
    return {'evidence_kind':'real-small-dense-BP-versus-exact-enumeration',
            'N':2,'sigma2':sigma,'H':complex_json(H),'y':complex_json(y),
            'exact_llr':exact.tolist(),'exact_rotated_llr':exact_qpsk_llr(1j*y,1j*H,sigma,const).tolist(),
            'BP_mu':complex_json(mu),'BP_var':var.tolist(),'BP_hard':complex_json(hard),
            'BP_llr':llr.tolist(),'BP_rotated_llr':rotated.tolist(),
            'BP_minus_exact_clipped_llr':(llr-np.clip(exact,-20,20)).tolist(),
            'scope':'Approximate dense BP need not equal exact joint likelihood; no N1024 claim.'}


class DataContracts(unittest.TestCase):
    def test_namespaces_components_and_repetition(self):
        fingerprints = set()
        for split in ('engineering','design','mechanism','confirm'):
            for component in ('channel','data','noise','order'):
                a = campaign_rng(split,0,component).integers(0,2**32,size=8)
                np.testing.assert_array_equal(a,campaign_rng(split,0,component).integers(0,2**32,size=8))
                fingerprints.add(a.tobytes())
        self.assertEqual(len(fingerprints),16)
        for split in ('D_test','D_dev',1):
            with self.assertRaises(ValueError):campaign_rng(split,0,'noise')
        with self.assertRaises(ValueError):campaign_rng('design',-1,'noise')

    def test_schema_rejects_truth_before_receiver(self):
        observed = dict(y=np.ones(2,complex),pilot=np.ones(2,complex),sigma2=.1,
                        constellation=np.array([1+1j,1-1j,-1+1j,-1-1j])/2)
        validate_observed(observed,2)
        for key in ('H','Htrue','info','params','data','noise'):
            with self.assertRaises(ValueError):validate_observed(dict(observed,**{key:None}),2)
        for sigma in (0.,-1.,np.nan,np.inf):
            with self.assertRaises(ValueError):validate_observed(dict(observed,sigma2=sigma),2)

    def test_split_bounds_and_confirmation_lock(self):
        # Request gate uses the real frozen protocol; avoids constructing LDPC here.
        data = CampaignData.__new__(CampaignData)
        data.protocol_sha256 = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
        data.freeze_token = None
        data._validate_request('design',191,8)
        for args in [('design',192,8),('mechanism',256,8),('design',0,7),('D_test',0,8),('confirm',0,8)]:
            with self.assertRaises(ValueError):data._validate_request(*args)
        data.freeze_token = {'campaign_id':'afdm-direction-20260908-v1',
            'protocol_sha256':data.protocol_sha256,'freeze01_completed':True,
            'frozen_manifest_sha256':'a'*64}
        with self.assertRaises(ValueError):data._validate_request('confirm',0,8)

    def test_confirmation_requires_actual_bound_manifest(self):
        data=CampaignData.__new__(CampaignData)
        data.protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            auth=root/'authorization.json'
            auth.write_text(json.dumps({'source':'unit fixture, NOT scientific authorization',
                                       'authorized':['fixture-only confirmation gate']}))
            manifest={'campaign_id':'afdm-direction-20260908-v1',
                'protocol_sha256':data.protocol_sha256,'proceed_confirmation':True,
                'arm_ids':['fixture-reference','fixture-candidate'],
                'n_by_snr':{'7':128,'8':256,'9':128},
                'authorization':{'status':'accepted','evidence_path':auth.name,
                    'evidence_sha256':hashlib.sha256(auth.read_bytes()).hexdigest()},
                'evidence_kind':'unit-fixture-not-scientific-authorization'}
            path=root/'manifest.json'
            def install(value):
                path.write_text(json.dumps(value))
                data.freeze_token={'frozen_manifest_path':str(path),
                    'frozen_manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            install(manifest)
            data._validate_request('confirm',255,8,arm_id='fixture-candidate')
            for block,snr,arm in [(0,8,None),(0,8,'unfrozen'),(256,8,'fixture-candidate'),
                                  (128,7,'fixture-reference')]:
                with self.assertRaises(ValueError):
                    data._validate_request('confirm',block,snr,arm_id=arm)
            data.freeze_token['frozen_manifest_sha256']='a'*64
            with self.assertRaises(ValueError):data._validate_request('confirm',0,8,arm_id='fixture-reference')
            for key,value in [('campaign_id','wrong'),('protocol_sha256','b'*64),
                              ('proceed_confirmation',False),('arm_ids',['duplicate','duplicate']),
                              ('n_by_snr',{'7':2049,'8':256,'9':128}),
                              ('n_by_snr',{'7':128,'8':4097,'9':128})]:
                changed=copy.deepcopy(manifest);changed[key]=value;install(changed)
                with self.subTest(key=key),self.assertRaises(ValueError):
                    data._validate_request('confirm',0,8,arm_id='fixture-reference')
            for field,value in [('status','pending'),('evidence_sha256','c'*64),
                                ('evidence_path','absent.json')]:
                changed=copy.deepcopy(manifest);changed['authorization'][field]=value;install(changed)
                with self.subTest(field=field),self.assertRaises(ValueError):
                    data._validate_request('confirm',0,8,arm_id='fixture-reference')
            install(manifest);path.unlink()
            with self.assertRaises(ValueError):data._validate_request('confirm',0,8,arm_id='fixture-reference')

    def test_real_make_frame_cross_snr_pairing(self):
        # Small generator fixture isolates RNG/frame assembly, not N1024 physics.
        from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
        class System:
            N_total=4
            rho=.5
            _zc_seq=np.ones(4,complex)
            def generate_channel_matrix(self):
                H=np.diag(np.random.standard_normal(4)+1j*np.random.standard_normal(4))
                return H,None,{'fixture':True}
        code={'n':8,'k':8}
        names={1:'channel',2:'data',3:'noise'}
        def rng_factory(rep,index,stream,*,split):
            return campaign_rng('mechanism',index,names[stream])
        a=make_frame(System(),code,0,3,7,uncoded=True,split=92,rng_factory=rng_factory)
        b=make_frame(System(),code,0,3,9,uncoded=True,split=92,rng_factory=rng_factory)
        for key in ('H','info','coded','noise','pilot','data'):
            np.testing.assert_array_equal(a[key],b[key])
        for frame in (a,b):
            np.testing.assert_allclose(frame['y']-frame['H']@(frame['pilot']+frame['data']),
                                       np.sqrt(frame['sigma2'])*frame['noise'],atol=1e-14)
        self.assertFalse(np.array_equal(a['y'],b['y']))


class NumericalContracts(unittest.TestCase):
    def test_pure_pilot_single_path_omp_ls_and_cancellation(self):
        from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix,omp_sparse
        from afdm_sp_joint_unrolled.classical_joint_unrolled import reconstruct_H_torch
        N,kmax,lmax=16,1,2
        c1,c2=3/(2*N),1e-4
        pilot=np.sqrt(.5)*np.exp(-1j*np.pi*7*np.arange(N)**2/N)
        Phi=construct_sensing_matrix(N,pilot,c1,c2,lmax,kmax)
        atom=4
        gain=.7+.2j
        H=reconstruct_H_torch(N,torch.tensor([atom//3]),torch.tensor([atom%3-1]),
            torch.tensor([gain],dtype=torch.complex128),c1,c2,kmax,torch.complex128).numpy()
        np.testing.assert_allclose(H@pilot,Phi[:,atom]*gain,atol=1e-12)
        h,support=omp_sparse(H@pilot,Phi,1)
        self.assertEqual(list(support),[atom])
        np.testing.assert_allclose(h[atom],gain,atol=1e-12)
        ls=np.linalg.lstsq(Phi[:,support],H@pilot,rcond=None)[0]
        np.testing.assert_allclose(ls,[gain],atol=1e-12)
        data=np.full(N,.5+.5j)
        y=H@(pilot+data)
        np.testing.assert_allclose(y-H@pilot,H@data,atol=1e-12)
        self.assertGreater(np.linalg.norm(y+H@pilot-H@data),.1)
        self.assertGreater(np.linalg.norm(y-H@(np.sqrt(.5)*pilot)-H@data),.1)

    def test_exact_diagonal_likelihood_matches_real_bp_gaussian_llr(self):
        const=np.array([1+1j,1-1j,-1+1j,-1-1j])/2
        H=np.diag([.8+.2j,1.1-.3j])
        y=np.array([.31+.18j,-.27+.41j])
        sigma=.3
        exact=exact_qpsk_llr(y,H,sigma,const)
        _,mu,var=mp_detect_bp_torch(y,H,sigma,const,device='cpu',return_soft=True,return_numpy=True)
        actual=demap_llr(mu,var,.5)
        # Diagonal factors have one unknown: Gaussian aggregate is exact for demapping.
        np.testing.assert_allclose(actual,np.clip(exact,-20,20),rtol=1e-8,atol=1e-8)
        # Existing BP adds a zero-mean Gaussian prior precision. Its mu/var
        # ratio still gives the exact equal-energy QPSK likelihood LLR here.
        prior_var=np.var(const)
        analytic_var=1/(1/prior_var+abs(np.diag(H))**2/sigma)
        analytic_mu=analytic_var*np.conj(np.diag(H))*y/sigma
        np.testing.assert_allclose(mu,analytic_mu,atol=1e-8)
        np.testing.assert_allclose(var,analytic_var,atol=1e-8)
        # This does not assert equality to finite-constellation posterior variance.

    def test_small_dense_exact_likelihood_is_consistent(self):
        report=dense_likelihood_bp_audit()
        json.dumps(report,allow_nan=False)
        self.assertTrue(np.isfinite(report['BP_llr']).all())
        self.assertTrue(np.isfinite(report['exact_llr']).all())
        np.testing.assert_allclose(report['exact_llr'],report['exact_rotated_llr'],atol=1e-12)
        np.testing.assert_allclose(report['BP_llr'],report['BP_rotated_llr'],atol=1e-10,rtol=1e-10)
        np.testing.assert_allclose(report['BP_minus_exact_clipped_llr'],
            np.array(report['BP_llr'])-np.clip(report['exact_llr'],-20,20),atol=1e-12)
        # Difference values are retained; approximate BP is not required to equal exact.

    def test_white_complex_noise_variance_scaling(self):
        rng=np.random.default_rng(2026090811)
        n=200000
        noise=(rng.standard_normal(n)+1j*rng.standard_normal(n))/np.sqrt(2)
        # Fixed sample/seed and tolerances set before execution: over four SE for
        # unit energy, and similarly conservative real/imag covariance checks.
        self.assertLess(abs(float(np.mean(abs(noise)**2))-1),.01)
        self.assertLess(abs(float(np.mean(noise.real**2))-.5),.008)
        self.assertLess(abs(float(np.mean(noise.imag**2))-.5),.008)
        self.assertLess(abs(float(np.mean(noise.real*noise.imag))),.008)
        sigma2=.2
        measured=float(np.mean(abs(np.sqrt(sigma2)*noise)**2))
        self.assertLess(abs(measured-sigma2),.002)
        self.assertGreater(abs(float(np.mean(abs(sigma2*noise)**2))-sigma2),.1)

    def test_real_small_terminal_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,seed=20260726,cache_dir=tmp)
            info=np.random.default_rng(71).integers(0,2,code['k'],dtype=np.uint8)
            coded=encode(code,info)
            data=qpsk_map(coded,scale=np.sqrt(.5))
            const=np.array([1+1j,1-1j,-1+1j,-1-1j])/2
            result=terminal_decode(data,np.eye(12,dtype=complex),.02,const,code)
            np.testing.assert_array_equal(result['decoded'],coded)
            np.testing.assert_array_equal(result['info_hat'],info)
            self.assertTrue(result['decode_ok'])

    def test_frozen_n2048_code_and_noiseless_llr_sign(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(cache_dir=tmp)
            self.assertEqual(hashlib.sha256(code['G'].tobytes()).hexdigest(),CODE_HASH)
            info=np.random.default_rng(72).integers(0,2,code['k'],dtype=np.uint8)
            coded=encode(code,info)
            llr=20*(1-2*coded.astype(float))
            decoded,ok=decode_llr(code,llr,maxiter=50)
            self.assertTrue(ok)
            np.testing.assert_array_equal(decoded,coded)
            np.testing.assert_array_equal(extract_info(code,decoded),info)


if __name__ == '__main__':
    unittest.main()
