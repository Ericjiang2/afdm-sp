"""Truth-isolated preparation and terminal replay of restricted structure oracles."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import physical_cluster_weights,array_hash
from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger
from afdm_sp_joint_unrolled.direction_structure import fit
from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
from afdm_sp_joint_unrolled.direction_factorial import residual_ledger

ARMS=('free','group','link','sham')


def prepare(normal_path,system,data):
    """Regenerate geometry, prove exact pairing, and restrict every arm to same I."""
    normal_path=Path(normal_path);raw=normal_path.read_bytes();normal=json.loads(raw)
    if normal['split'] not in ('engineering','mechanism') or normal['call_type']!='full':
        raise ValueError('structure replay requires engineering/mechanism normal full receiver')
    if normal['failure'] is not None or normal['protocol_sha256']!=data.protocol_sha256:
        raise ValueError('invalid normal provenance')
    spath=Path(normal['snapshot']['path'])
    if hashlib.sha256(spath.read_bytes()).hexdigest()!=normal['snapshot']['sha256']:
        raise ValueError('normal snapshot hash mismatch')
    with np.load(spath,allow_pickle=False) as arrays:snapshot={k:arrays[k].copy() for k in arrays.files}
    frame=data.make_frame(system,normal['split'],normal['block_id'],normal['SNR'])
    if frame.metadata['input_hashes']!=normal['input_hashes']:
        raise ValueError('regenerated exogenous input differs from frozen normal record')
    for key,source in [('y',frame.observed['y']),('pilot',frame.observed['pilot']),
                       ('Htrue',frame._truth['H']),('info',frame._truth['info']),
                       ('coded',frame._truth['coded']),('data',frame._truth['data']),('noise',frame._truth['noise'])]:
        if array_hash(snapshot[key])!=array_hash(source):raise ValueError('snapshot/regeneration mismatch: '+key)
    support=np.asarray(snapshot['support'],dtype=int)
    if support.tolist()!=normal['S_submitted'] or len(np.unique(support))!=len(support):
        raise ValueError('normal support identity mismatch')
    params=frame._truth['params']
    truth=merged_truth_ledger(params,system.k_max_cap,threshold=0.)
    true_ids={e['column'] for e in truth['entries'] if e['above_threshold'] and e['column'] is not None
              and 0<=e['delay']<=system.l_max_cap}
    I=np.asarray(sorted(set(support)&true_ids),dtype=int)
    # Gains and emitted coefficients stay in this diagnostic container only.
    geometry={k:params[k] for k in ('taps','l_i','k_real')}
    basis=physical_cluster_weights(system,geometry)[I,:]
    if int(round(2*system.N_total*system.c1))!=2*system.k_max_cap+1:
        raise ValueError('dictionary/generator shift convention mismatch')
    Phi=construct_sensing_matrix(system.N_total,frame.observed['pilot'],system.c1,system.c2,
                                 system.l_max_cap,system.k_max_cap)[:,I]
    return {'normal':normal,'snapshot':snapshot,'I':I,'basis':basis,'Phi_I':Phi,
        'geometry':geometry,'normal_record_sha256':hashlib.sha256(raw).hexdigest(),
        'truth_support':sorted(true_ids),'pairing_verified':True}


def run_arm(prepared,system,code,arm,*,device,before_call,on_fit=None):
    """Fit from raw observation, then independently rebuild cancellation and BP."""
    if arm not in ARMS or not callable(before_call):raise ValueError('registered arm and call accounting required')
    s=prepared['snapshot'];I=prepared['I'];basis=prepared['basis']
    kwargs={'sigma_terminal':float(s['sigma2_terminal'])}
    if arm=='group':kwargs['incidence']=np.abs(basis)>0
    if arm in ('link','sham'):kwargs['basis']=basis
    before_call('CE',arm)
    start=time.perf_counter();cpu=time.process_time()
    fitted=fit(s['y'],prepared['Phi_I'],I,arm,**kwargs)
    fit_seconds=time.perf_counter()-start;fit_cpu=time.process_time()-cpu
    if fitted['atom_ids']!=I.tolist():raise AssertionError('fit changed shared support')
    if on_fit is not None:on_fit(fitted,fit_seconds,fit_cpu)
    gains=fitted['coefficients'];K=2*system.k_max_cap+1
    H=system.gen_h_daft(gains,I//K,I%K-system.k_max_cap)
    # No hidden renormalization or omitted-support fill.
    z=s['y']-H@s['pilot']
    residual=residual_ledger(s,H,H)
    before_call('terminal',arm)
    dev=torch.device(device)
    if dev.type=='cuda':torch.cuda.synchronize(dev);torch.cuda.reset_peak_memory_stats(dev)
    start=time.perf_counter();cpu=time.process_time()
    result=terminal_decode(z,H,float(s['sigma2_terminal']),s['constellation'],code,device=dev,audit=True)
    if dev.type=='cuda':torch.cuda.synchronize(dev)
    result.update(device=str(dev),arm_id='M_'+arm,atom_ids=I.tolist(),coefficients=gains,Hfit=H,
        fit_diagnostics=fitted['diagnostics'],fit_seconds=fit_seconds,fit_cpu_seconds=fit_cpu,
        terminal_seconds=time.perf_counter()-start,terminal_cpu_seconds=time.process_time()-cpu,
        peak_gpu_bytes=int(torch.cuda.max_memory_allocated(dev)) if dev.type=='cuda' else 0,
        residual=residual,Hfit_sha256=array_hash(H),z_sha256=array_hash(z),
        sigma2_terminal=float(s['sigma2_terminal']),candidate_eligible=False,
        truth_access_level='geometry_oracle',
        oracle_information='support+template' if arm in ('link','sham') else 'support+incidence' if arm=='group' else 'support')
    result['info_errors']=int(np.count_nonzero(result['info_hat']!=s['info']))
    result['FER']=int(result['info_errors']>0)
    return result
