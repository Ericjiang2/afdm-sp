"""Small, paired, uncoded OMP-support diagnostic. Truth is offline only.

The three receiver trajectories estimate gains normally. Oracle channels are
terminal-only interventions at frozen A noise states, not oracle feedback runs.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash, project_channel_on_support
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.budgeted_job_queue import write_status
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled, construct_sensing_matrix_torch,
    reconstruct_H_torch,
)
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger
from afdm_sp_joint_unrolled.run_classical_baselines_python import _bits_of_symbol


def complex_record(value):
    a = np.asarray(value)
    return dict(real=a.real.tolist(), imag=a.imag.tolist())


def reference_support(raw, gains, dictionary_size):
    """Same cardinality: true strongest first, retain raw padding in OMP order."""
    if not raw or len(set(raw)) != len(raw) or any(i < 0 or i >= dictionary_size for i in raw):
        raise ValueError('raw support must be nonempty, unique and in domain')
    if any(i < 0 or i >= dictionary_size or not np.isfinite(g) for i, g in gains.items()):
        raise ValueError('truth outside dictionary or nonfinite')
    ranked = sorted((i for i, g in gains.items() if abs(g) > 0), key=lambda i: (-abs(gains[i])**2, i))
    compact = ranked[:len(raw)]
    if not compact:
        raise ValueError('zero true channel')
    padded = compact + [i for i in raw if i not in compact][:len(raw)-len(compact)]
    if len(padded) != len(raw):
        raise AssertionError('reference capacity changed')
    return padded, compact


def support_quality(raw, gains):
    truth = {i for i, g in gains.items() if abs(g) > 0}
    selected = set(raw)
    energy = sum(abs(g)**2 for g in gains.values())
    if not truth or energy <= 0:
        raise ValueError('positive truth energy required')
    missing = sorted(truth-selected)
    return dict(true_atoms=len(truth), selected_atoms=len(raw),
                missed_ids=missing, false_ids=sorted(selected-truth),
                recall=len(selected & truth)/len(truth), precision=len(selected & truth)/len(selected),
                missed_coefficient_energy=sum(abs(gains[i])**2 for i in missing)/energy)


def count_errors(mu, truth_bits):
    if not np.isfinite(mu).all():
        raise ValueError('nonfinite detector output')
    bits = _bits_of_symbol(mu, len(mu)).astype(np.uint8)
    if bits.shape != truth_bits.shape or not np.isin(truth_bits, [0, 1]).all():
        raise ValueError('bit endpoint mismatch')
    mask = bits != truth_bits
    return dict(errors=int(mask.sum()), bits=int(mask.size),
                error_mask_hex=np.packbits(mask).tobytes().hex(), decoded_hash=array_hash(bits))


def build_model(system):
    cfg = ClassicalJointConfig(
        N=system.N_total, l_max=system.l_max_cap, k_max=system.k_max_cap,
        c1=system.c1, c2=system.c2, rho=float(system.rho), n_paths=40,
        n_outer_iter=10, pic_iter=20, mp_mode='bp', pic_damp=.5,
        update_sigma2=True, early_stop=False, eps_stop_rel=-1,
        dtype=torch.complex64, rdtype=torch.float32, device='cuda')
    return ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=True).cuda().eval()


@torch.no_grad()
def run_frame(system, model, replicate, index, snr, *, verify=False):
    started = time.perf_counter()
    cfg = model.cfg
    frame = make_frame(system, {'n':2*cfg.N}, replicate, index, snr, uncoded=True, split=1)
    input_hashes = {k:array_hash(frame[k]) for k in ('y','H','noise','info','coded','pilot')}
    y = torch.as_tensor(frame['y'], device='cuda', dtype=cfg.dtype)
    pilot = torch.as_tensor(frame['pilot'], device='cuda', dtype=cfg.dtype)
    noise = torch.tensor(frame['sigma2'], device='cuda', dtype=cfg.rdtype)
    const = torch.tensor([1+1j,1-1j,-1+1j,-1-1j], device='cuda', dtype=cfg.dtype)*np.sqrt((1-cfg.rho)/2)
    Phi = construct_sensing_matrix_torch(cfg.N,pilot,cfg.c1,cfg.c2,cfg.l_max,cfg.k_max,cdtype=cfg.dtype)
    observed = []
    def observer(raw, chosen, delays, dopplers):
        observed.append((list(raw),list(chosen)))
    common = dict(Phi=Phi, return_trajectory=True, enable_support_repair=False,
                  active_support_cap=40, receiver_extension=0)
    a = model(y,pilot,noise,const,diagnostic_support_observer=observer,**common)
    if len(observed)!=1 or observed[0][0]!=observed[0][1]:
        raise AssertionError('raw OMP was repaired')
    raw = observed[0][0]
    ledger = merged_truth_ledger(frame['params'],cfg.k_max)
    gains = {}
    for e in ledger['entries']:
        if e['column'] is None or e['delay']>cfg.l_max:
            raise ValueError('truth outside the receiver dictionary')
        gains[e['column']] = complex(e['real'],e['imag'])
    reference, compact = reference_support(raw,gains,Phi.shape[1])
    supports = dict(A=raw,B=reference,F=compact)
    outputs = dict(A=a)
    for arm in ('B','F'):
        outputs[arm] = model(y,pilot,noise,const,oracle_support=supports[arm],**common)
    for arm,out in outputs.items():
        trace = out['capacity_trace']
        expected = set(supports[arm])
        if len(out['trajectory'])!=10 or any(set(t['atom_ids'])!=expected for t in trace):
            raise AssertionError('support or iteration count changed downstream')
    verification = {}
    if verify:
        repeat = model(y,pilot,noise,const,**common)
        torch.testing.assert_close(repeat['H_est'],a['H_est'],rtol=1e-5,atol=1e-6)
        if not np.array_equal(_bits_of_symbol(repeat['x_soft'].cpu().numpy(),cfg.N),
                              _bits_of_symbol(a['x_soft'].cpu().numpy(),cfg.N)):
            raise AssertionError('observer/repeat changed receiver hard bits')
        verification['observer_repeat'] = dict(
            H_bitexact=bool(torch.equal(repeat['H_est'],a['H_est'])),
            H_max_abs_difference=float((repeat['H_est']-a['H_est']).abs().max()), hard_bits_equal=True)
        del repeat
    truth = torch.from_numpy(frame['H'])
    denominator = float(np.linalg.norm(frame['H'])**2)
    projections, projection_metrics = {}, {}
    for arm, ids in supports.items():
        ids_t = torch.tensor(ids,dtype=torch.long)
        h,g = project_channel_on_support(truth,ids_t//(2*cfg.k_max+1),ids_t%(2*cfg.k_max+1)-cfg.k_max,
                                         cfg.c1,cfg.c2,cfg.k_max)
        expected = np.array([gains.get(i,0j) for i in ids])
        np.testing.assert_allclose(g.numpy(),expected,rtol=1e-10,atol=1e-11)
        lost = float(np.linalg.norm(frame['H']-h.numpy())**2/denominator)
        expected_loss = sum(abs(gain)**2 for i,gain in gains.items() if i not in ids)/sum(abs(gain)**2 for gain in gains.values())
        if abs(lost-expected_loss)>1e-10:
            raise AssertionError('coefficient energy and channel projection disagree')
        projections[arm] = h.to(device='cuda',dtype=cfg.dtype)
        projection_metrics[arm] = dict(E_repr=lost,true_gains=complex_record(g.numpy()),
                                       coefficient_projection_verified=True)
    rebuilt = system.gen_h_daft(np.array(list(gains.values())),
        np.array(list(gains))//(2*cfg.k_max+1),np.array(list(gains))%(2*cfg.k_max+1)-cfg.k_max)
    np.testing.assert_allclose(rebuilt,frame['H'],rtol=1e-10,atol=1e-11)
    # One detector entry for every endpoint. Cache identical H/sigma inputs.
    detector_cache = {}
    def detect(H,sigma):
        h_array = H.cpu().numpy()
        key = (array_hash(h_array),float(sigma))
        if key in detector_cache:
            return detector_cache[key]
        # Pilot cancellation in source precision, then the existing BP's complex128 conversion.
        y_data = frame['y']-h_array@frame['pilot']
        _,mu,var = mp_detect_bp_torch(y_data,h_array,float(sigma),const.cpu().numpy(),
            n_iter=20,threshold=cfg.bp_threshold,damp=.5,device='cuda',return_numpy=True,return_soft=True)
        if not np.isfinite(var).all():
            raise ValueError('nonfinite BP variance')
        result = count_errors(mu,frame['coded'])
        result.update(sigma2=float(sigma),H_hash=key[0],mu_hash=array_hash(mu),
                      nmse=float(np.linalg.norm(h_array-frame['H'])**2/denominator),
                      graph_edges=int(np.count_nonzero(np.abs(h_array.astype(np.complex128))>=cfg.bp_threshold)))
        detector_cache[key]=result
        return result
    stages = {}
    initial_gains = {}
    for stage,t in [('initial_ls',None),('first_receiver',0),('final_receiver',9)]:
        sigma_a = frame['sigma2'] if t is None else float(a['trajectory'][t]['sigma2'])
        arms = {}
        for arm,out in outputs.items():
            if t is None:
                ids = torch.tensor(supports[arm],dtype=torch.long,device='cuda')
                g = torch.linalg.lstsq(Phi[:,ids],y[:,None]).solution[:,0]
                H = reconstruct_H_torch(cfg.N,ids//(2*cfg.k_max+1),ids%(2*cfg.k_max+1)-cfg.k_max,
                                         g,cfg.c1,cfg.c2,cfg.k_max,cfg.dtype)
                sigma = sigma_a
                initial_gains[arm] = complex_record(g.cpu().numpy())
            else:
                H = out['trajectory'][t]['H_est']
                sigma = float(out['trajectory'][t]['sigma2'])
            arms[arm] = detect(H,sigma)
            if t is not None and arm!='A':
                arms[arm+'_sigmaA'] = detect(H,sigma_a)
        arms['C'] = detect(projections['A'],sigma_a)
        arms['D'] = detect(projections['B'],sigma_a)
        arms['E'] = detect(truth.to(device='cuda',dtype=cfg.dtype),sigma_a)
        arms['E_thermal'] = detect(truth.to(device='cuda',dtype=cfg.dtype),frame['sigma2'])
        stages[stage] = arms
    # Measured gain/threshold discrepancy, separated from representation loss.
    channel_errors = {}
    for arm,out in outputs.items():
        actual = out['H_est'].cpu().numpy().astype(np.complex128)
        ids_t = torch.tensor(supports[arm],dtype=torch.long)
        best,_ = project_channel_on_support(truth,ids_t//(2*cfg.k_max+1),ids_t%(2*cfg.k_max+1)-cfg.k_max,cfg.c1,cfg.c2,cfg.k_max)
        distance = float(np.linalg.norm(actual-best.numpy())**2/denominator)
        nmse = float(np.linalg.norm(actual-frame['H'])**2/denominator)
        closure = nmse-projection_metrics[arm]['E_repr']-distance
        if abs(closure)>1e-8:
            raise AssertionError('channel error decomposition failed')
        channel_errors[arm] = dict(nmse=nmse,excess_within_support=distance,closure=closure,
            raw_final_gains=complex_record(out['gains'].cpu().numpy()),
            final_ids=(out['support_delays']*(2*cfg.k_max+1)+out['support_dopplers']+cfg.k_max).tolist())
    if input_hashes != {k:array_hash(frame[k]) for k in input_hashes}:
        raise AssertionError('paired input mutated')
    torch.cuda.synchronize()
    return dict(replicate=replicate,frame_index=index,snr=snr,split='D_dev',uncoded=True,
        input_hashes=input_hashes,supports=supports,truth=ledger,
        quality=support_quality(raw,gains),projection=projection_metrics,
        initial_ls_gains=initial_gains,channel_errors=channel_errors,stages=stages,
        verification=verification,detector_calls=len(detector_cache),seconds=time.perf_counter()-started)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replicate',type=int,required=True)
    p.add_argument('--frames',type=int,default=16)
    p.add_argument('--snrs',type=int,nargs='+',default=[8,12,16])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--verify',action='store_true')
    args=p.parse_args()
    if args.frames<1 or args.replicate<0 or len(set(args.snrs))!=len(args.snrs):
        raise ValueError('invalid frame/SNR identity')
    if not torch.cuda.is_available():
        raise RuntimeError('deinlab CUDA required; no CPU fallback')
    torch.set_num_threads(4)
    args.out.mkdir(parents=True,exist_ok=False)
    status=dict(complete=False,started=time.time(),pid=os.getpid(),host=platform.node(),
                torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name(),
                replicate=args.replicate,frames=args.frames,snrs=args.snrs,completed=0,
                threads=torch.get_num_threads(),cpu_affinity=sorted(os.sched_getaffinity(0)))
    write_status(args.out/'status.json',status)
    try:
        system=_make_config_a(1024,2,8,10,4)
        model=build_model(system)
        status['config']={k:str(v) if isinstance(v,torch.dtype) else v for k,v in asdict(model.cfg).items()}
        status['generator']=dict(P_paths=system.P_paths,k_leak=system.k_leak,fs=system.fs,rho=float(system.rho))
        status['source_hashes']={str(f):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in Path('afdm_sp_joint_unrolled').rglob('*.py')}
        torch.cuda.reset_peak_memory_stats()
        with (args.out/'frames.jsonl').open('x') as stream:
            for i in range(args.frames):
                for snr in args.snrs:
                    result=run_frame(system,model,args.replicate,i,snr,verify=args.verify and i==0)
                    stream.write(json.dumps(result,allow_nan=False)+'\n');stream.flush()
                    status['completed']+=1
                    status['peak_allocated_mib']=torch.cuda.max_memory_allocated()/2**20
                    write_status(args.out/'status.json',status)
                    print(json.dumps(dict(frame=i,snr=snr,seconds=result['seconds'],
                        missed=len(result['quality']['missed_ids']),loss=result['quality']['missed_coefficient_energy'],
                        final={k:v['errors'] for k,v in result['stages']['final_receiver'].items()})),flush=True)
        status['complete']=True
    except Exception as error:
        status['failure']=repr(error)
        raise
    finally:
        status['ended']=time.time()
        write_status(args.out/'status.json',status)


if __name__=='__main__':
    main()
