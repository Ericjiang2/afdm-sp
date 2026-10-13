"""SYN-02 read-only CE synthesis from audited N1024 saved arrays.

No receiver, BP, LDPC, complete-chain, or candidate likelihood is called.
The saved mean-CE variance is data-symbol variance, not a channel-gain Gamma.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

N = 1024
NSIZE_SNRS = (10, 20)
G1_SNRS = (7, 8)
SYMBOL_IDS = tuple(range(40))  # fixed before looking at any frame or error
CANDIDATE_LIKELIHOOD_LIMIT = 5120


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audited_stage(summary_path, audit_path, *, expected_f, stage):
    summary_path, audit_path = Path(summary_path), Path(audit_path)
    summary, audit = (json.loads(p.read_text()) for p in (summary_path, audit_path))
    require(summary.get('status') == 'COMPLETE' and audit.get('status') == 'PASS',
            stage + ' saved summary/raw audit incomplete')
    require(audit.get('summary_sha256') == digest(summary_path),
            stage + ' raw audit does not bind saved summary')
    require(summary.get('calls', {}).get('F') == expected_f,
            stage + ' saved F budget differs')
    require(audit.get('rows') == summary.get('raw_checks', {}).get('rows'),
            stage + ' independent raw rows differ from producer checks')
    if 'source_sha256' in summary:
        require(audit.get('source_sha256') == summary['source_sha256'],
                stage + ' audited source SHA differs')
    f = [e for e in summary['records'] if e['kind'] == 'F']
    require(len(f) == expected_f and len({(e['block'], e['snr'], e['arm']) for e in f}) == expected_f,
            stage + ' saved F identities duplicate or incomplete')
    return dict(summary=summary, audit=audit, summary_path=summary_path,
                audit_path=audit_path, summary_sha256=digest(summary_path),
                audit_sha256=digest(audit_path), f=f)


def validated_sources(args):
    """Admission does not infer completion from a directory or partial NPZs."""
    nsize = None
    if args.nsize_root:
        require(all(getattr(args,'nsize_'+suffix) is not None for suffix in
            ('engineering_summary','engineering_audit','development_summary','development_audit')),
            'N1024 root needs both audited stage paths')
        stages = {
            'engineering': audited_stage(args.nsize_engineering_summary,
                args.nsize_engineering_audit, expected_f=8, stage='N1024 engineering'),
            'development': audited_stage(args.nsize_development_summary,
                args.nsize_development_audit, expected_f=56, stage='N1024 development'),
        }
        entries = [e for stage in stages.values() for e in stage['summary']['records']]
        require(len(entries)==80 and {e['kind'] for e in entries}=={'A','F'},
                'N1024 saved A/F record inventory differs')
        index = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in entries}
        require(len(index) == len(entries), 'N1024 duplicate A/F identities across stages')
        arms = {'p0__OMP_BASE', 'pZ__OMP_BASE'}
        for name, blocks in (('engineering',range(2)),('development',range(2,16))):
            require({(e['block'], e['snr'], e['arm']) for e in stages[name]['f']}
                    == {(b,s,a) for b in blocks for s in NSIZE_SNRS for a in arms},
                    'N1024 '+name+' registered F split differs')
        require({(e['block'], e['snr'], e['arm']) for stage in stages.values() for e in stage['f']}
                == {(b, s, a) for b in range(16) for s in NSIZE_SNRS for a in arms},
                'N1024 16-block two-pilot two-SNR F grid differs')
        require({(e['block'], e['snr'], e['arm']) for e in entries if e['kind'] == 'A'}
                == {(b, 10, 'UWA_N1024_INPUT') for b in range(16)},
                'N1024 physical A grid differs')
        for key in ('runner_sha256', 'source_sha256', 'checkpoint_sha256'):
            require(stages['engineering']['summary'][key] == stages['development']['summary'][key],
                    'N1024 stage lineage differs: ' + key)
        nsize = dict(root=Path(args.nsize_root).resolve(), stages=stages, index=index,
                     source_sha256=stages['engineering']['summary']['source_sha256'])
    g1 = None
    if args.g1_root:
        require(all(getattr(args,'g1_'+suffix) is not None for suffix in
            ('engineering_summary','engineering_audit','development_summary',
             'development_audit','physical_summary')),
            'G1 root needs both O3 audits and physical summary')
        stages = {
            'engineering': audited_stage(args.g1_engineering_summary,
                args.g1_engineering_audit, expected_f=4, stage='G1 O3 engineering'),
            'development': audited_stage(args.g1_development_summary,
                args.g1_development_audit, expected_f=60, stage='G1 O3 development'),
        }
        f = [e for stage in stages.values() for e in stage['f']]
        require(all({e['kind'] for e in stage['summary']['records']}=={'F'}
                    for stage in stages.values()),
                'G1 O3 stage contains non-F record')
        for name, blocks in (('engineering',(0,20)),
                             ('development',tuple(b for b in range(32) if b not in (0,20)))):
            require({(e['block'], e['snr'], e['arm']) for e in stages[name]['f']}
                    == {(b,s,'O3_TRUE_DATA_CE_T1') for b in blocks for s in G1_SNRS},
                    'G1 O3 '+name+' registered F split differs')
        require({(e['block'], e['snr'], e['arm']) for e in f}
                == {(b, s, 'O3_TRUE_DATA_CE_T1') for b in range(32) for s in G1_SNRS},
                'G1 O3 32-block two-SNR F grid differs')
        require(stages['engineering']['summary']['source_sha256']
                == stages['development']['summary']['source_sha256'],
                'G1 O3 source lineage differs')
        physical_path = Path(args.g1_physical_summary)
        physical = json.loads(physical_path.read_text())
        require(physical.get('status') == 'COMPLETE' and len(physical.get('records', [])) == 288,
                'G1 physical/full upstream summary differs')
        pindex = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in physical['records']}
        require(len(pindex) == 288 and all(('A', b, 7, 'G1_PROPAGATION') in pindex for b in range(32)),
                'G1 physical A grid differs')
        g1 = dict(root=Path(args.g1_root).resolve(), stages=stages, f=f,
                  physical_index=pindex, physical_summary_path=physical_path,
                  physical_summary_sha256=digest(physical_path),
                  source_sha256=stages['engineering']['summary']['source_sha256'])
    require(nsize is not None or g1 is not None, 'at least one audited N1024 source required')
    return nsize, g1


def _scalar(x):
    value = np.asarray(x)
    require(value.size == 1 and np.isfinite(value).all(), 'finite scalar state required')
    return float(value.reshape(-1)[0])


def gram_and_schur(A, energy, *, max_columns=275):
    """Fixed active design: leave-one-out Schur, not addition candidates."""
    A = np.asarray(A, dtype=np.complex128)
    require(A.ndim == 2 and A.shape[0] == N and 0 < A.shape[1] <= max_columns
            and np.isfinite(A).all() and energy > 0,
            'finite N1024 active CE design required')
    G = A.conj().T @ A
    ev = np.linalg.eigvalsh(G)
    threshold = np.finfo(float).eps * max(A.shape) * max(1., float(ev[-1]))
    if ev[0] <= threshold:
        return dict(active_columns=A.shape[1], rank_deficient=True,
            normalized_min_eigenvalue=float(ev[0]/energy),
            normalized_max_eigenvalue=float(ev[-1]/energy),
            white_noise_gamma=None, active_leave_one_out_schur=None,
            candidate_extension_schur='not_evaluated_without_full_dictionary')
    inverse = np.linalg.inv(G)
    s = 1/np.real(np.diag(inverse))
    require(np.isfinite(s).all() and np.all(s > 0), 'active Schur must be positive')
    return dict(active_columns=A.shape[1], rank_deficient=False,
        normalized_min_eigenvalue=float(ev[0]/energy),
        normalized_max_eigenvalue=float(ev[-1]/energy),
        white_noise_gamma=float(energy/A.shape[1]*np.trace(inverse).real),
        active_leave_one_out_schur=dict(min=float(s.min()), median=float(np.median(s)),
            max=float(s.max())),
        candidate_extension_schur='not_evaluated_without_full_dictionary')


def state_metrics(state, raw, pilot, y, *, c1, c2, k_max):
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import data_uncertainty_gram
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    data, pilot, y = (np.asarray(v, dtype=np.complex128) for v in (raw['data'], pilot, y))
    mu = np.asarray(state['mu'], dtype=np.complex128)
    A = np.asarray(state['A']); previous = np.asarray(state['g_previous'])
    solution = np.asarray(state['g_solution']); variance = np.asarray(state['finite_variance'], dtype=float)
    delays, dopplers = (np.asarray(state[k], dtype=np.int64) for k in ('support_delays', 'support_dopplers'))
    require(all(v.shape == (N,) for v in (data, pilot, y, mu, variance))
            and A.shape == (N, len(solution)) and previous.shape == solution.shape
            and delays.shape == dopplers.shape == solution.shape
            and np.isfinite(variance).all() and np.all(variance >= 0)
            and all(np.isfinite(v).all() for v in (data, pilot, y, mu, A, previous, solution)),
            'CE state/raw dimensions or finite values differ')
    require(state['mode'] == 'mean' and state['outer_iter'] in range(1, 10),
            'saved mean CE trajectory differs')
    total = pilot + mu
    energy_p = float(np.vdot(pilot, pilot).real)
    energy_mu = float(np.vdot(mu, mu).real)
    cross = float(2*np.vdot(pilot, mu).real)
    energy_total = float(np.vdot(total, total).real)
    require(abs(energy_total-energy_p-energy_mu-cross) <= 1e-9*max(1., energy_total),
            'pilot/data energy and cross term do not close')
    max_columns = 275 if k_max == 5 else 40
    geometry = gram_and_schur(A, energy_total, max_columns=max_columns)
    Q = data_uncertainty_gram(N, torch.from_numpy(delays), torch.from_numpy(dopplers),
        torch.from_numpy(variance), c1, c2, k_max, cdtype=torch.complex128).numpy()
    diagonal = np.diag(np.diag(Q))
    error = mu-data
    selected = np.asarray(SYMBOL_IDS)
    residual = y - np.asarray(A, dtype=np.complex128) @ np.asarray(solution, dtype=np.complex128)
    return dict(outer_iter=int(state['outer_iter']), support_size=len(solution),
        support_delays_sha256=array_hash(delays), support_dopplers_sha256=array_hash(dopplers),
        A_sha256=array_hash(A), mu_sha256=array_hash(state['mu']),
        g_previous_sha256=array_hash(previous), g_solution_sha256=array_hash(solution),
        pilot_energy=energy_p, feedback_energy=energy_mu,
        pilot_feedback_cross=cross, total_design_input_energy=energy_total,
        true_symbol_mse=float(np.mean(abs(error)**2)),
        selected40_symbol_mse=float(np.mean(abs(error[selected])**2)),
        selected40_error_squared=[float(v) for v in abs(error[selected])**2],
        finite_variance_mean=float(variance.mean()),
        gain_step_squared=float(np.vdot(solution-previous, solution-previous).real),
        CE_residual_squared=float(np.vdot(residual, residual).real),
        sigma2=_scalar(state['sigma2']), regularization=_scalar(state['regularization']),
        Gram=geometry,
        Q_diagnostic_mean_unused=dict(trace=float(np.trace(Q).real),
            offdiagonal_frobenius=float(np.linalg.norm(Q-diagonal)),
            max_offdiagonal=float(np.max(abs(Q-diagonal))) if len(Q)>1 else 0.,
            finite_variance_sha256=array_hash(variance)),
        truth_scope='mu error uses saved true data only offline; no receiver input')


def paired_error_correlation(first, last):
    a, b = (np.asarray(v['selected40_error_squared']) for v in (first, last))
    require(a.shape == b.shape == (40,), 'fixed selected40 error vectors required')
    centered_a, centered_b = a-a.mean(), b-b.mean()
    denominator = float(np.linalg.norm(centered_a)*np.linalg.norm(centered_b))
    correlation = None if denominator == 0 else float(np.vdot(centered_a, centered_b).real/denominator)
    return dict(selected_indices=list(SYMBOL_IDS), first_last_squared_error_correlation=correlation,
        both_above_quarter=int(np.count_nonzero((a > .25) & (b > .25))),
        first_above_quarter=int(np.count_nonzero(a > .25)),
        last_above_quarter=int(np.count_nonzero(b > .25)),
        scope='descriptive same-frame spatial error co-occurrence; no independent transfer claim')


def frame_metrics(ce, raw, pilot, y, geometry):
    require(len(ce) == 9 and [s['outer_iter'] for s in ce] == list(range(1, 10)),
            'nine actual CE observer states required')
    trajectory = [state_metrics(s, raw, pilot, y, **geometry) for s in ce]
    first, last = trajectory[0], trajectory[-1]
    return dict(trajectory=trajectory,
        first_last_error_correlation=paired_error_correlation(first, last),
        scalar_transfer_status='not_closed_or_validated_from_same_frame_trajectory',
        preserved_state_coordinates=['symbol_error','support_size','Gram_geometry',
            'finite_variance','gain_step','CE_residual','pilot_feedback_cross'],
        candidate_channel_Gamma='missing_independent_or_cross_fitted_gain_covariance',
        candidate_likelihood_status='not_identifiable',
        candidate_likelihood_evaluations=0)


def gamma_field_inventory(raw, value, ce):
    """Saved field inventory, not an inference from mean-CE Q or true gains."""
    keys = {'raw':sorted(raw), 'receiver':sorted(value), 'CE':sorted(ce[0])}
    suspects = {scope:[key for key in fields if key.lower() in
        ('gamma','gain_covariance','channel_gain_covariance','gain_posterior_covariance')]
        for scope,fields in keys.items()}
    require(not any(suspects.values()),
            'saved Gamma-like field needs separate provenance/independence review')
    return dict(saved_field_keys=keys, gamma_like_fields=suspects,
        independent_channel_gain_Gamma_saved=False,
        Q_is_not_Gamma='Q=tr(U_i^H U_j diag(symbol_variance)); mean CE does not consume it')


def analyze(args):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    nsize, g1 = validated_sources(args)
    started = time.time(); cpu_started = time.process_time()
    rows = []; parent_hashes = []; field_inventories = {}
    if nsize:
        root, index = nsize['root'], nsize['index']
        for b in range(16):
            ae = index['A', b, 10, 'UWA_N1024_INPUT']
            _, raw = verified_record(ae, root)
            require(raw.get('domain') == 'uwa' and raw.get('N') == N and raw.get('block') == b,
                    'N1024 physical A identity differs')
            parent_hashes.append(ae['sha256'])
            metadata = raw['metadata']
            require(metadata['k_max'] == 5 and abs(2*N*metadata['c1']-11) < 1e-10,
                    'N1024 W5/q11 geometry differs')
            geometry = dict(c1=metadata['c1'], c2=metadata['c2'], k_max=5)
            for pilot in ('p0', 'pZ'):
                for snr in NSIZE_SNRS:
                    entry = index['F', b, snr, pilot+'__OMP_BASE']
                    record, value = verified_record(entry, root)
                    require(record['input_record_sha256'] == ae['sha256'],
                            'N1024 F/A parent hash differs')
                    p = raw['pilots'][pilot]
                    sigma2 = 10**(-snr/10)
                    y = raw['noiseless'][pilot]+np.sqrt(sigma2)*raw['noise']
                    observed = dict(y=y, pilot=p, sigma2=np.asarray(sigma2),
                        constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
                    require(record['observed_hashes'] == hashes(observed),
                            'N1024 saved observed input hash differs')
                    metrics = frame_metrics(value['CE'], raw, p, y, geometry)
                    inventory = gamma_field_inventory(raw,value,value['CE'])
                    if 'N1024_UWA_uncoded' in field_inventories:
                        require(field_inventories['N1024_UWA_uncoded']==inventory,
                                'N1024 saved field inventory differs across frames')
                    field_inventories['N1024_UWA_uncoded']=inventory
                    rows.append(dict(domain='N1024_UWA_uncoded', block=b, snr=snr,
                        pilot=pilot, F_record_sha256=entry['sha256'],
                        A_record_sha256=ae['sha256'], **metrics))
                    parent_hashes.append(entry['sha256'])
    if g1:
        root = g1['root']
        for entry in sorted(g1['f'], key=lambda e:(e['block'],e['snr'])):
            b, snr = entry['block'], entry['snr']
            ae = g1['physical_index']['A', b, 7, 'G1_PROPAGATION']
            _, physical = verified_record(ae, root)
            raw, _ = reuse_at_snr(physical['raw'], physical['diagnostics'], snr)
            record, value = verified_record(entry, root)
            require(record['physical_record_sha256'] == ae['sha256'],
                    'G1 O3 physical parent hash differs')
            p, y = raw['pilot'], raw['y']
            observed = dict(y=np.asarray(y), pilot=np.asarray(p), sigma2=np.asarray(raw['sigma2']),
                constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            require(record['observed_hashes'] == hashes(observed),
                    'G1 O3 observed input hash differs')
            params = raw['params']
            require(len(p)==N and abs(2*N*params['c1']-5)<1e-10,
                    'G1 W2/q5 geometry differs')
            metrics = frame_metrics(value['dals'], raw, p, y,
                dict(c1=params['c1'],c2=params['c2'],k_max=2))
            inventory = gamma_field_inventory(raw,value,value['dals'])
            if 'G1_CPP_coded_O3' in field_inventories:
                require(field_inventories['G1_CPP_coded_O3']==inventory,
                        'G1 saved field inventory differs across frames')
            field_inventories['G1_CPP_coded_O3']=inventory
            rows.append(dict(domain='G1_CPP_coded_O3', block=b, snr=snr,
                pilot='p0', F_record_sha256=entry['sha256'],
                A_record_sha256=ae['sha256'], **metrics))
            parent_hashes.extend((ae['sha256'],entry['sha256']))
    require(len(rows) == (64 if nsize else 0) + (64 if g1 else 0),
            'SYN-02 audited F row count differs')
    for source in (nsize,g1):
        if source:
            for stage in source['stages'].values():
                require(digest(stage['summary_path'])==stage['summary_sha256']
                    and digest(stage['audit_path'])==stage['audit_sha256'],
                    'audited source changed during SYN-02 analysis')
    if g1:
        require(digest(g1['physical_summary_path'])==g1['physical_summary_sha256'],
                'G1 physical summary changed during SYN-02 analysis')
    result = dict(schema='ce-synthesis-offline-v1', status='COMPLETE',
        rows=rows, source_provenance=dict(nsize=None if not nsize else {
            'source_sha256':nsize['source_sha256'],
            'stages':{k:{'summary_sha256':v['summary_sha256'],'audit_sha256':v['audit_sha256']}
                      for k,v in nsize['stages'].items()}},
            g1=None if not g1 else {'source_sha256':g1['source_sha256'],
                'physical_summary_sha256':g1['physical_summary_sha256'],
                'stages':{k:{'summary_sha256':v['summary_sha256'],'audit_sha256':v['audit_sha256']}
                          for k,v in g1['stages'].items()}},
            parent_record_sha256=sorted(set(parent_hashes)),
            saved_field_inventories=field_inventories,
            script_sha256=digest(Path(__file__))),
        candidate_likelihood=dict(status='not_identifiable_without_independent_Gamma',
            candidate_mean_term='not_identifiable_as_channel_marginal_without_independent_Gamma',
            candidate_logdet_term='not_identifiable_without_Gamma',
            candidate_inverse_covariance_term='not_identifiable_without_Gamma',
            error_correlation_term='saved_first_last_selected40_descriptive_only',
            independent_Gamma_saved=False, same_y_plugin_is_not_model_exact=True,
            approximation_if_ever_used='plug-in/cavity; not performed here',
            eligible_N1024_raw_frames=len(rows), preselected_states=[1,9],
            preselected_symbol_indices=list(SYMBOL_IDS),
            registered_max_evaluations=CANDIDATE_LIKELIHOOD_LIMIT,
            actual_evaluations=0, new_BP=0, new_LDPC=0, new_F=0),
        empirical_transfer=dict(status='multi_state_trajectory_preserved',
            scalar_closure='not_demonstrated', fixed_points_or_threshold_theorem='not_claimed',
            scope='same saved development/diagnostic frames only; no independent CONF'),
        offline_resources=dict(saved_F_states_read=len(rows),
            CE_states_analyzed=9*len(rows),
            active_Gram_eigendecompositions=9*len(rows),
            active_Gram_inverse_solves=sum(not state['Gram']['rank_deficient']
                for row in rows for state in row['trajectory']),
            Q_diagnostic_constructs=9*len(rows),
            candidate_likelihood_evaluations=0,
            new_BP=0,new_LDPC=0,new_F=0),
        analysis_wall_seconds=time.time()-started,
        analysis_CPU_seconds=time.process_time()-cpu_started)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(dict(status=result['status'], frames=len(rows),
        likelihood_evaluations=0, output=str(target))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nsize-root', type=Path)
    parser.add_argument('--nsize-engineering-summary', type=Path)
    parser.add_argument('--nsize-engineering-audit', type=Path)
    parser.add_argument('--nsize-development-summary', type=Path)
    parser.add_argument('--nsize-development-audit', type=Path)
    parser.add_argument('--g1-root', type=Path)
    parser.add_argument('--g1-engineering-summary', type=Path)
    parser.add_argument('--g1-engineering-audit', type=Path)
    parser.add_argument('--g1-development-summary', type=Path)
    parser.add_argument('--g1-development-audit', type=Path)
    parser.add_argument('--g1-physical-summary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    analyze(parser.parse_args())
