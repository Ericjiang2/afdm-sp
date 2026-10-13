"""Actual evidence round trip for every successful arm and trace storage form.

Uses only synthetic N=1024 inputs; never opens a cold production observation.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE=Path(__file__).resolve().parent
EXP=HERE.parent
sys.path[:0]=[str(HERE),str(EXP/'sp_afdm_native_joint_20260921/src'),
              str(EXP/'sp_afdm_frozen_20260920/src')]
import evidence  # noqa: E402
import run_observed as runner  # noqa: E402
import tf_base  # noqa: E402
import tf_cgr  # noqa: E402
import tf_sham  # noqa: E402
import tf_block  # noqa: E402


@dataclass
class PathSlot:
    delay:int
    doppler:float


@dataclass
class Result:
    paths:list
    gains:np.ndarray
    diagnostics:dict
    elapsed_seconds:float
    evaluations:int


class Kernel:
    Path=PathSlot
    @staticmethod
    def reopen_geometry(Y,x,v,initial,**kwargs):
        stages={key:0. for key in runner.STAGES[2:10]}
        return Result(paths=initial,gains=np.asarray([.21+.08j,-.13+.12j]),
            diagnostics=dict(stage_timing=dict(exclusive_seconds=stages,total_seconds=0.)),
            elapsed_seconds=0.,evaluations=1)


class Native:
    @staticmethod
    def decoder_messages(code,llr,maxiter):
        if maxiter!=50:
            raise AssertionError('one frozen LDPC50 boundary required')
        bits=np.zeros(2048,np.uint8)
        return dict(decoded=bits,incoming_llr=llr.copy(),raw_app=llr.copy(),
                    raw_check_extrinsic=np.zeros(2048),iterations=1,
                    decode_ok=True,metadata=dict(seconds=0.),syndrome_trace=[0])


def check_metadata(value,path='payload'):
    if isinstance(value,dict):
        for key,item in value.items():
            if not isinstance(key,str):
                raise AssertionError(f'non-string evidence metadata key at {path}: {key!r}')
            check_metadata(item,f'{path}.{key}')
    elif isinstance(value,(list,tuple)):
        for index,item in enumerate(value):
            check_metadata(item,f'{path}[{index}]')
    elif isinstance(value,np.ndarray):
        if np.issubdtype(value.dtype,np.number) and not np.isfinite(value).all():
            raise AssertionError(f'nonfinite array at {path}')
    elif isinstance(value,np.generic):
        check_metadata(value.item(),path)
    elif isinstance(value,float) and not np.isfinite(value):
        raise AssertionError(f'nonfinite scalar at {path}')


def test_roundtrip():
    n=1024;rng=np.random.default_rng(20260923)
    system=type('System',(),dict(rho=.5,c1=3.7/(2*n),c2=.017,l_max_cap=102))()
    obs=dict(y=rng.normal(size=n)+1j*rng.normal(size=n),
             pilot=.3*(rng.normal(size=n)+1j*rng.normal(size=n)),sigma2=.25)
    arrays=dict(r1_app=rng.normal(size=2048),r1_check=rng.normal(size=2048),
        r1_delays=np.array([3,3]),r1_dopplers=np.array([.2,.27]),
        r1_gains=np.array([.21+.08j,-.13+.12j]),
        r0_decoded=np.zeros(2048,np.uint8),r1_decoded=np.zeros(2048,np.uint8))
    native=Native()
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        for arm,detector in (('BASE',tf_base),('CGR',tf_cgr),
                             ('SHAM',tf_sham),('BLOCK',tf_block)):
            branch=runner._branch(obs,system,None,native,Kernel(),arrays,detector)
            for target in (True,False):
                stem='s650_f0390' if target else 's600_f0087'
                detector_result=dict(branch['detector'])
                common=runner._base_common_state(detector_result['states'],n) if arm=='BASE' else None
                if not target:
                    detector_result['states']=runner._scalar_states(detector_result['states'])
                raw=dict(observation_id=stem,arm=arm,input_sha256='synthetic',
                    native_arrays=arrays,native_timing=dict(seconds=0.,events=[]),
                    native_decoder=dict(decoded=np.zeros(2048,np.uint8)),
                    triggered=True,numerical_failure=None,
                    entering=branch['entering'],gram=branch['gram'],
                    geometry_result=asdict(branch['result']),
                    branch_detector=detector_result,base_common_state=common,
                    trace_origin='synthetic qualification',
                    branch_decoder=branch['decoder'],
                    final_decoded=branch['decoder']['decoded'])
                check_metadata(raw)
                path=tmp/f'{stem}_{arm}.npz'
                digest=evidence.save_artifact(path,raw,
                    dict(schema=runner.SCHEMA,observation_id=stem,arm=arm))
                assert runner.sha256(path)==digest
                loaded,identity=evidence.load_artifact(path)
                assert identity['arm']==arm and identity['observation_id']==stem
                assert len(loaded['branch_detector']['states'])==20
                assert np.array_equal(loaded['gram']['R'],raw['gram']['R'])
                assert loaded['gram']['group_multiplicities']==raw['gram']['group_multiplicities']
                decision=dict(observation_id=stem,arm=arm,raw_sha256=digest)
                runner.write_json(tmp/f'{stem}_{arm}.json',decision)
                runner._persist_jsonl(tmp/'ledger.jsonl',dict(status='ok',**decision))
        rows=[json.loads(line) for line in (tmp/'ledger.jsonl').read_text().splitlines()]
        assert len(rows)==8
        assert {(row['observation_id'],row['arm']) for row in rows}=={
            (stem,arm) for stem in ('s650_f0390','s600_f0087') for arm in runner.ARMS}
    print('8 synthetic four-arm target/control raw+decision+ledger evidence round trips passed')


if __name__=='__main__':
    test_roundtrip()
