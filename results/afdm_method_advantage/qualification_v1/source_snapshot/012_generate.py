"""Independent physical population generation. Not imported by wrapper receiver."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from wrapper import bootstrap,sha256,write_json,append_json,assert_frozen_modules,verify_runtime_registration,writer_lock,runtime_binding


def _generate(rt,allocation_path,split,out,registration):
    registration_path=Path(registration)
    reg=json.loads(registration_path.read_text())
    verify_runtime_registration(rt,reg)
    registration_sha=sha256(registration_path)
    allocation_path=Path(allocation_path);out=Path(out)
    if sha256(allocation_path)!=reg['allocation_sha256']:raise ValueError('allocation registration differs')
    allocation=json.loads(allocation_path.read_text())
    rows=[r for r in allocation if r['split']==split]
    if not rows or len({r['index'] for r in rows})!=len(rows):raise ValueError('split allocation invalid')
    out.mkdir(parents=True,exist_ok=False)
    observed=out/'observed';truth=out/'truth'
    observed.mkdir();truth.mkdir()
    allocation_sha=sha256(allocation_path)
    for root,kind in ((observed,'observed'),(truth,'truth')):
        write_json(root/'manifest.json',dict(allocation_sha256=allocation_sha,split=split,kind=kind,allocation=rows,seed_rule='hex digest bytes interpreted little-endian u32 limbs passed to SeedSequence',generator_sha256=sha256(__file__),registration_sha256=registration_sha,registration=reg,runtime_binding=runtime_binding(rt)))
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
    from analyze_reopening import observation_hash
    assert_frozen_modules(rt.up)
    seen=set()
    for row in rows:
        index=row['index'];stem=f'{split}_f{index:06d}';seeds=row['component_seeds']
        if set(seeds)!={'channel','message','noise'}:raise ValueError('component seeds absent')
        def factory(_rep,frame,component,*,split):
            if frame!=index or split!=2 or component not in (1,2,3):raise ValueError('unregistered generator stream')
            name=('channel','message','noise')[component-1]
            words=np.frombuffer(bytes.fromhex(seeds[name]),dtype='<u4').astype(np.uint32).tolist()
            return np.random.default_rng(np.random.SeedSequence(words))
        append_json(out/'attempts.jsonl',dict(observation_id=stem,event='started'))
        state=np.random.get_state()
        try:raw=make_frame(rt.system,rt.code,0,index,row['snr_centi_db']/100,split=2,rng_factory=factory)
        except BaseException as error:
            append_json(out/'attempts.jsonl',dict(observation_id=stem,event='failed',exception=repr(error)));raise
        finally:np.random.set_state(state)
        raw,diagnostics=physical_observation(raw,rt.system,prefix_length=rt.system.l_max_cap)
        scale=np.sqrt(2*(1-rt.system.rho))
        obs=dict(y=np.asarray(raw['y'])/scale,pilot=np.asarray(raw['pilot'])/scale,sigma2=float(raw['sigma2'])/scale**2)
        digest=observation_hash(obs)
        if digest in seen:raise ValueError('duplicate observation; do not replace')
        seen.add(digest)
        coord=dict(observation_id=stem,snr_centi_db=row['snr_centi_db'],frame=index,split=split,observation_hash=digest,stream_ids=seeds)
        op=observed/'data'/f'{stem}.npz';tp=truth/'data'/f'{stem}.npz'
        osh=rt.evidence.save_artifact(op,dict(observation=obs,observation_id=stem,observation_hash=digest,stream_ids=seeds),dict(kind='observed',allocation_sha256=allocation_sha,observation_id=stem))
        truth_payload=dict(coded=raw['coded'],info=raw['info'],l_i=raw['params']['l_i'],k_real=raw['params']['k_real'],g_i=raw['params']['g_i'],diagnostics=diagnostics,observation_hash=digest,stream_ids=seeds)
        tsh=rt.evidence.save_artifact(tp,truth_payload,dict(kind='truth',allocation_sha256=allocation_sha,observation_id=stem))
        append_json(observed/'ledger.jsonl',dict(coord,observation_path=str(op.relative_to(observed)),observation_sha256=osh))
        append_json(truth/'ledger.jsonl',dict(coord,truth_path=str(tp.relative_to(truth)),truth_sha256=tsh))
        append_json(out/'attempts.jsonl',dict(observation_id=stem,event='finished'))
    verify_runtime_registration(rt,reg)
    if sha256(registration_path)!=registration_sha:raise ValueError('registration changed during generation')
    if sha256(allocation_path)!=allocation_sha:raise ValueError('allocation changed during generation')
    for root,kind in ((observed,'observed'),(truth,'truth')):
        write_json(root/f'{kind}_seal.json',dict(status='pass',allocation_sha256=allocation_sha,registration_sha256=registration_sha,observations=len(rows),files={str(p.relative_to(root)):sha256(p) for p in root.rglob('*') if p.is_file()}))
    return dict(observations=len(rows),allocation_sha256=allocation_sha)



def generate(rt,allocation_path,split,out,registration):
    with writer_lock(out):
        return _generate(rt,allocation_path,split,out,registration)

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--allocation',type=Path,required=True);p.add_argument('--split',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);a=p.parse_args()
    rt=bootstrap(a.project,a.source,a.baseline);print(json.dumps(generate(rt,a.allocation,a.split,a.out,a.registration)))

if __name__=='__main__':main()
