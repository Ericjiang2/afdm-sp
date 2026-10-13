"""Small synthetic wrapper contract; never opens a cold production witness."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
from unittest.mock import patch

import numpy as np

HERE=Path(__file__).resolve().parent
EXP=HERE.parent
sys.path[:0]=[str(HERE),str(EXP/'sp_afdm_native_joint_20260921/src'),
              str(EXP/'sp_afdm_frozen_20260920/src')]
import run_observed as runner  # noqa: E402
import tf_base  # noqa: E402
import tf_cgr  # noqa: E402
import tf_sham  # noqa: E402
import tf_block  # noqa: E402
from messages import moments  # noqa: E402


@dataclass
class PathSlot:
    delay:int
    doppler:float


class Kernel:
    Path=PathSlot
    def __init__(self):
        self.calls=[]
    def reopen_geometry(self,Y,x,v,initial,**kwargs):
        self.calls.append(dict(Y=Y.copy(),x=x.copy(),v=v.copy(),
                               initial=initial,kwargs=kwargs))
        stages={name:0. for name in runner.STAGES[2:10]}
        return SimpleNamespace(paths=initial,gains=np.array([.2+.1j,-.1+.3j]),
            diagnostics=dict(stage_timing=dict(exclusive_seconds=stages,total_seconds=0.)),
            elapsed_seconds=0.,evaluations=1)


class Native:
    def __init__(self):
        self.calls=[]
    def decoder_messages(self,code,llr,maxiter):
        self.calls.append((llr.copy(),maxiter))
        return dict(decoded=np.zeros(len(llr),np.uint8),incoming_llr=llr.copy(),
                    raw_app=llr.copy(),raw_check_extrinsic=np.zeros_like(llr),
                    iterations=1)


def test_branch():
    n=32;rng=np.random.default_rng(24)
    c1=3.7/(2*n);c2=.017
    obs=dict(y=rng.normal(size=n)+1j*rng.normal(size=n),
             pilot=.5*(rng.normal(size=n)+1j*rng.normal(size=n)),sigma2=.25)
    arrays=dict(r1_app=rng.normal(size=2*n)*40,
                r1_check=rng.normal(size=2*n)*40,
                r1_delays=np.array([3,3]),r1_dopplers=np.array([.2,.27]),
                r1_gains=np.array([.2+.1j,-.1+.3j]))
    system=SimpleNamespace(rho=.5,c1=c1,c2=c2,l_max_cap=10)
    results=[]
    for detector in (tf_base,tf_cgr,tf_sham,tf_block):
        kernel=Kernel();native=Native()
        branch=runner._branch(obs,system,None,native,kernel,arrays,detector)
        assert len(kernel.calls)==len(native.calls)==1
        expected_mu,expected_v,_=moments(np.clip(arrays['r1_app'],-20,20),.5)
        assert np.array_equal(kernel.calls[0]['x'],obs['pilot']+expected_mu)
        assert np.array_equal(kernel.calls[0]['v'],expected_v)
        assert np.array_equal(branch['entering']['check'],np.clip(arrays['r1_check'],-20,20))
        assert native.calls[0][1]==50
        assert np.array_equal(native.calls[0][0],
                              np.clip(branch['detector']['extrinsic'],-20,20))
        assert len(branch['detector']['states'])==20
        assert len(branch['exclusive_stages'])==len(runner.STAGES)
        assert sum(branch['exclusive_stages'].values())==branch['branch_decision_seconds'] or np.isclose(
            sum(branch['exclusive_stages'].values()),branch['branch_decision_seconds'],atol=1e-7)
        results.append(branch)
    assert len({b['entering_sha256'] for b in results})==1
    assert np.max(abs(results[0]['gram']['R']-results[1]['gram']['R']))==0
    assert np.max(abs(results[0]['detector']['gains']-results[1]['detector']['gains']))>1e-10
    print('synthetic final branch: APP/check, exact CSTATE config, 1 LDPC50, 4-arm prefix identity passed')


def test_manifest():
    path=EXP.parent/'_archive/20260923_tf_cgr_investigation/extracted/coherent_gain_investigation/witness_manifest.json'
    entries=json.loads(path.read_text())['entries']
    calls=runner.schedule(entries)
    assert len(calls)==100
    for block in range(4):
        assert {arm for _,arm in calls[block*4:(block+1)*4]}==set(runner.ARMS)
    for offset in range(4):
        assert len({arm for _,arm in calls[offset::4]})==4
    print('frozen 25x4 balanced schedule passed')


def test_numerical_fallback_and_cap():
    """One fully serialized synthetic wrapper, with no actual receiver/context."""
    from argparse import Namespace
    import evidence
    n=1024
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);witness=root/'witness';witness.mkdir()
        obs=dict(y=np.zeros(n,complex),pilot=np.zeros(n,complex),sigma2=.25)
        parts=[]
        for name in ('y','pilot','sigma2'):
            a=np.asarray(obs[name]);digest=hashlib.sha256()
            digest.update(str(a.dtype).encode());digest.update(json.dumps(a.shape).encode())
            digest.update(np.ascontiguousarray(a).tobytes());parts.append(digest.hexdigest())
        observation_hash=hashlib.sha256('|'.join(parts).encode()).hexdigest()
        artifact=witness/'synthetic.npz'
        input_sha=evidence.save_artifact(artifact,
            dict(observation_id='synthetic',observation=obs,observation_hash=observation_hash,
                 stream_ids=dict(channel='a',message='b',noise='c')),
            dict(kind='observed',observation_id='synthetic'))
        entry=dict(observation_id='synthetic',role='synthetic',
                   files=[dict(kind='observation',relative_path=artifact.name,sha256=input_sha)])
        cache=root/'cache.npz';H=np.zeros((1026,2048),np.uint8);H[0,0]=1
        G=np.zeros((2048,1024),np.uint8);free=np.arange(1024)
        np.savez(cache,H=H,G=G,free_cols=free)
        G_sha=hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest()
        for name in ('witness_manifest.json','witness_receipt.json','source_bindings.json',
                     'registration.json','qualification.json'):
            (root/name).write_text('{}')
        bits=np.zeros(2048,np.uint8);bits[0]=1
        native_dec=dict(decoded=bits)
        def fake_receive(observation,system,code,**kwargs):
            sink=kwargs['checkpoint_sink']
            for round_index in (0,1):
                sink(dict(round=round_index,snapshot=dict(decoded=bits)),bits)
            return native_dec,dict(r1_decoded=bits),dict(events=[])
        fake_native=SimpleNamespace(receive=fake_receive)
        fake_evidence=SimpleNamespace(bind_runtime_environment=lambda:{'synthetic':True},
            verify_runtime_binding=lambda:None,save_artifact=evidence.save_artifact,
            load_artifact=evidence.load_artifact)
        fake_receiver=SimpleNamespace(context=lambda:(
            SimpleNamespace(N_total=1024,l_max_cap=102,rho=.5),None,None,
            dict(code_g_sha256=G_sha)))
        common=dict(source=EXP/'sp_afdm_native_joint_20260921',
            baseline=EXP/'sp_afdm_frozen_20260920',
            geometry=EXP/'tf_cstate_validation_20260922',witness_root=witness,
            witness_manifest=root/'witness_manifest.json',
            witness_receipt=root/'witness_receipt.json',
            source_bindings=root/'source_bindings.json',seconds=1800)
        common['registration']=root/'registration.json'
        common['qualification']=root/'qualification.json'
        def args(name,cap):return Namespace(**common,out=root/name,bytes_cap=cap)
        with patch.object(runner,'preflight',return_value=(dict(n_frames=1),[(entry,'BASE')],{})),\
             patch.object(runner,'attach',return_value=fake_evidence),\
             patch.object(runner,'_source_files',return_value=dict(code_cache=cache)),\
             patch.object(runner,'_branch',side_effect=np.linalg.LinAlgError('synthetic final failure')),\
             patch.dict(sys.modules,{'native_twofft':fake_native,
                                     'geometry_validation':SimpleNamespace(),
                                     'receiver':fake_receiver}):
            runner.run(args('fallback',2*1024**3))
            out=root/'fallback'
            row=json.loads((out/'ledger.jsonl').read_text())
            assert row['status']=='ok' and row['numerical_failure'] is not None
            assert len(row['checkpoints'])==2 and row['baseline_syndrome_weight']==1
            assert row['branch_complete_seconds']>=row['branch_elapsed_seconds']>0
            assert row['final_decision_ready_seconds']<row['complete_latency_seconds']
            assert (out/'observed_seal.json').exists()
            raw,_=evidence.load_artifact(out/row['raw_path'])
            assert np.array_equal(raw['final_decoded'],bits)
            assert raw['branch_decoder'] is None
            try:
                runner.run(args('capped',5000))
            except RuntimeError as error:
                assert '2GiB cap reached after completed call' in str(error)
            else:
                raise AssertionError('post-call cap was not enforced')
            assert (root/'capped/blocked.json').exists()
            assert not (root/'capped/observed_seal.json').exists()
    print('synthetic numerical fallback, retained ready decision, cost, post-call cap passed')


if __name__=='__main__':
    test_manifest()
    test_branch()
    test_numerical_fallback_and_cap()
