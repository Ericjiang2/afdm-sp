"""Audit-only recovery of frozen PILOT-02 v1 engineering records."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np


ARMS = (('P02', 'stored_p0', 2), ('P03', 'stored_p0', 3),
        ('C33', 'b338', 3), ('P04', 'stored_p0', 4), ('C54', 'b855', 4))
SEED = 202609150401
DTYPE_RELATIVE_TOLERANCE = 2e-5  # Predeclared complex64 / double gate.
PRODUCER_V1_SHA256 = '95a55d9026ab3f91d4716d63618ce6e5ca676967ac714343598c0d74ea64a2aa'


def energy(v):
    return float(np.vdot(v, v).real)


def interpolate_fourfold(signal):
    signal = np.asarray(signal, dtype=np.complex128)
    spectrum = np.fft.fftshift(np.fft.fft(signal))
    padding = np.zeros(4 * len(signal), dtype=np.complex128)
    start = (len(padding) - len(spectrum)) // 2
    padding[start:start + len(spectrum)] = spectrum
    return 4 * np.fft.ifft(np.fft.ifftshift(padding))


def waveform(pilot, data, c1, c2, *, prefix_length):
    from afdm_sp_joint_unrolled.supplement_pilots import transform, cpp
    combined = np.asarray(pilot, dtype=np.complex128) + np.asarray(data, dtype=np.complex128)
    payload = transform(combined, c1, c2, inverse=True)
    extended = cpp(payload, c1, prefix_length)
    payload_power = abs(payload)**2
    mean = float(payload_power.mean())
    if mean <= 0 or not np.isfinite(mean):
        raise ValueError('zero or nonfinite payload power')
    native_peak = float(np.max(abs(extended)**2))
    oversampled_payload = interpolate_fourfold(payload)
    oversampled_cpp = interpolate_fourfold(extended)
    metrics = dict(pilot_energy=energy(pilot), data_energy=energy(data),
        pilot_data_cross=2 * float(np.vdot(pilot, data).real),
        payload_energy=energy(payload), cpp_prefix_energy=energy(extended[:prefix_length]),
        mean_payload_power=mean, native_payload_peak=float(payload_power.max()),
        native_cpp_peak=native_peak, native_gate_papr_db=float(10*np.log10(native_peak/mean)),
        oversampled_payload_peak=float(np.max(abs(oversampled_payload)**2)),
        oversampled_cpp_peak=float(np.max(abs(oversampled_cpp)**2)),
        oversampled_payload_papr_db=float(10*np.log10(np.max(abs(oversampled_payload)**2)/mean)),
        oversampled_cpp_papr_db=float(10*np.log10(np.max(abs(oversampled_cpp)**2)/mean)),
        passes_native_gate=bool(native_peak <= 16. and 10*np.log10(native_peak/mean) <= 12.),
        interpolation='4x centered DFT zero-pad; payload and finite CPP sequence separately',
        normalization='none; component power and pilot/data cross retained')
    return metrics


def physical_q(unit_A, offsets, variance):
    """Q for fixed diagonal symbol variance, grouped by physical q5 shifts."""
    unit_A=np.asarray(unit_A,dtype=np.complex128)
    offsets=np.asarray(offsets,dtype=np.int64)
    variance=np.asarray(variance,dtype=float)
    N,K=unit_A.shape
    if (offsets.shape!=(K,) or variance.shape!=(N,) or np.any(variance<0)
            or not np.isfinite(unit_A).all() or not np.isfinite(variance).all()):
        raise ValueError('physical Q requires finite matching unit operators and variance')
    Q=variance.sum()*np.eye(K,dtype=np.complex128)
    n=np.arange(N)
    aliases=0
    for shift in np.unique(offsets%N):
        ids=np.flatnonzero(offsets%N==shift)
        if len(ids)>1:
            aliases+=1
            phi=unit_A[(n+shift)%N][:,ids]
            Q[np.ix_(ids,ids)]=phi.conj().T@(variance[:,None]*phi)
    return Q,aliases


def verify_native_gram(A_native, saved_gram, saved_norms, saved_eigenvalues):
    """Match the producer's complex64 diagnostics and double LS Gram separately."""
    A_native = np.asarray(A_native)
    if A_native.dtype != np.complex64:
        raise ValueError('saved actual-support operator must retain native complex64 dtype')
    A = np.asarray(A_native, dtype=np.complex128)
    G = A.conj().T @ A
    norms=np.linalg.norm(A_native,axis=0)
    normalized=A_native/norms
    eig=np.linalg.eigvalsh(normalized.conj().T@normalized)
    if (np.linalg.norm(G-saved_gram)>1e-9*max(1.,np.linalg.norm(G))
            or np.linalg.norm(norms-saved_norms)>1e-9*max(1.,np.linalg.norm(norms))
            or np.linalg.norm(eig-saved_eigenvalues)>1e-9*max(1.,np.linalg.norm(eig))):
        raise FloatingPointError('saved actual-support Gram spectrum differs')
    return A,G


def verify_saved(v):
    """Recheck stored equations and summary metrics without a new initializer."""
    A,G=verify_native_gram(v['A_native'],v['gram'],v['column_norms'],
                           v['normalized_gram_eigenvalues'])
    A_exact = np.asarray(v['A_exact'], dtype=np.complex128)
    B = np.asarray(v['B'], dtype=np.complex128)
    if np.linalg.norm(G @ B - A.conj().T) > 1e-8 * max(1., np.linalg.norm(A)):
        raise FloatingPointError('saved LS affine equation differs')
    terms = v['error']['terms']; g = np.asarray(v['gS'], dtype=np.complex128)
    expected_map = (B @ A_exact - np.eye(len(g))) @ g
    if np.linalg.norm(terms['map'] - expected_map) > 1e-9 * max(1., np.linalg.norm(expected_map)):
        raise FloatingPointError('saved pilot map error differs')
    if len(terms) != 4 or len(v['error']['cross']) != 6:
        raise ValueError('pilot four-vector/six-cross accounting incomplete')
    for i, a in enumerate(terms):
        if abs(energy(terms[a])-v['error']['squares'][a]) > 1e-8 * max(1., energy(terms[a])):
            raise FloatingPointError('saved pilot term square differs')
        for b in list(terms)[i+1:]:
            cross = 2 * float(np.vdot(terms[a], terms[b]).real)
            if abs(cross-v['error']['cross'][f'{a}:{b}']) > 1e-8 * max(1., abs(cross)):
                raise FloatingPointError('saved pilot cross term differs')
    if np.linalg.norm(sum(terms.values()) + g - v['error']['physical_affine']) > 1e-8 * max(1., np.linalg.norm(g)):
        raise FloatingPointError('saved four-vector closure differs')
    if v['error']['dtype_rounding_relative'] > DTYPE_RELATIVE_TOLERANCE:
        raise FloatingPointError('saved pilot dtype gate differs')
    Q = np.asarray(v['Q_initial_model_unused'])
    recomputed,aliases=physical_q(v['unit_operator_design'],v['physical_offsets'],
                                  np.full(1024,.5))
    probe_variance=.5*(1+np.cos(2*np.pi*np.arange(1024)/1024))
    probe,probe_aliases=physical_q(v['unit_operator_design'],v['physical_offsets'],probe_variance)
    eigen=np.linalg.eigvalsh((Q+Q.conj().T)/2)
    if (Q.shape != (len(g),len(g)) or np.linalg.norm(Q-recomputed)>1e-8*max(1.,np.linalg.norm(recomputed))
            or aliases!=v['Q_physical_alias_groups']
            or np.linalg.norm(v['Q_colored_probe_only']-probe)>1e-8*max(1.,np.linalg.norm(probe))
            or probe_aliases!=v['Q_colored_probe_alias_groups']
            or np.linalg.norm(Q-Q.conj().T)>1e-8*max(1.,np.linalg.norm(Q))
            or eigen[0]<-1e-7 or np.any(v['Q_consumed'] != 0)):
        raise ValueError('initial theoretical Q was incorrectly consumed')
    row = v['schur']; q,h,z = (np.asarray(row[k]) for k in ('q','h','solved_q'))
    calculated = h - np.sum(q.conj()*z,axis=0).real
    threshold = np.finfo(float).eps * max(A.shape) * np.maximum(1.,h)
    valid = np.asarray(row['increment_valid'],dtype=bool)
    increment = np.zeros(len(h))
    increment[valid] = (1 + np.sum(abs(z[:,valid])**2,axis=0))/calculated[valid]
    if (np.linalg.norm(G @ z-q) > 1e-8 * max(1.,np.linalg.norm(q))
            or not np.array_equal(valid,calculated>threshold)
            or not np.array_equal(threshold,row['rank_threshold'])
            or np.linalg.norm(row['residual']-np.maximum(calculated,0)) > 1e-8 * max(1.,np.linalg.norm(calculated))
            or np.linalg.norm(row['white_variance_increment']-increment) > 1e-8 * max(1.,np.linalg.norm(increment))):
        raise FloatingPointError('saved pilot Schur equation differs')
    return True


def recovery_records(out, root, sha_fn):
    """Rebuild LightRun's entry list from closed reservations and saved results."""
    failure_path=out/'failure.json'
    failure=json.loads(failure_path.read_text())
    if (failure['status']!='FAILED' or failure['stage']!='engineering'
            or failure['calls']!={'A':20,'E':16} or failure['active'] is not None):
        raise ValueError('producer did not fail after 20 A and 16 E closed calls')
    if (out/'summary.json').exists() or (out/'summary-v2.json').exists():
        raise FileExistsError('original or recovered summary already exists')
    results=list(out.glob('*-result.json'))
    reservations=list(out.glob('*-reserve.json'))
    if len(results)!=36 or len(reservations)!=36:
        raise ValueError('saved result/reservation inventory does not close')
    ordered=[];tokens=set()
    for path in results:
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('result outside bound pilot root')
        record=json.loads(path.read_text())
        token=record['token']
        if token in tokens or path.name!=token+'-result.json':
            raise ValueError('duplicate or misplaced pilot result token')
        tokens.add(token)
        reservation_path=out/(token+'-reserve.json')
        reservation=json.loads(reservation_path.read_text())
        for key in ('token','kind','block','snr','split','arm'):
            if reservation[key]!=record[key]:
                raise ValueError('reservation/result identity mismatch: '+key)
        if (not isinstance(reservation['reserved_at'],(int,float))
                or not np.isfinite(reservation['reserved_at'])):
            raise ValueError('invalid pilot reservation clock')
        entry={key:record[key] for key in ('kind','block','snr','split','arm','seconds','CPU_seconds','scores')}
        entry.update(record=str(path),sha256=sha_fn(path))
        ordered.append((reservation['reserved_at'],entry))
    if {p.name for p in reservations}!={t+'-reserve.json' for t in tokens}:
        raise ValueError('unpaired pilot reservation')
    if tokens!={f'A-{i:05d}' for i in range(1,21)}|{f'E-{i:05d}' for i in range(1,17)}:
        raise ValueError('closed pilot call token ledger differs')
    clocks=[clock for clock,_ in ordered]
    if len(set(clocks))!=len(clocks):
        raise ValueError('ambiguous reservation ordering')
    return [entry for _,entry in sorted(ordered,key=lambda pair:pair[0])],failure


def main(args):
    root = args.root.resolve()
    source = (args.source or os.environ.get('AFDM_PILOT_SOURCE'))
    if not source:
        raise ValueError('explicit --source or AFDM_PILOT_SOURCE required for frozen source')
    source = Path(source).resolve(); sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    from afdm_sp_joint_unrolled.classical_joint_unrolled import (
        construct_sensing_matrix_torch, reconstruct_H_torch, physical_stride)
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    from afdm_sp_joint_unrolled.light_gap_replay import setup_guard, verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays

    contract = root/'contracts'/(args.tag+'.json'); c=json.loads(contract.read_text())
    manifest=source/'source-manifest.json'
    if sha(contract)!=args.contract_sha256 or sha(Path(__file__))!=args.script_sha256 or sha(manifest)!=c['source_sha256']:
        raise ValueError('pilot source/script/contract hash differs')
    producer_v1=Path(__file__).with_name('pilot_initial_runner_v1.py')
    if sha(producer_v1)!=PRODUCER_V1_SHA256:
        raise ValueError('frozen PILOT-02 producer v1 hash differs')
    stage=c['stage']; blocks=[0,20] if stage=='engineering' else [b for b in range(32) if b not in (0,20)]
    if stage!='engineering':
        raise ValueError('PILOT-02 v2 recovery supports only frozen engineering results')
    bounds=dict(A=20,E=16,seconds=7200) if stage=='engineering' else dict(A=300,E=240,seconds=7200)
    if (stage not in ('engineering','development') or c['schema']!=args.tag or c['tag']!=args.tag
            or c['blocks']!=blocks or c['snrs']!=[7,8] or c['arms']!=[x[0] for x in ARMS]
            or c['bounds']!=bounds or c['device']!='cpu' or c['threads']!=1
            or c['dtype_relative_tolerance']!=DTYPE_RELATIVE_TOLERANCE
            or c['order_seed']!=SEED or c['output_bytes']>20*1024**3):
        raise ValueError('frozen PILOT-02 stage contract differs')
    prediction_file=root/c['prediction_file']
    if sha(prediction_file)!=c['prediction_sha256']:
        raise ValueError('frozen prediction file hash differs')
    frozen=json.loads(prediction_file.read_text())['pilot_stage']
    if (frozen['N']!=1024 or frozen['rho']!=.5 or frozen['c1']!=.00244140625
            or frozen['c2']!=1.9751241797117955e-07 or frozen['l_max']!=102
            or frozen['K']!=24 or frozen['engineering_blocks']!=[0,20]
            or [(a['id'],a['pilot'],a['W']) for a in frozen['arms']]!=list(ARMS)
            or frozen['run_order']!='after fixed engineering blocks, seeded permutation of block/SNR/arm tasks; seed 202609150401'
            or frozen['signal_constraints']['native_payload_papr_db_max']!=12.
            or frozen['signal_constraints']['native_payload_peak_power_max']!=16.):
        raise ValueError('PILOT-02 prediction stage differs')
    pilot_file=root/c['new_pilots_file']
    if sha(pilot_file)!=c['new_pilots_sha256']:
        raise ValueError('frozen b338/b855 pilot file differs')
    with np.load(pilot_file) as z:
        if set(z.files)!={'b338','b855'}:
            raise ValueError('new pilot keys differ')
        new_pilots={k:np.array(z[k],copy=True) for k in z.files}
    if (any(p.shape!=(1024,) or not np.isfinite(p).all() or
            abs(energy(p)-512.)>1e-8 for p in new_pilots.values())
            or physical_stride(1024,0.00244140625)!=5):
        raise ValueError('new pilot/physical q5 geometry differs')
    if (np.count_nonzero(abs(new_pilots['b338'])>1e-8*max(abs(new_pilots['b338'])))!=1024
            or np.count_nonzero(abs(new_pilots['b855'])>1e-8*max(abs(new_pilots['b855'])))!=512):
        raise ValueError('frozen b338 full-bin / b855 half-bin layout differs')
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,
        source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    for sp,ap in c['audited_inputs'].items():
        receipt=json.loads((root/ap).read_text())
        if receipt['status']!='PASS' or receipt['summary_sha256']!=sha(root/sp):
            raise ValueError('upstream raw audit receipt differs')
    if stage=='development':
        receipt_path=root/c['engineering_receipt']; receipt=json.loads(receipt_path.read_text())
        if (receipt['status']!='PASS' or receipt['script_sha256']!=args.script_sha256
                or receipt['source_sha256']!=sha(manifest)
                or receipt['summary_sha256']!=sha(root/c['engineering_summary'])):
            raise ValueError('engineering receipt does not admit development')
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    upstream=json.loads((root/c['old_summary']).read_text())
    if upstream['status']!='COMPLETE' or len(upstream['records'])!=288:
        raise ValueError('old G1 summary incomplete')
    index={(e['kind'],e['block'],e['snr'],e['arm']):e for e in upstream['records']}
    if len(index)!=288:raise ValueError('duplicate old G1 records')
    best_cache={}

    def pair(block,snr,arm):
        pe=index['A',block,7,'G1_PROPAGATION']; ref=index['F',block,snr,'G1_FULL']
        _,physical=verified_record(pe,root); rr,full=verified_record(ref,root)
        raw,_=reuse_at_snr(physical['raw'],physical['diagnostics'],snr)
        baseline_obs={k:np.array(raw[k],copy=True) for k in ('y','pilot','sigma2')}
        baseline_obs['constellation']=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        if rr['observed_hashes']!=hashes(baseline_obs):
            raise ValueError('old FULL baseline observation hashes differ')
        if (len(full['dals'])!=9 or full['dals'][0]['outer_iter']!=1
                or raw['params']['c1']!=0.00244140625 or raw['params']['c2']!=1.9751241797117955e-07
                or raw['H'].shape!=(1024,1024)):
            raise ValueError('saved G1 physics/initialization differs')
        definition=next(x for x in ARMS if x[0]==arm)
        pilot=np.asarray(raw['pilot'] if definition[1]=='stored_p0' else new_pilots[definition[1]])
        y=(np.asarray(raw['y']) if definition[1]=='stored_p0' else
           np.asarray(raw['y'])+np.asarray(raw['H'])@(pilot-np.asarray(raw['pilot'])))
        if definition[1]=='stored_p0':np.testing.assert_array_equal(y,raw['y'])
        if (abs(energy(pilot)-512.)>1e-8 or len(raw['data'])!=1024
                or not np.isfinite(y).all()):
            raise ValueError('paired observed pilot/input invalid')
        return pe,ref,raw,full,definition,pilot,y

    def cached_p02(full,raw,pilot,y):
        first=full['dals'][0]; ids=first['support_delays']*5+first['support_dopplers']+2
        initial=full['initial_estimator']
        initial_trace=full['support_trace'][0]
        if (first['mode']!='mean' or len(ids)!=24 or set(ids.tolist())!=set(full['initial_estimator']['support'])
                or first['g_previous'].shape!=(24,) or initial['recipe']['id']!='B0-p2-s0.5'
                or initial['truth_access']!='none' or initial['omp_budget']!=24
                or initial.get('lstsq_driver')!='gels' or len(initial['support'])!=24
                or initial_trace['selected']!=initial['support']
                or initial_trace['expanded_atom_ids']!=ids.tolist()
                or set(full['support'])!=set(ids.tolist())
                or not np.array_equal(pilot,raw['pilot']) or not np.array_equal(y,raw['y'])
                or not np.array_equal(first['y'],np.asarray(y,dtype=np.complex64))):
            raise ValueError('old p0 initialization cache differs')
        Phi=construct_sensing_matrix_torch(1024,torch.as_tensor(pilot,dtype=torch.complex64),
            raw['params']['c1'],raw['params']['c2'],102,2,cdtype=torch.complex64).numpy()
        return dict(Phi=Phi,support_ids=np.asarray(ids,dtype=np.int64),
            gains=np.asarray(first['g_previous']),pilot=np.asarray(pilot),y=np.asarray(y),
            W=2,arm='P02',initializer_record=full['initial_estimator'],
            resource_counts=dict(initialization_CE=0,old_initialization_reused=1,
                                 extra_dictionary_builds=1,BP=0,LDPC=0,F=0))

    def raw_checks(summary):
        if summary['status']!='COMPLETE' or summary['calls']!=dict(A=len(blocks)*10,E=len(blocks)*8):
            raise ValueError('five-arm stage call bounds differ')
        if len(summary['records'])!=sum(summary['calls'].values()):
            raise ValueError('pilot record count differs')
        estimates={};rows=[];arrays=0
        resource_totals=dict(new_OMP_lstsq_solves=0,extra_affine_solves=0,
            extra_schur_solves=0,extra_gamma_solves=0,extra_Q_constructions=0,
            extra_unit_operator_builds=0,extra_oracle_projections=0)
        for e in summary['records']:
            record,v=verified_record(e,root)
            reservation=json.loads(Path(e['record']).with_name(record['token']+'-reserve.json').read_text())
            if any(reservation[k]!=record[k] or record[k]!=e[k] for k in ('kind','block','snr','arm','split')):
                raise ValueError('pilot reservation/result mismatch')
            key=(e['block'],e['snr'],e['arm'])
            if e['kind']=='E':
                if key in estimates or v['resource_counts']['initialization_CE']!=1:
                    raise ValueError('duplicate/nonreal initializer CE')
                if (v['initializer_record']['recipe']['id']!='B0-p2-s0.5'
                        or v['initializer_record']['omp_budget']!=24
                        or v['initializer_record']['truth_access']!='none'
                        or v['initializer_record'].get('lstsq_driver')!='gels'
                        or v['initializer_record']['support']!=v['support_ids'].tolist()
                        or len(v['support_ids'])!=24):
                    raise ValueError('saved source initializer contract differs')
                A=np.asarray(v['Phi'][:,v['support_ids']],dtype=np.complex128)
                y=np.asarray(v['y'],dtype=np.complex128)
                gains=np.asarray(v['gains'],dtype=np.complex128)
                stationarity=np.linalg.norm(A.conj().T@(A@gains-y))/max(1.,np.linalg.norm(A.conj().T@y))
                if stationarity>2e-5:
                    raise FloatingPointError('saved actual initializer LS normal residual differs')
                resource_totals['new_OMP_lstsq_solves']+=v['resource_counts']['OMP_lstsq_solves']
                estimates[key]=sha(Path(record['state']['file']['path']))
                arrays+=finite_arrays(v)
            elif e['kind']=='A':
                verify_saved(v)
                pe=index['A',e['block'],7,'G1_PROPAGATION']
                ref=index['F',e['block'],e['snr'],'G1_FULL']
                if (v['raw_p0_sha256']!=pe['sha256'] or v['reference_record_sha256']!=ref['sha256']
                        or record['physical_record_sha256']!=pe['sha256']):
                    raise ValueError('pilot analysis old source binding differs')
                _,physical=verified_record(pe,root)
                raw,_=reuse_at_snr(physical['raw'],physical['diagnostics'],e['snr'])
                W=v['W']
                td=torch.as_tensor(v['support_delays'],dtype=torch.long)
                tk=torch.as_tensor(v['support_dopplers'],dtype=torch.long)
                H=np.asarray(raw['H'],dtype=np.complex128)
                HS,gtrue=project_channel_on_support(torch.from_numpy(H),td,tk,
                    raw['params']['c1'],raw['params']['c2'],W)
                HS,gtrue=HS.numpy(),gtrue.numpy()
                if np.linalg.norm(gtrue-v['gS'])>1e-9*max(1.,np.linalg.norm(gtrue)):
                    raise FloatingPointError('saved selected true coefficients differ from projection')
                R=H-HS;p=np.asarray(v['pilot']);B=np.asarray(v['B'])
                noise=np.sqrt(float(raw['sigma2']))*np.asarray(raw['noise'])
                expected_terms=dict(map=(B@v['A_exact']-np.eye(24))@gtrue,
                    tail=B@(R@p),data=B@(H@raw['data']),noise=B@noise)
                for name,term in expected_terms.items():
                    if np.linalg.norm(v['error']['terms'][name]-term)>1e-8*max(1.,np.linalg.norm(term)):
                        raise FloatingPointError('saved pilot error term differs from raw: '+name)
                Hhat=reconstruct_H_torch(1024,torch.as_tensor(v['support_delays'],dtype=torch.long),
                    torch.as_tensor(v['support_dopplers'],dtype=torch.long),
                    torch.as_tensor(v['gains'],dtype=torch.complex64),
                    raw['params']['c1'],raw['params']['c2'],W,torch.complex64).numpy()
                h_error=energy(Hhat-H);hp_error=energy((Hhat-H)@p)
                if (abs(h_error-v['metrics']['H_squared_error'])>1e-8*max(1.,h_error)
                        or abs(hp_error-v['metrics']['Hp_squared_error'])>1e-8*max(1.,hp_error)
                        or abs(h_error/energy(H)-v['metrics']['H_NMSE'])>1e-8*max(1.,h_error/energy(H))
                        or abs(hp_error/energy(H@p)-v['metrics']['Hp_NMSE'])>1e-8*max(1.,hp_error/energy(H@p))):
                    raise FloatingPointError('saved H/Hp score differs from saved coefficients')
                expected_y=(np.asarray(raw['y']) if e['arm'] in ('P02','P03','P04') else
                    np.asarray(raw['y'])+H@(p-np.asarray(raw['pilot'])))
                if not np.array_equal(v['y'],expected_y):
                    raise ValueError('saved paired observation differs')
                expected_wave=waveform(p,raw['data'],raw['params']['c1'],raw['params']['c2'],prefix_length=102)
                if expected_wave!=v['metrics']['waveform']:
                    raise ValueError('saved waveform gate/oversampling differs')
                if (e['arm']!='P02' and record['estimator_state_sha256']!=estimates.get(key)):
                    raise ValueError('analysis not bound to initializer state')
                if e['arm']=='P02' and v['resource_counts']['initialization_CE']!=0:
                    raise ValueError('P02 old initialization was recomputed')
                if e['arm']=='P02':
                    _,_,old_raw,old_full,_,old_pilot,old_y=pair(e['block'],e['snr'],'P02')
                    old_est=cached_p02(old_full,old_raw,old_pilot,old_y)
                    if (not np.array_equal(v['support_ids'],old_est['support_ids'])
                            or not np.array_equal(v['gains'],old_est['gains'])
                            or not np.array_equal(v['pilot'],old_pilot)
                            or not np.array_equal(v['y'],old_y)):
                        raise ValueError('P02 did not reuse old initializer bytes')
                rows.append(dict(block=e['block'],snr=e['snr'],arm=e['arm'],W=v['W'],
                    H_NMSE=v['metrics']['H_NMSE'],Hp_NMSE=v['metrics']['Hp_NMSE'],
                    native_gate=v['metrics']['waveform']['passes_native_gate'],
                    source_ref=v['reference_record_sha256']))
                for key_name,total_name in (('extra_affine_solves','extra_affine_solves'),
                        ('extra_schur_solves','extra_schur_solves'),('extra_gamma_solves','extra_gamma_solves'),
                        ('extra_Q_constructions','extra_Q_constructions'),
                        ('extra_unit_operator_builds','extra_unit_operator_builds'),
                        ('extra_oracle_projection','extra_oracle_projections')):
                    resource_totals[total_name]+=v['resource_counts'][key_name]
                arrays+=finite_arrays(v)
            else:raise ValueError('unexpected PILOT-02 call kind')
        if {(r['block'],r['snr'],r['arm']) for r in rows}!={(b,s,a[0]) for b in blocks for s in (7,8) for a in ARMS}:
            raise ValueError('missing PILOT-02 paired work point')
        if (resource_totals['new_OMP_lstsq_solves']!=len(blocks)*8*25
                or resource_totals['extra_affine_solves']!=len(blocks)*10
                or resource_totals['extra_schur_solves']!=len(blocks)*10
                or resource_totals['extra_gamma_solves']!=len(blocks)*10
                or resource_totals['extra_Q_constructions']!=len(blocks)*10*4
                or resource_totals['extra_unit_operator_builds']!=len(blocks)*10
                or resource_totals['extra_oracle_projections']!=len(blocks)*3):
            raise ValueError('PILOT-02 analysis/OMP solve ledger differs')
        return dict(rows=rows,arrays=arrays,saved_records=len(summary['records']),
            logical_initializations=len(blocks)*10,actual_new_initialization_CE=len(blocks)*8,
            reused_original_p0=len(blocks)*2,new_BP=0,new_LDPC=0,new_F=0,
            resource_totals=resource_totals)

    out=root/'runs'/args.tag/stage
    if args.mode=='recover':
        records,failure=recovery_records(out,root,sha)
        summary=dict(status='COMPLETE',stage=stage,calls=failure['calls'],records=records,
            source_sha256=sha(manifest),script_sha256=PRODUCER_V1_SHA256,
            recovery_script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,
            scope=c['scope'],producer_status='FAILED_after_all_calls',
            original_failure_sha256=sha(out/'failure.json'),
            recovery_new_initialization_CE=0)
        summary['raw_checks']=raw_checks(summary)
        guard.verify()
        with (out/'summary-v2.json').open('x') as f:
            json.dump(summary,f,indent=2,allow_nan=False)
        print(json.dumps(dict(status='RECOVERED',calls=summary['calls'],
            summary_sha256=sha(out/'summary-v2.json'),new_initialization_CE=0)));return
    if args.mode=='audit-recovered':
        summary_path=out/'summary-v2.json'
        summary=json.loads(summary_path.read_text())
        if (summary['script_sha256']!=PRODUCER_V1_SHA256
                or summary['recovery_script_sha256']!=args.script_sha256
                or summary['contract_sha256']!=args.contract_sha256
                or summary['source_sha256']!=sha(manifest)
                or summary['original_failure_sha256']!=sha(out/'failure.json')
                or summary['producer_status']!='FAILED_after_all_calls'
                or summary['recovery_new_initialization_CE']!=0):
            raise ValueError('recovered pilot source/producer/failure identity differs')
        checks=raw_checks(summary)
        if checks!=summary['raw_checks']:
            raise ValueError('recovered pilot raw checks differ')
        guard.verify()
        checks.update(status='PASS',summary_sha256=sha(summary_path),
            producer_script_sha256=PRODUCER_V1_SHA256,
            recovery_script_sha256=args.script_sha256,source_sha256=sha(manifest),
            contract_sha256=args.contract_sha256,original_failure_sha256=sha(out/'failure.json'),
            audit_new_initialization_CE=0,scope=c['scope'],
            independence='main-session self-review; weak')
        receipt=root/'evidence'/(args.tag+'-'+stage+'-raw-audit-v2.json')
        with receipt.open('x') as f:
            json.dump(checks,f,indent=2,allow_nan=False)
        print(json.dumps({k:v for k,v in checks.items() if k!='rows'}));return
    raise ValueError('v2 performs audit-only recovery; no producer mode')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--source',type=Path)
    p.add_argument('--mode',choices=('recover','audit-recovered'),required=True)
    p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
