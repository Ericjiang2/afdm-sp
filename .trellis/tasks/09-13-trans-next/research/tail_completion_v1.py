"""Read-only finite integer-tail completion on saved G1/ridge CE states.

Only the actual-core/actual-centre arm is a legal receiver-side candidate.
The other arms use truth for diagnosis, and every arm is scored against its
own identical-core F=0 baseline. No receiver, CE, BP or LDPC call is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

SNRS = (7, 8)
STATES = (1, 9)
ARMS = ('oracle_true_core_mixed_true_centre',
        'oracle_actual_core_mixed_true_centre',
        'deploy_actual_core_actual_centre')
N = 1024
Q = .01
K_TAIL = 5
STRIDE = 5


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(value):
    a = np.ascontiguousarray(value)
    return hashlib.sha256(str((a.shape, a.dtype)).encode() + a.tobytes()).hexdigest()


def positive_fft_coefficient(n, integer_offset, kappa):
    """FFT of exp(+2πi κ n/N) at bin r, r=integer_bin-centre."""
    r = np.asarray(integer_offset)[None, :]
    u = np.asarray(kappa)[:, None] - r
    # Stable at exact integer u, including the r=0, κ=0 node.
    return np.exp(1j * np.pi * (n - 1) * u / n) * np.sinc(u) / np.sinc(u / n)


def predictor(n, core_k, tail_k, centre, q=Q, quadrature=128):
    core_k = np.asarray(core_k, dtype=np.int64)
    tail_k = np.asarray(tail_k, dtype=np.int64)
    require(core_k.ndim == tail_k.ndim == 1 and len(core_k) > 0
            and len(np.unique(core_k)) == len(core_k)
            and len(np.unique(tail_k)) == len(tail_k)
            and not set(core_k).intersection(tail_k), 'invalid core/tail integer bins')
    require(n >= 8 and quadrature == 128 and q == Q and isinstance(centre, (int, np.integer)),
            'unfrozen predictor parameter')
    if not len(tail_k):
        return np.zeros((0, len(core_k)), np.complex128)
    nodes, weights = np.polynomial.legendre.leggauss(quadrature)
    kappa, weights = nodes / 2, weights / 2
    core = positive_fft_coefficient(n, core_k - centre, kappa)
    tail = positive_fft_coefficient(n, tail_k - centre, kappa)
    rss = core.T @ (weights[:, None] * core.conj())
    rts = tail.T @ (weights[:, None] * core.conj())
    f = np.linalg.solve(rss + q * np.eye(len(core_k)), rts.conj().T).conj().T
    require(np.isfinite(f).all(), 'nonfinite F')
    return f


def support_and_tail(delays, dopplers, n=N):
    l = np.asarray(delays, dtype=np.int64)
    k = np.asarray(dopplers, dtype=np.int64)
    require(l.shape == k.shape == (24,) and np.all((0 <= l) & (l < n))
            and np.all(np.abs(k) <= 2), 'ridge original S24 geometry differs')
    support = tuple((int(a), int(b)) for a, b in zip(l, k))
    require(len(set(support)) == 24, 'ridge S24 has repeated physical atom')
    tail = tuple((delay, bin_k) for delay in sorted(set(l.tolist()))
                 for bin_k in range(-K_TAIL, K_TAIL + 1)
                 if (delay, bin_k) not in support)
    require(not set(support).intersection(tail), 'finite tail overlaps original core')
    return support, tail


def actual_centres(support, z):
    z = np.asarray(z)
    require(z.shape == (24,) and np.isfinite(z).all(), 'invalid actual ridge core')
    out = {}
    for delay in sorted({l for l, _ in support}):
        chosen = sorted(((-abs(z[i]), k) for i, (l, k) in enumerate(support) if l == delay))[0]
        out[delay] = int(chosen[1])
    return out


def mixed_true_centres(support, actual, true_delays, true_dopplers):
    td = np.asarray(true_delays)
    tk = np.asarray(true_dopplers)
    require(td.ndim == tk.ndim == 1 and td.shape == tk.shape and np.isfinite(td).all()
            and np.isfinite(tk).all() and np.all(td == np.floor(td)),
            'invalid saved physical path geometry')
    out = dict(actual)
    counts = dict(unique=0, missing=0, multi=0, replaced=0)
    for l in sorted({x for x, _ in support}):
        hits = np.flatnonzero(td == l)
        if len(hits) == 1:
            c = int(np.rint(tk[hits[0]]))
            counts['unique'] += 1
            counts['replaced'] += int(c != actual[l])
            out[l] = c
        elif len(hits) == 0:
            counts['missing'] += 1
        else:
            counts['multi'] += 1
    require(sum(counts[k] for k in ('unique', 'missing', 'multi')) == len(out),
            'mixed oracle centre coverage differs')
    return out, counts


def completed_tail(support, tail, z, centres, n=N, cache=None, calls=None):
    """Predict only T; support coefficients z are returned unchanged by caller."""
    z = np.asarray(z, dtype=np.complex128)
    require(z.shape == (len(support),) and np.isfinite(z).all()
            and set(centres) == {l for l, _ in support}, 'invalid centre/core inventory')
    out = np.zeros(len(tail), dtype=np.complex128)
    for l in sorted(centres):
        si = [i for i, (d, _) in enumerate(support) if d == l]
        ti = [i for i, (d, _) in enumerate(tail) if d == l]
        sk = tuple(support[i][1] for i in si)
        tk = tuple(tail[i][1] for i in ti)
        key = (n, sk, tk, centres[l])
        if cache is not None and key in cache:
            f = cache[key]
            if calls is not None: calls['F_cache_hits'] += 1
        else:
            f = predictor(n, sk, tk, centres[l])
            if cache is not None: cache[key] = f
            if calls is not None: calls['F_matrix_solves'] += 1
        out[ti] = f @ z[si]
    require(np.isfinite(out).all(), 'nonfinite finite-tail output')
    return out


def atom_action(n, c1, c2, atoms, gains, signal, calls=None):
    """Full CPP/DAFT integer U action; row-shift aliases retain delay phase."""
    x = np.asarray(signal, dtype=np.complex128)
    g = np.asarray(gains, dtype=np.complex128)
    require(x.shape == (n,) and len(atoms) == len(g)
            and len(set(atoms)) == len(atoms) and np.isfinite(x).all()
            and np.isfinite(g).all() and abs(2 * n * c1 - STRIDE) < 1e-10,
            'invalid physical U action')
    cols = np.arange(n, dtype=np.int64)
    out = np.zeros(n, dtype=np.complex128)
    for (l, k), gain in zip(atoms, g):
        if gain == 0: continue
        rows = (cols + STRIDE * l + k) % n
        angle = 2 * np.pi * (-c1 * l * l + c2 * (rows.astype(float)**2 - cols.astype(float)**2)
                             - l * cols / n)
        out[rows] += gain * np.exp(1j * angle) * x
        if calls is not None: calls['nonzero_atom_actions'] += 1
    return out


def direct_projection(H, n, c1, c2, atoms, calls=None):
    """Direct Frobenius projection; no shift-only alias approximation."""
    require(H.shape == (n, n) and np.isfinite(H).all()
            and len(set(atoms)) == len(atoms), 'invalid physical H projection')
    cols = np.arange(n, dtype=np.int64)
    gains = np.empty(len(atoms), dtype=np.complex128)
    for i, (l, k) in enumerate(atoms):
        rows = (cols + STRIDE * l + k) % n
        angle = 2 * np.pi * (-c1 * l * l + c2 * (rows.astype(float)**2 - cols.astype(float)**2)
                             - l * cols / n)
        gains[i] = np.sum(np.exp(-1j * angle) * H[rows, cols]) / n
        if calls is not None: calls['Frobenius_atom_projections'] += 1
    return gains


def alias_gram_check(n, c1, c2):
    """Engineering check: (1,5) and (2,0) share shift but not atom."""
    atoms=((1,5),(2,0))
    cols=np.arange(n,dtype=np.int64)
    phases=[]
    for l,k in atoms:
        rows=(cols+STRIDE*l+k)%n
        angle=2*np.pi*(-c1*l*l+c2*(rows.astype(float)**2-cols.astype(float)**2)
                       -l*cols/n)
        phases.append(np.exp(1j*angle))
    same_shift=(STRIDE*atoms[0][0]+atoms[0][1])==(STRIDE*atoms[1][0]+atoms[1][1])
    gram=np.vdot(phases[0],phases[1])/n
    require(same_shift and abs(gram)<=1e-10,
            'physical alias U atoms wrongly collapsed by row shift')
    return float(abs(gram))


def physical_fft_coefficients(n, atoms, true_delays, true_dopplers, true_gains):
    """CPP true coefficients from saved physical paths, independently of H."""
    d, k, g = map(np.asarray, (true_delays, true_dopplers, true_gains))
    require(d.shape == k.shape == g.shape and d.ndim == 1 and np.isfinite(g).all(),
            'invalid physical path bank')
    samples = np.arange(n)
    by_delay = {}
    for delay in set(l for l, _ in atoms):
        hits = d == delay
        modulation = np.sum(g[hits, None] * np.exp(2j * np.pi * k[hits, None] * samples / n), axis=0)
        by_delay[delay] = np.fft.fft(modulation) / n
    return np.array([by_delay[l][bin_k % n] for l, bin_k in atoms], dtype=np.complex128)


def projected_energy(H_energy, gains, n):
    residual = H_energy - n * float(np.vdot(gains, gains).real)
    require(residual >= -1e-8 * max(1., H_energy), 'physical projection energy exceeds truth')
    return max(0., residual)


def score_pair(H_energy, true_response, signal, n, c1, c2, support, tail,
               truth_st, z, tail_hat, calls=None):
    """Same-core completed/F=0 scores, truth read only at this boundary."""
    truth_s, truth_t = truth_st[:len(support)], truth_st[len(support):]
    z, tail_hat = map(lambda x: np.asarray(x, dtype=np.complex128), (z, tail_hat))
    require(z.shape == truth_s.shape and tail_hat.shape == truth_t.shape
            and np.isfinite(z).all() and np.isfinite(tail_hat).all(), 'invalid score inventory')
    residual_st = projected_energy(H_energy, truth_st, n)
    core_error = n * float(np.vdot(z - truth_s, z - truth_s).real)
    baseline_H = residual_st + core_error + n * float(np.vdot(truth_t, truth_t).real)
    completed_H = residual_st + core_error + n * float(np.vdot(tail_hat - truth_t, tail_hat - truth_t).real)
    truth_y_energy = float(np.vdot(true_response, true_response).real)
    require(H_energy > 0 and truth_y_energy > 0, 'zero physical scoring denominator')
    core_y = atom_action(n, c1, c2, support, z, signal, calls)
    tail_y = atom_action(n, c1, c2, tail, tail_hat, signal, calls)
    baseline_R = float(np.vdot(true_response - core_y, true_response - core_y).real)
    completed_R = float(np.vdot(true_response - core_y - tail_y,
                                true_response - core_y - tail_y).real)
    return dict(H_NMSE_baseline=baseline_H/H_energy,
                H_NMSE_completed=completed_H/H_energy,
                H_delta=(completed_H-baseline_H)/H_energy,
                response_NMSE_baseline=baseline_R/truth_y_energy,
                response_NMSE_completed=completed_R/truth_y_energy,
                response_delta=(completed_R-baseline_R)/truth_y_energy)


def legal_intervals(rows):
    legal = [r for r in rows if r['arm'] == ARMS[2]]
    require(len(legal) == 128, 'legal 32x2x2 state inventory differs')
    idx = {(r['block'], r['snr'], r['t']):r for r in legal}
    values = np.empty((32, 4), dtype=float)
    for b in range(32):
        for j, (t, key) in enumerate(((1,'H_delta'),(1,'response_delta'),
                                    (9,'H_delta'),(9,'response_delta'))):
            values[b,j] = np.mean([idx[b,s,t]['scores'][key] for s in SNRS])
    rng = np.random.default_rng(202609150701)
    draw = rng.integers(0, 32, size=(20000, 32))
    boot = values[draw].mean(axis=1)
    names = ('t1_H','t1_response','t9_H','t9_response')
    return {name:dict(mean=float(values[:,j].mean()),
                      simultaneous_95_percentile=[float(x) for x in np.quantile(boot[:,j],
                                                                               [.00625,.99375])],
                      per_channel_values=[float(x) for x in values[:,j]])
            for j, name in enumerate(names)}


def memory_preflight():
    info = Path('/proc/meminfo')
    if not info.exists(): return {'local_test':'no Linux MemAvailable'}
    available = int(next(line.split()[1] for line in info.read_text().splitlines()
                         if line.startswith('MemAvailable:'))) * 1024
    conservative = 4 * 2**30
    require(available >= 2 * conservative, 'insufficient free memory for bounded analysis')
    return dict(MemAvailable_bytes=available, conservative_peak_bytes=conservative)


def assert_threads():
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
        require(os.environ.get(key) == '1', 'single-thread environment missing: '+key)


def source_guard(args, contract):
    from afdm_sp_joint_unrolled import light_gap_replay
    package = Path(light_gap_replay.__file__).resolve().parent
    require(package == (args.source_dir/'afdm_sp_joint_unrolled').resolve(),
            'imported package differs from frozen analysis source')
    require(sha(args.source_manifest) == contract['source_binding']['analysis_ce_source_v4_manifest_sha256'],
            'source manifest hash differs')
    manifest = json.loads(args.source_manifest.read_text())
    inventory = {str(p.relative_to(package)) for p in package.rglob('*.py')}
    require(set(manifest) == inventory and all(sha(package/name) == digest
            for name,digest in manifest.items()), 'source inventory/hash differs')
    old_manifest_path=args.ridge_root/'source-v4/source-manifest.json'
    require(sha(old_manifest_path)==contract['source_binding']['original_ridge_production_manifest_sha256'],
            'old ridge production source manifest differs')
    old_manifest=json.loads(old_manifest_path.read_text())
    for name in ('supplement_g1.py','supplement_pilots.py','light_gap_replay.py'):
        require(manifest[name]==old_manifest[name],
                'physical/source reading module differs across old ridge and analysis: '+name)
    require(manifest['classical_joint_unrolled.py']!=old_manifest['classical_joint_unrolled.py'],
            'analysis/old receiver lineage distinction lost')


def input_guard(args, contract):
    bound = contract['source_binding']
    paths = {
        'original_ridge_production_manifest_sha256': args.ridge_root/'source-v4/source-manifest.json',
        'ridge_engineering_summary_sha256': args.ridge_root/'engineering/summary.json',
        'ridge_engineering_raw_audit_sha256': args.ridge_root/'audit/engineering.json',
        'ridge_development_summary_sha256': args.ridge_root/'development/summary.json',
        'ridge_development_raw_audit_sha256': args.ridge_root/'audit/development.json',
        'g1_physical_summary_sha256': args.old_root/'runs/g1-strong-development-recovery-v1/development/summary.json',
        'g1_physical_raw_audit_sha256': args.old_root/'evidence/g1-strong-development-recovery-v1-raw-audit.json',
    }
    require(all(sha(path)==bound[key] for key,path in paths.items()), 'saved source summary/audit hash differs')
    for phase in ('engineering','development'):
        summ=json.loads((args.ridge_root/phase/'summary.json').read_text())
        audit=json.loads((args.ridge_root/'audit'/f'{phase}.json').read_text())
        require(summ['status']=='COMPLETE' and audit['status']=='PASS'
                and audit['summary_sha256']==sha(args.ridge_root/phase/'summary.json'),
                'ridge source audit differs')
    g=json.loads(paths['g1_physical_summary_sha256'].read_text())
    ga=json.loads(paths['g1_physical_raw_audit_sha256'].read_text())
    require(g['status']=='COMPLETE' and ga['status']=='PASS'
            and ga['summary_sha256']==sha(paths['g1_physical_summary_sha256']),
            'G1 physical source audit differs')


def load_index(args):
    ridge = [json.loads((args.ridge_root/phase/'summary.json').read_text())
             for phase in ('engineering','development')]
    physical = json.loads((args.old_root/'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    ri={(e['block'],e['snr']):e for d in ridge for e in d['records']
        if e['kind']=='F' and e['arm']=='ridge'}
    gi={e['block']:e for e in physical['records']
        if e['kind']=='A' and e['snr']==7 and e['arm']=='G1_PROPAGATION'}
    require(set(ri)=={(b,s) for b in range(32) for s in SNRS}
            and set(gi)==set(range(32)) and len(ri)==64 and len(gi)==32,
            'saved G1/ridge physical work-point inventory differs')
    return ri,gi


def collect_rows(args, contract, started, on_engineering=None):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch
    import torch
    ri,gi=load_index(args)
    rows=[]
    calls=dict(ridge_F_record_reads=0,physical_A_record_reads=0,
               Frobenius_atom_projections=0,F_matrix_solves=0,F_cache_hits=0,
               nonzero_atom_actions=0,true_response_matvec=0,
               physical_fft_coefficients=0,score_pairs=0,
               saved_A_reconstructions=0,saved_A_column_action_checks=0,
               saved_A_core_action_checks=0,alias_gram_engineering_checks=0,
               saved_H_action_differences=0)
    fcache={}
    block_order=(0,20)+tuple(b for b in range(32) if b not in (0,20))
    for b in block_order:
        require(time.monotonic()-started < 7200, 'tail analysis wall cap reached')
        physical_record, physical = verified_record(gi[b], args.old_root)
        calls['physical_A_record_reads'] += 1
        raw=physical['raw']; params=raw['params']
        H=np.asarray(raw['H'],dtype=np.complex128)
        p=np.asarray(raw['pilot'],dtype=np.complex128)
        d=np.asarray(raw['data'],dtype=np.complex128)
        require(H.shape==(N,N) and p.shape==d.shape==(N,)
                and params['representation']=='physical_cpp_untruncated'
                and abs(2*N*params['c1']-STRIDE)<1e-10,
                'saved physical CPP geometry differs')
        if b==0:
            alias_gram_check(N,params['c1'],params['c2'])
            calls['alias_gram_engineering_checks']+=1
        x=p+d
        true_y=H@x; calls['true_response_matvec']+=1
        require(np.linalg.norm(true_y-raw['noiseless'])<=1e-9*max(1.,np.linalg.norm(true_y)),
                'saved physical CPP noiseless response differs')
        H_energy=float(np.vdot(H,H).real)
        projections={}
        for snr in SNRS:
            ridge_record, ridge=verified_record(ri[b,snr],args.ridge_root)
            calls['ridge_F_record_reads']+=1
            require(ridge_record['strength']==.1 and ridge_record['physical_record_sha256']==gi[b]['sha256']
                    and len(ridge['dals'])==9 and ridge_record['truth_access']=='error scoring only',
                    'ridge F/source binding differs')
            state0=ridge['dals'][0]
            support,tail=support_and_tail(state0['support_delays'],state0['support_dopplers'])
            for state in ridge['dals']:
                require(tuple(zip(state['support_delays'].tolist(),state['support_dopplers'].tolist()))==support,
                        'ridge S changes within saved nine-state frame')
            st=support+tail
            key=(support,tail)
            if key not in projections:
                coeff=direct_projection(H,N,params['c1'],params['c2'],st,calls)
                expected=physical_fft_coefficients(N,st,params['l_i'],params['k_real'],params['g_i'])
                calls['physical_fft_coefficients']+=len(st)
                require(np.max(abs(coeff-expected))<=2e-9*max(1.,np.max(abs(expected))),
                        'saved physical H/CPP FFT/DAFT U projection differs')
                ES=projected_energy(H_energy,coeff[:24],N)
                EST=projected_energy(H_energy,coeff,N)
                require(ES+1e-8*max(1.,H_energy)>=EST,
                        'finite tail cannot increase physical projection residual')
                projections[key]=(coeff,ES,EST)
            coeff,ES,EST=projections[key]
            for t in STATES:
                state=ridge['dals'][t-1]
                z=np.asarray(state['g_solution'],dtype=np.complex128)
                require(z.shape==(24,) and np.isfinite(z).all()
                        and np.array_equal(z,np.asarray(state['g_solution'],dtype=np.complex128)),
                        'actual ridge core changed')
                mu=np.asarray(state['mu'],dtype=np.complex128)
                saved_A=np.asarray(state['A'],dtype=np.complex128)
                require(mu.shape==(N,) and saved_A.shape==(N,24),
                        'ridge saved CE design/core shape differs')
                x_ce=p+mu
                new_A=build_A_for_DALS_torch(N,torch.from_numpy(np.array(state0['support_delays'],dtype=np.int64)),
                    torch.from_numpy(np.array(state0['support_dopplers'],dtype=np.int64)),
                    torch.from_numpy(x_ce),params['c1'],params['c2'],2).numpy()
                calls['saved_A_reconstructions']+=1
                relative=float(np.linalg.norm(saved_A-new_A)/max(1.,np.linalg.norm(saved_A)))
                require(relative<=2e-5,'ridge saved A differs from analysis physical U(p+mu)')
                for i,atom in enumerate(support):
                    column=atom_action(N,params['c1'],params['c2'],(atom,),(1.+0j,),x_ce)
                    calls['saved_A_column_action_checks']+=1
                    require(np.linalg.norm(column-saved_A[:,i])<=2e-5*max(1.,np.linalg.norm(saved_A[:,i])),
                            'ridge saved A column differs from full physical CPP integer U')
                original_core_response=atom_action(N,params['c1'],params['c2'],support,z,x_ce)
                saved_core_response=saved_A@z
                calls['saved_A_core_action_checks']+=1
                require(np.linalg.norm(original_core_response-saved_core_response)
                        <=2e-5*max(1.,np.linalg.norm(saved_core_response)),
                        'saved ridge A@g_solution differs from F=0 physical U action')
                saved_H=np.asarray(state['H'],dtype=np.complex128)
                require(saved_H.shape==(N,N) and np.isfinite(saved_H).all(),
                        'saved ridge lifecycle H differs')
                H_lifecycle_action=saved_H@x_ce
                calls['saved_H_action_differences']+=1
                saved_H_vs_current_core=float(np.linalg.norm(H_lifecycle_action-saved_core_response)
                    /max(1.,np.linalg.norm(saved_core_response)))
                actual=actual_centres(support,z)
                mixed,coverage=mixed_true_centres(support,actual,params['l_i'],params['k_real'])
                for arm in ARMS:
                    core=coeff[:24] if arm==ARMS[0] else z
                    centres=actual if arm==ARMS[2] else mixed
                    tail_hat=completed_tail(support,tail,core,centres,N,fcache,calls)
                    scores=score_pair(H_energy,true_y,x,N,params['c1'],params['c2'],support,tail,
                                      coeff,core,tail_hat,calls)
                    calls['score_pairs']+=1
                    rows.append(dict(block=b,snr=snr,t=t,arm=arm,scores=scores,
                        ridge_F_record_sha256=ri[b,snr]['sha256'],
                        physical_A_record_sha256=gi[b]['sha256'],
                        original_S_sha256=array_sha(np.array(support,dtype=np.int64)),
                        ridge_g_solution_sha256=array_sha(z),
                        used_core_sha256=array_sha(core),
                        centre_map={str(k):int(v) for k,v in centres.items()},
                        saved_A_relative_reconstruction_error=relative,
                        saved_lifecycle_H_vs_current_core_action_relative=saved_H_vs_current_core,
                        mixed_oracle_coverage=coverage if arm!=ARMS[2] else None,
                        S_atoms=24,T_atoms=len(tail),nonzero_tail_atoms=int(np.count_nonzero(tail_hat)),
                        projection_residual_S=ES/H_energy,
                        projection_residual_S_union_T=EST/H_energy,
                        finite_tail_coverable_energy=(ES-EST)/H_energy))
        if b==20 and on_engineering is not None:
            require(len(rows)==24 and calls['ridge_F_record_reads']==4
                    and calls['physical_A_record_reads']==2
                    and calls['saved_A_reconstructions']==8
                    and calls['alias_gram_engineering_checks']==1,
                    'engineering 0/20 admission inventory differs')
            on_engineering(rows,calls)
    require(len(rows)==384 and calls['score_pairs']==384 and calls['ridge_F_record_reads']==64
            and calls['physical_A_record_reads']==32,
            'run inventory or score accounting differs')
    return rows,calls


def main():
    parser=argparse.ArgumentParser()
    for name in ('contract','source_dir','source_manifest','old_root','ridge_root','output_dir'):
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--script-sha256',required=True)
    args=parser.parse_args()
    started=time.monotonic()
    assert_threads()
    require(sha(__file__)==args.script_sha256 and sha(args.contract)==args.contract_sha256,
            'frozen analysis source/contract hash differs')
    contract=json.loads(args.contract.read_text())
    require(contract['schema']=='tail-completion-contract-v1'
            and contract['status']=='FROZEN_AFTER_INDEPENDENT_REVIEW'
            and contract['method_md_sha256']==sha(Path(__file__).with_name('tail_completion_contract_v1.md')),
            'TAIL contract not independently frozen')
    require(not args.output_dir.exists(), 'output directory already exists')
    source_guard(args,contract)
    input_guard(args,contract)
    preflight=memory_preflight()
    args.output_dir.mkdir(parents=True)
    def engineering_admission(partial, current_calls):
        source_guard(args,contract)
        input_guard(args,contract)
        engineering_path=args.output_dir/'engineering-rows.json'
        engineering_path.write_text(json.dumps(partial,indent=2,ensure_ascii=False)+'\n')
        receipt=dict(schema='tail-completion-engineering-admission-v1',status='PASS',
            blocks=[0,20],snrs=[7,8],states=[1,9],arms=list(ARMS),
            pair_comparisons=24,rows_sha256=sha(engineering_path),
            script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,
            calls_at_gate=dict(current_calls),wall_seconds_at_gate=time.monotonic()-started,
            note='all saved A/source/CPP projection/alias and layer comparisons passed before other physical blocks')
        (args.output_dir/'engineering-admission.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    rows,calls=collect_rows(args,contract,started,engineering_admission)
    rows_path=args.output_dir/'rows.json'
    rows_path.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    summary=dict(schema='tail-completion-run-v1',status='COMPLETE',
        input_binding=contract['source_binding'],contract_sha256=args.contract_sha256,
        script_sha256=args.script_sha256,source_manifest_sha256=sha(args.source_manifest),
        rows_sha256=sha(rows_path),work_points=64,pair_comparisons=384,
        legal_four_endpoints=legal_intervals(rows),calls=calls,
        new_F=0,new_CE=0,new_BP=0,new_LDPC=0,
        memory_preflight=preflight,wall_seconds=time.monotonic()-started,
        peak_resident_bytes=__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss*1024)
    (args.output_dir/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    # Re-read original records with the same code as a weak self-audit. Its
    # recomputed projection/F/action/score calls are explicitly counted.
    fresh,acalls=collect_rows(args,contract,started)
    require(len(fresh)==len(rows) and all(a==b for a,b in zip(fresh,rows)),
            'source re-read differs from saved tail comparison rows')
    source_guard(args,contract)
    input_guard(args,contract)
    require(sha(__file__)==args.script_sha256 and sha(args.contract)==args.contract_sha256,
            'TAIL analysis source changed during run')
    audit=dict(schema='tail-completion-raw-audit-v1',status='PASS',
               summary_sha256=sha(args.output_dir/'summary.json'),rows_sha256=sha(rows_path),
               reread_calls=acalls,independence='same-process source re-read; weak',
               new_F=0,new_CE=0,new_BP=0,new_LDPC=0,
               total_wall_seconds=time.monotonic()-started)
    (args.output_dir/'raw-audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'PASS','pairs':384,'legal_endpoints':summary['legal_four_endpoints'],
                      'wall_seconds':audit['total_wall_seconds']}))


if __name__=='__main__':
    main()
