"""RUN-04 offline oracle: replace only terminal H, never upstream feedback."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import torch
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame, final_bp, file_hash, e1
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash, project_channel_on_support
from afdm_sp_joint_unrolled.representation_ledger import representation_error
from afdm_sp_joint_unrolled.e1_ldpc import build_code, demap_llr, decode_llr, extract_info
from afdm_sp_joint_unrolled.budgeted_job_queue import write_status


def frozen_support(record, k_max, N):
    baseline=record['arms']['baseline']
    finals=[t for t in baseline['capacity_trace'] if t['stage']=='final']
    if len(finals)!=1:raise ValueError('missing unique final support')
    ids=finals[0]['atom_ids']
    if any(type(i) is not int or i<0 for i in ids):raise ValueError('integer support IDs required')
    if not np.isfinite(baseline['nmse']) or baseline['nmse']<0:raise ValueError('invalid archived NMSE')
    if len(ids)!=40 or len(set(ids))!=40:raise ValueError('reference must have 40 unique atoms')
    outer=[t for t in baseline['capacity_trace'] if t['stage']=='outer']
    if [t.get('outer_iter') for t in outer]!=list(range(10)):
        raise ValueError('reference must contain all ten outer supports')
    if any(t['atom_ids']!=ids for t in outer):
        raise ValueError('effective excess derivation requires fixed outer support')
    if len({(i-k_max)%N for i in ids})!=len(ids):raise ValueError('shift collisions invalidate coordinate-support proof')
    if not np.isfinite(baseline['sigma2_final']) or baseline['sigma2_final']<=0:raise ValueError('invalid archived noise estimate')
    return np.array(ids,dtype=np.int64)


def run_one(system,code,old, *, dense_check=False):
    started=time.perf_counter();rep,i=old['replicate'],old['frame_index']
    if old['split']!='D_cal' or rep not in (30,31,32) or not 0<=i<64 or old['snr']!=8:
        raise ValueError('unregistered fit frame')
    frame=make_frame(system,code,rep,i,8,split=2)
    hashes={k:array_hash(frame[k]) for k in ('y','H','noise','info','coded','pilot')}
    if hashes!=old['input_hashes']:raise ValueError('regenerated fit input bytes changed')
    k=system.k_max_cap;N=system.N_total;ids=frozen_support(old,k,N)
    if int(round(2*N*system.c1))!=2*k+1 or system.gen_h_daft_convention!='python':raise ValueError('projection convention mismatch')
    dl,dk=ids//(2*k+1),ids%(2*k+1)-k
    H,g=project_channel_on_support(torch.from_numpy(frame['H']),torch.from_numpy(dl),torch.from_numpy(dk),system.c1,system.c2,k)
    high=H.numpy();injected=high.astype(np.complex64)
    denominator=float(np.linalg.norm(frame['H'])**2);residual=frame['H']-high
    repr_abs=float(np.linalg.norm(residual)**2)
    if not np.isfinite(denominator) or denominator<=0:raise ValueError('positive finite true channel energy required')
    old_mse=old['arms']['baseline']['nmse']*denominator
    col=np.arange(N);row=(col[None,:]+(ids-k)[:,None])%N
    epsilon=float(np.linalg.norm(residual[row,col[None,:]]))
    # Triangle inequality bounds the unknown actual-minus-projected H norm.
    cross_bound=2*epsilon*(np.sqrt(old_mse)+np.sqrt(repr_abs))
    round_bound=64*np.finfo(float).eps*max(1.,old_mse,repr_abs)
    excess=old_mse-repr_abs
    if excess<-(cross_bound+round_bound):raise ValueError('effective excess violates numerical bound')
    independent=representation_error(system,frame['params'],frame['H'],ids,k,dense_reference=True) if dense_check else None
    preparation=time.perf_counter()-started
    sigma=old['arms']['baseline']['sigma2_final']
    const=np.sqrt(1-system.rho)*e1.QPSK
    torch.cuda.synchronize();bp_start=time.perf_counter()
    _,mu,var=final_bp(frame['y']-injected@frame['pilot'],injected,sigma,const,
                     n_iter=20,threshold=1e-4,damp=.5,return_soft=True)
    llr=demap_llr(mu,var,np.sqrt((1-system.rho)/2))
    decoded,ok=decode_llr(code,llr,maxiter=50)
    errors=int((extract_info(code,decoded)!=frame['info']).sum())
    torch.cuda.synchronize()
    if not all(np.isfinite(x).all() for x in (mu,var,llr)):raise ValueError('nonfinite terminal receiver')
    return dict(replicate=rep,frame_index=i,split='D_cal',input_hashes=hashes,final_ids=ids.tolist(),
        original_H_hash=old['arms']['baseline']['output_h_sha256'],original_sigma=sigma,
        old_info_errors=old['arms']['baseline']['info_errors'],info_errors=errors,decode_ok=bool(ok),
        injected_H_hash=array_hash(injected),projection_gains=dict(real=g.real.tolist(),imag=g.imag.tolist()),
        E_repr=repr_abs/denominator,E_injected=float(np.linalg.norm(frame['H']-injected)**2/denominator),
        denominator=denominator,effective_channel_excess_squared=excess,
        excess_numerical_bound=cross_bound+round_bound,selected_residual_norm=epsilon,
        cross_term_bound=cross_bound,rounding_allowance=round_bound,
        bound_scope="Cauchy/triangle cross term plus heuristic64eps rounding allowance; not certified interval arithmetic",
        actual_gain_scope='effective channel excess; no raw gain-vector recovery',
        independent_dense=independent,preparation_seconds=preparation,terminal_seconds=time.perf_counter()-bp_start,
        final_llr_hash=array_hash(llr),decoded_bits_hash=array_hash(decoded))


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=64)
    args=p.parse_args();reference=json.loads(args.reference.read_text())
    if args.start<0 or args.count<=0 or args.start+args.count>len(reference['frames']):raise ValueError('invalid slice')
    if not torch.cuda.is_available():raise RuntimeError('registered CUDA required')
    args.out.mkdir(exist_ok=False,parents=True)
    status=dict(complete=False,started_at=time.time(),reference_sha256=file_hash(args.reference),completed=0)
    write_status(args.out/'status.json',status)
    try:
        system=_make_config_a(1024,2,8,10,4);code=build_code(2048,d_v=3,d_c=6,seed=20260726)
        if file_hash(code['cache_path'])!=reference['ldpc_sha256']:raise ValueError('LDPC changed')
        with (args.out/'frames.jsonl').open('x') as f:
            for n in range(args.start,args.start+args.count):
                result=run_one(system,code,reference['frames'][n],dense_check=n%64==0)
                f.write(json.dumps(result,allow_nan=False)+'\n');f.flush();status['completed']+=1
                write_status(args.out/'status.json',status)
        status['complete']=True
    except Exception as e:
        status['failure']=repr(e);raise
    finally:
        status['ended_at']=time.time();write_status(args.out/'status.json',status)

if __name__=='__main__':main()
