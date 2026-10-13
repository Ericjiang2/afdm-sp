"""Bounded Phase-0 generator algebra and pilot geometry; no receiver calls.

Run from the repository root with ``python -m afdm_sp_joint_unrolled.direction_structure_audit``.
Controlled UWA inputs below are algebra fixtures passed through the REAL generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

# Start accounting before numerical imports; single-thread BLAS bounds CPU cost.
START_CPU = time.process_time()
START_WALL = time.monotonic()
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '1'


def complex_json(x):
    import numpy as np
    a = np.asarray(x)
    return {'real': a.real.tolist(), 'imag': a.imag.tolist()}


def spectrum(a):
    import numpy as np
    s = np.linalg.svd(a, compute_uv=False)
    tol = np.finfo(float).eps * max(a.shape) * float(s[0]) if len(s) else 0.
    return {'shape': list(a.shape), 'singular_values': s.tolist(),
            'rank': int(np.count_nonzero(s > tol)), 'rank_absolute_tolerance': tol,
            'gram_eigenvalues': (s*s).tolist()}


def checked_error(a, b):
    import numpy as np
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('nonfinite algebra result')
    error = float(np.linalg.norm(a-b) / max(1., float(np.linalg.norm(b))))
    if error > 1e-10:
        raise AssertionError(f'normalized reconstruction error {error} > 1e-10')
    return error


def controlled_channel(system, delays, dopplers, gains):
    """Replace ONLY the UWA draw; expansion/pruning/normalization remain real."""
    import numpy as np
    dl = np.asarray(delays, dtype=float)
    dk = np.asarray(dopplers, dtype=float)
    g = np.asarray(gains, dtype=complex)
    if dl.shape != dk.shape or dk.shape != g.shape:
        raise ValueError('controlled path shapes differ')
    original = system.generate_uwa_channel
    def draw():
        a = dk * system.fs / (system.N_total * system.fc)
        return (dl*system.delay_resolution, g, dl.astype(int)+1,
                np.ones(len(g)), a, a*system.c_sound, 1)
    system.generate_uwa_channel = draw
    try:
        return system.generate_channel_matrix()
    finally:
        system.generate_uwa_channel = original


def audit_case(system, Phi, H, params, label):
    import numpy as np
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import physical_cluster_weights, array_hash
    W = physical_cluster_weights(system, params)
    K = 2*system.k_max_cap+1
    ids = np.flatnonzero(np.any(W != 0, axis=1))
    emitted = np.asarray(params['l_exp'])*K + np.asarray(params['k_exp'])+system.k_max_cap
    merged = np.zeros(W.shape[0], dtype=complex)
    np.add.at(merged, emitted, params['chan_coef_exp'])
    coefficients = W @ params['g_i']
    rebuilt = system.gen_h_daft(coefficients[ids], ids//K, ids%K-system.k_max_cap)
    errors = {'g_equals_Lh': checked_error(coefficients, merged),
              'H_equals_Gdict_g': checked_error(rebuilt, H),
              'pilot_response': checked_error(Phi@coefficients, H@(np.sqrt(system.rho)*system._zc_seq))}
    # A compact isometric embedding of vec(G_i): retain only occupied shifts.
    shifts = (ids//K*K + ids%K-system.k_max_cap) % system.N_total
    unique_shifts = np.unique(shifts)
    compact = np.zeros((len(unique_shifts)*system.N_total, len(ids)), dtype=complex)
    n = np.arange(system.N_total)
    for j, (atom, shift) in enumerate(zip(ids, shifts)):
        operator = system.gen_h_daft(np.ones(1, complex), np.array([atom//K]),
                                     np.array([atom%K-system.k_max_cap]))
        block = int(np.searchsorted(unique_shifts, shift))*system.N_total
        compact[block:block+system.N_total, j] = operator[(n+shift)%system.N_total, n]
        checked_error(Phi[:, atom], operator@(np.sqrt(system.rho)*system._zc_seq))
    slots = []
    for p in range(W.shape[1]):
        active = np.flatnonzero(W[:, p])
        slots.append({'path_id': p, 'delay': int(params['l_i'][p]),
                      'doppler': float(params['k_real'][p]),
                      'gain_raw': complex_json(params['g_i_raw'][p]),
                      'gain_normalized': complex_json(params['g_i'][p]),
                      'atom_ids': active.tolist(), 'leakage_weights': complex_json(W[active, p]),
                      'unmerged_coefficients': complex_json(W[active, p]*params['g_i'][p]),
                      'retained_window_energy': float(np.sum(np.abs(W[:, p])**2))})
    A = Phi@W
    gains, _, rank, singular = np.linalg.lstsq(A, H@(np.sqrt(system.rho)*system._zc_seq),
                                               rcond=np.finfo(float).eps*max(A.shape))
    errors['noiseless_pilot_fit'] = checked_error(A@gains, Phi@coefficients)
    return {'case': label, 'source': 'real_UWA_draw' if label == 'random_P8' else 'controlled_UWA_input_real_generator',
            'slots': slots, 'L': complex_json(W[ids]), 'L_row_ids': ids.tolist(),
            'emitted_atom_ids': emitted.tolist(), 'emitted_coefficients': complex_json(params['chan_coef_exp']),
            'merged_coefficients': complex_json(merged[ids]), 'P_physical': int(params['taps']),
            'K_emit': int(params['P_actual']), 'K_unique': len(ids),
            'collision_row_ids': np.flatnonzero(np.count_nonzero(W, axis=1)>1).tolist(),
            'fro_scale': float(params['fro_scale']), 'H_sha256': array_hash(H),
            'L_spectrum': spectrum(W), 'Gdict_active_spectrum': spectrum(compact),
            'Gdict_L_spectrum': spectrum(compact@W[ids]),
            'pilot_physical_spectrum': spectrum(A), 'active_atom_pilot_spectrum': spectrum(Phi[:, ids]),
            'pilot_fit_rank': int(rank), 'pilot_fit_singular_values': singular.tolist(),
            'errors': errors}


def geometry(system, Phi, cases, support):
    import numpy as np
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import physical_cluster_weights, array_hash
    norms = np.linalg.norm(Phi, axis=0)
    zero = np.flatnonzero(norms == 0)
    valid = np.flatnonzero(norms > 0)
    U = Phi[:, valid]/norms[valid]
    gram = U.conj().T@U
    mu = np.abs(gram)
    upper = np.triu(np.ones(mu.shape, bool), 1)
    exact = np.argwhere(upper & (mu >= 1-1e-10))
    near = np.argwhere(upper & (mu >= .99))
    nearest = []
    # Legal nonnegative UWA Doppler interval: finite grid, not a continuous minimum.
    for delay in (0, system.l_max_cap//2, system.l_max_cap):
        locations = np.linspace(0., float(system.k_max_cap), 17)
        W = physical_cluster_weights(system, {'taps': 17, 'l_i': [delay]*17, 'k_real': locations})
        A = Phi@W
        for j in range(16):
            a, b = A[:, j], A[:, j+1]
            if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
                raise ValueError('zero legal physical template')
            coherence = min(1., float(abs(np.vdot(a,b))/(np.linalg.norm(a)*np.linalg.norm(b))))
            nearest.append({'delay': delay, 'locations': locations[j:j+2].tolist(),
                            'phase_invariant_unit_distance': float(np.sqrt(max(0., 2-2*coherence))),
                            'coherence': coherence, 'L_distance': float(np.linalg.norm(W[:,j]-W[:,j+1]))})
    current = {'status': 'unavailable_without_existing_support_artifact', 'spectrum': None}
    if support is not None:
        ids = json.loads(support.read_text())
        if (not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids)
                or len(set(ids)) != len(ids) or min(ids)<0 or max(ids)>=Phi.shape[1]):
            raise ValueError('support JSON must be a nonempty unique legal integer-ID list')
        current = {'status': 'existing_receiver_support_no_receiver_rerun', 'atom_ids': ids,
                   'source': str(support), 'sha256': hashlib.sha256(support.read_bytes()).hexdigest(),
                   'spectrum': spectrum(Phi[:,ids])}
    pairs = lambda p: [[int(valid[i]), int(valid[j]), float(mu[i,j])] for i,j in p]
    return {'pilot': 'actual sqrt(rho) * system._zc_seq, DAFT domain',
            'pilot_sha256': array_hash(np.sqrt(system.rho)*system._zc_seq),
            'Phi_sha256': array_hash(Phi), 'Phi_spectrum': spectrum(Phi),
            'zero_response_atom_ids': zero.tolist(), 'column_norm_range': [float(norms.min()),float(norms.max())],
            'normalized_gram': complex_json(gram), 'exact_collinear_pairs': pairs(exact),
            'near_collinear_pairs': pairs(near), 'max_offdiagonal_coherence': float(mu[upper].max()),
            'current_S': current,
            'generated_true_support_spectra': [{'case': c['case'], 'spectrum': c['active_atom_pilot_spectrum']} for c in cases],
            'legal_adjacent_templates': nearest, 'template_scope': '17 equally spaced legal Dopplers at three fixed delays; adjacent only',
            'thresholds': {'exact_mu_min': 1-1e-10, 'near_mu_min': .99,
                           'rationale': '.99 is a preregistered severe pair-confusion flag, not a FER threshold; exact slack covers float64 phases'},
            'H_T_geometry_entry_condition': bool(len(near) or len(zero)),
            'limitation': 'Geometry alert only. No claim of full coded-SP nonidentifiability or receiver/FER improvement.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-out', type=Path, required=True)
    parser.add_argument('--geometry-out', type=Path, required=True)
    parser.add_argument('--support-json', type=Path)
    parser.add_argument('--cpu-seconds', type=int, default=450)
    args = parser.parse_args()
    if not 1 <= args.cpu_seconds <= 600:
        parser.error('CPU budget must be between 1 and 600 seconds, including imports')
    for path in (args.physical_out, args.geometry_out):
        if path.exists():
            raise FileExistsError(path)
    if args.physical_out.resolve() == args.geometry_out.resolve():
        raise ValueError('output paths must differ')
    # RLIMIT_CPU measures aggregate process CPU (all threads), not wall time.
    soft = math.ceil(time.process_time()+max(0., args.cpu_seconds-(time.process_time()-START_CPU)))
    resource.setrlimit(resource.RLIMIT_CPU, (soft, soft+1))
    def timeout(signum, frame):
        raise TimeoutError('Phase-0 process CPU budget exhausted')
    signal.signal(signal.SIGXCPU, timeout)
    import numpy as np
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix
    import torch
    torch.set_num_threads(1)
    # Runtime tripwire prohibits receiver/OMP/detector/decoder calls, including imported aliases.
    forbidden = ('omp_', 'mp_detect', 'joint_omp', '_fast_bp', 'decode', 'ldpc_decode')
    def guard(frame, event, arg):
        if event == 'call':
            name = frame.f_code.co_name
            filename = frame.f_code.co_filename
            if ('afdm_sp_joint_unrolled' in filename and
                    (name.startswith(forbidden) or (name == 'forward' and 'classical_joint_unrolled' in filename))):
                raise RuntimeError(f'forbidden Phase-0 call: {filename}:{name}')
    sys.setprofile(guard)
    try:
        system = _make_config_a(1024, 2., 8, 10., 4.)
        if (system.k_max_cap, system.l_max_cap, system.k_leak, system.rho) != (2,102,2,.5):
            raise ValueError('canonical physical configuration drift')
        Phi = construct_sensing_matrix(1024, np.sqrt(system.rho)*system._zc_seq,
                                       system.c1, system.c2, system.l_max_cap, system.k_max_cap)
        cases = []
        fixtures = [('single_integer',[0],[1.],[1.]), ('single_fractional',[2],[.35],[1j]),
                    ('clipped_fractional',[3],[1.8],[1.]),
                    ('overlap_distinct',[2,2],[.35,.6],[1.,.4j]),
                    ('overlap_identical',[2,2],[.35,.35],[1.,-.4]),
                    ('overlap_cancellation',[2,2],[.35,.35],[1.,-1.])]
        for label, dl, dk, gains in fixtures:
            H, _, params = controlled_channel(system, dl, dk, gains)
            cases.append(audit_case(system, Phi, H, params, label))
        np.random.seed(2026090802)
        H, _, params = system.generate_channel_matrix()
        cases.append(audit_case(system, Phi, H, params, 'random_P8'))
        geo = geometry(system, Phi, cases, args.support_json)
    finally:
        sys.setprofile(None)
    source_files = ['direction_structure_audit.py', 'afdm_env.py', 'budgeted_support_diagnostics.py',
                    'afdm_baselines.py', 'classical_joint_unrolled.py', 'loop9_cache_features.py',
                    'run_classical_baselines_python.py', 'system_config.py']
    shared = {'status': 'passed', 'evidence_kind': 'real_generator_algebra_no_receiver',
              'command': [sys.executable]+sys.argv, 'exit_code': 0,
              'source_sha256': {f: hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in source_files},
              'cpu_seconds': time.process_time()-START_CPU, 'wall_seconds': time.monotonic()-START_WALL,
              'cpu_budget_seconds': args.cpu_seconds, 'receiver_calls': 0, 'omp_calls': 0,
              'detector_calls': 0, 'decoder_calls': 0, 'numpy': np.__version__, 'torch': torch.__version__,
              'configuration': {'N':1024,'P_random':8,'rho':.5,'k_leak':2,'l_max':102,'k_max':2,
                                'seed':2026090802,'frac_prune_rel_thres':system.frac_prune_rel_thres,
                                'c1':system.c1,'c2':system.c2,'fs':system.fs}}
    if shared['cpu_seconds'] > args.cpu_seconds:
        raise TimeoutError('CPU budget exceeded')
    physical = dict(shared, cases=cases, mapping_verdict='exists_underused_in_independent_atom_receiver',
                    mapping_domain='Fractional truncated generator; h denotes normalized physical gains. L depends on clipped locations, window, relative pruning, not gains. Mapping from g_i_raw includes gain-dependent global Frobenius scale.',
                    algebra='g=L(eta) h; vec(H)=Gdict g; overlapping rows sum complex coefficients before thresholding.',
                    code_refs={'generator':'afdm_env.py:505-663','L':'budgeted_support_diagnostics.py:80-103',
                               'independent_atom_OLS':'classical_joint_unrolled.py:155-160',
                               'independent_atom_gain_update':'classical_joint_unrolled.py:294-314'},
                    underuse_scope='Static independent-atom OMP/DA-LS parameterization; oracle physical-cluster helper already exists. Does not prove statistical benefit.',
                    error_tolerance={'dtype':'complex128','normalized_norm_error_max':1e-10,
                                     'rationale':'Float64 sum/phase consistency, denominator max(1,norm(reference)); no relaxation for singular gains. SVD reports rank and uses minimum-norm pilot fit.'})
    for path, payload in ((args.physical_out, physical), (args.geometry_out, dict(shared, **geo))):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as handle:
            json.dump(payload, handle, indent=2, allow_nan=False)
            handle.write('\n')
    print(json.dumps({'status':'passed','cpu_seconds':shared['cpu_seconds'],
                      'physical_out':str(args.physical_out),'geometry_out':str(args.geometry_out)}, allow_nan=False))


if __name__ == '__main__':
    main()
