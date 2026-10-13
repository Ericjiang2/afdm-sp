"""Direct objective, LDPC candidate legality and immutable-input gates."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'afdm_sp_joint_unrolled'/'outputs_ce_state_20260915'/'source-v4'))
spec=importlib.util.spec_from_file_location('codeword_profile_runner_v1',HERE/'codeword_profile_runner_v1.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_ridge_profile_direct_equals_closed_and_normal():
    rng=np.random.default_rng(20260915)
    A=(rng.normal(size=(1024,24))+1j*rng.normal(size=(1024,24)))/np.sqrt(2)
    y=rng.normal(size=1024)+1j*rng.normal(size=1024)
    lam=11.5
    g,score=module.fit_profile(y,A,lam)
    np.testing.assert_allclose(g,np.linalg.solve(A.conj().T@A+lam*np.eye(24),A.conj().T@y),rtol=1e-13)
    assert abs(score['J']-score['closed_profile'])<1e-7
    assert score['relative_normal_residual']<1e-12
    assert score['rank']==24
    bad=A.copy();bad[:,1]=bad[:,0]
    with pytest.raises(np.linalg.LinAlgError,match='rank'):
        module.fit_profile(y,bad,lam)


def test_decoded_raw_invalid_reencoding_legal_and_qpsk_order():
    from afdm_sp_joint_unrolled.e1_ldpc import encode,qpsk_map
    G=np.zeros((2048,1024),dtype=np.uint8)
    G[:1024]=np.eye(1024,dtype=np.uint8)
    H=np.zeros((1024,2048),dtype=np.uint8)
    H[:,1024:]=np.eye(1024,dtype=np.uint8)
    code=dict(G=G,H=H,free_cols=np.arange(1024),k=1024)
    info=np.zeros(1024,dtype=np.uint8)
    truth=encode(code,info)
    decoded=truth.copy();decoded[0]=1;decoded[1024]=1
    candidates,status=module.candidate_bits(code,truth,decoded,decoded[:1024])
    assert status['true_c']['valid']
    assert not status['decoded_raw']['valid']
    assert status['reencoded_info_hat']['valid']
    assert not np.array_equal(candidates['decoded_raw'],candidates['reencoded_info_hat'])
    assert not np.array_equal(candidates['reencoded_info_hat'],truth)
    z=qpsk_map(candidates['reencoded_info_hat'],scale=np.sqrt(.5))
    assert z.shape==(1024,) and z[0]==-.5+.5j and z[1]==.5+.5j


def test_hash_guard_rejects_changed_input(tmp_path):
    p=tmp_path/'source.json';p.write_text('{"frozen":true}')
    digest=module.file_sha(p)
    module.require_sha(p,digest)
    p.write_text('{"frozen":false}')
    with pytest.raises(ValueError,match='digest differs'):
        module.require_sha(p,digest)


def test_cross_snapshot_saved_A_numeric_gate():
    A=np.ones((1024,24),dtype=np.complex64)
    assert module.saved_operator_parity(A,np.asarray(A,dtype=np.complex128))==0
    drift=np.asarray(A,dtype=np.complex128).copy();drift[0,0]+=.01
    with pytest.raises(FloatingPointError,match='operator differs'):
        module.saved_operator_parity(A,drift)


def test_margin_sign_and_flip():
    fixed=dict(true_c=4.,decoded_raw=2.,reencoded_info_hat=7.)
    profile=dict(true_c=1.,decoded_raw=3.,reencoded_info_hat=2.)
    result=module.margins(fixed,profile)
    assert result['decoded_raw']['ranking_flip']
    assert result['decoded_raw']['profile_true_preferred']
    assert not result['reencoded_info_hat']['ranking_flip']
