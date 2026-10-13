"""Read-only scalar mechanism ledger from audited PILOT-02 A/E states."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ARMS=('P02','P03','C33','P04','C54')
TERMS=('map','tail','data','noise')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def energy(x):
    return float(np.vdot(x,x).real)


def finite_number(x):
    value=float(x)
    if not np.isfinite(value):
        raise ValueError('nonfinite saved PILOT-02 scalar')
    return value


def geometry(gram,pilot_energy,saved_gamma,eigenvalues):
    G=np.asarray(gram,dtype=np.complex128)
    eigen=np.asarray(eigenvalues,dtype=float)
    if G.shape!=(24,24) or eigen.shape!=(24,) or pilot_energy<=0:
        raise ValueError('actual K24 Gram geometry differs')
    if eigen[0]<=0 or np.linalg.norm(G-G.conj().T)>1e-8*max(1.,np.linalg.norm(G)):
        raise ValueError('actual K24 Gram is nonpositive or nonHermitian')
    gamma=float((pilot_energy/24)*np.trace(np.linalg.solve(G,np.eye(24))).real)
    equal=float(np.max(abs(np.diag(G)-pilot_energy))/pilot_energy)
    orth=float(np.linalg.norm(G-pilot_energy*np.eye(24),ord=2)/pilot_energy)
    premise=bool(equal<=1e-4 and orth<=1e-4)
    return dict(pilot_energy=finite_number(pilot_energy),gamma=finite_number(gamma),
        producer_saved_gamma_without_divisor=finite_number(saved_gamma),
        saved_to_contract_gamma_ratio=finite_number(saved_gamma/gamma),
        normalized_lambda_min=finite_number(eigen[0]),
        normalized_lambda_max=finite_number(eigen[-1]),
        equal_energy_relative=equal,orthogonality_operator_relative=orth,
        P1_full_rank=True,P1_equal_energy_orthogonality_premise=premise,
        P1_gamma_within_complex64_tolerance=bool(abs(gamma-1.)<=1e-4) if premise else None)


def four_vector(error):
    terms=error['terms']; squares=error['squares']; crosses=error['cross']
    keys={f'{a}:{b}' for i,a in enumerate(TERMS) for b in TERMS[i+1:]}
    if set(terms)!=set(TERMS) or set(squares)!=set(TERMS) or set(crosses)!=keys:
        raise ValueError('saved four-square/six-cross key inventory differs')
    squared={a:finite_number(squares[a]) for a in TERMS}
    cross={f'{a}:{b}':finite_number(crosses[f'{a}:{b}'])
           for i,a in enumerate(TERMS) for b in TERMS[i+1:]}
    for a in TERMS:
        if abs(energy(terms[a])-squared[a])>1e-8*max(1.,squared[a]):
            raise ValueError('saved vector square differs')
    for key,value in cross.items():
        a,b=key.split(':')
        if abs(2*float(np.vdot(terms[a],terms[b]).real)-value)>1e-8*max(1.,abs(value)):
            raise ValueError('saved vector cross differs')
    closure=sum(squared.values())+sum(cross.values())
    affine=finite_number(error['affine_error'])
    if abs(closure-affine)>1e-8*max(1.,affine):
        raise ValueError('saved error square/cross sum does not close')
    return dict(squares=squared,cross=cross,affine_error=affine,
        actual_dtype_error=finite_number(error['actual_error']),
        dtype_rounding_relative=finite_number(error['dtype_rounding_relative']),
        observed_y_defect_relative=finite_number(error['observed_y_defect_relative']))


def row_from_a(v):
    ids=np.asarray(v['support_ids']);g=np.asarray(v['gains']);true=np.asarray(v['gS'])
    if ids.shape!=(24,) or g.shape!=(24,) or true.shape!=(24,):
        raise ValueError('saved PILOT-02 actual support/coefficient width differs')
    metrics=v['metrics'];wave=metrics['waveform'];sch=v['schur']
    q=np.asarray(v['Q_initial_model_unused'],dtype=np.complex128)
    consumed=np.asarray(v['Q_consumed'])
    if q.shape!=(24,24) or consumed.shape!=(24,24) or np.any(consumed!=0):
        raise ValueError('initial model Q unexpectedly consumed')
    off=q-np.diag(np.diag(q))
    valid=np.asarray(sch['increment_valid'],dtype=bool)
    increments=np.asarray(sch['white_variance_increment'],dtype=float)
    if valid.shape!=increments.shape or np.any(increments[~valid]!=0):
        raise ValueError('Schur undefined increment was treated as finite')
    hist=v['histogram'];edges=np.asarray(hist['edges'])
    counts_true=np.asarray(hist['true']);counts_error=np.asarray(hist['gain_error'])
    if (len(edges)!=9 or len(counts_true)!=8 or len(counts_error)!=8
            or counts_true.sum()!=24 or counts_error.sum()!=24):
        raise ValueError('saved coefficient histogram differs')
    pilot_energy=energy(v['pilot'])
    geom=geometry(v['gram'],pilot_energy,metrics['gamma'],v['normalized_gram_eigenvalues'])
    return dict(block=int(v['block']),snr=int(v['snr']),arm=v['arm'],W=int(v['W']),
        support_ids=ids.astype(int).tolist(),support_delays=np.asarray(v['support_delays']).astype(int).tolist(),
        support_dopplers=np.asarray(v['support_dopplers']).astype(int).tolist(),
        coefficient_squared_error=energy(g-true),geometry=geom,error=four_vector(v['error']),
        H_NMSE=finite_number(metrics['H_NMSE']),Hp_NMSE=finite_number(metrics['Hp_NMSE']),
        H_squared_error=finite_number(metrics['H_squared_error']),
        Hp_squared_error=finite_number(metrics['Hp_squared_error']),
        selected_true_coefficient_energy=finite_number(metrics['selected_true_coefficient_energy']),
        best_same_domain_K24_energy=finite_number(metrics['best_same_domain_K24_energy']),
        omitted_energy_floor=finite_number(metrics['omitted_energy_floor']),
        best_vs_selected_omission_energy=finite_number(metrics['best_vs_selected_omission_energy']),
        schur=dict(candidate_count=len(np.asarray(sch['candidate_ids'])),
            increment_defined_count=int(valid.sum()),increment_undefined_count=int((~valid).sum()),
            undefined_reason=sch['invalid_reason'],
            valid_increment_min=finite_number(increments[valid].min()) if valid.any() else None,
            valid_increment_max=finite_number(increments[valid].max()) if valid.any() else None,
            residual_min=finite_number(np.min(sch['residual']))),
        Q=dict(model_offdiag_frobenius_ratio=finite_number(np.linalg.norm(off)/max(1.,np.linalg.norm(q))),
            model_alias_groups=int(v['Q_physical_alias_groups']),
            colored_probe_alias_groups=int(v['Q_colored_probe_alias_groups']),
            model_Q_consumed=False,colored_probe_Q_consumed=False),
        histogram=dict(edges=edges.tolist(),true_counts=counts_true.astype(int).tolist(),
            coefficient_error_counts=counts_error.astype(int).tolist()),
        waveform=dict(native_pass=bool(wave['passes_native_gate']),
            native_papr_db=finite_number(wave['native_gate_papr_db']),
            native_cpp_peak_power=finite_number(wave['native_cpp_peak']),
            oversampled_payload_papr_db=finite_number(wave['oversampled_payload_papr_db']),
            oversampled_cpp_papr_db=finite_number(wave['oversampled_cpp_papr_db']),
            oversampled_cpp_peak_power=finite_number(wave['oversampled_cpp_peak']),
            nonzero_pilot_DAFT_bins=int(metrics['nonzero_pilot_DAFT_bins'])),
        provenance=dict(raw_p0_sha256=v['raw_p0_sha256'],
            reference_record_sha256=v['reference_record_sha256']))


def aggregate(rows):
    result={}
    for arm in ARMS:
        selected=[r for r in rows if r['arm']==arm]
        if len(selected)!=64:
            raise ValueError('five-arm mechanism row count differs')
        def span(values):
            a=np.asarray(values,dtype=float)
            return dict(mean=float(a.mean()),min=float(a.min()),max=float(a.max()),
                median=float(np.median(a)))
        result[arm]=dict(rows=64,
            H_NMSE=span([r['H_NMSE'] for r in selected]),
            Hp_NMSE=span([r['Hp_NMSE'] for r in selected]),
            gamma=span([r['geometry']['gamma'] for r in selected]),
            producer_saved_gamma_without_divisor=span([r['geometry']['producer_saved_gamma_without_divisor'] for r in selected]),
            saved_to_contract_gamma_ratio=span([r['geometry']['saved_to_contract_gamma_ratio'] for r in selected]),
            normalized_lambda_min=span([r['geometry']['normalized_lambda_min'] for r in selected]),
            normalized_lambda_max=span([r['geometry']['normalized_lambda_max'] for r in selected]),
            P1_premise_count=sum(r['geometry']['P1_equal_energy_orthogonality_premise'] for r in selected),
            P1_applicable_gamma_success_count=sum(r['geometry']['P1_gamma_within_complex64_tolerance'] is True for r in selected),
            Schur_defined_candidates=sum(r['schur']['increment_defined_count'] for r in selected),
            Schur_undefined_candidates=sum(r['schur']['increment_undefined_count'] for r in selected),
            Q_alias_group_count=sum(r['Q']['model_alias_groups'] for r in selected),
            Q_offdiag_ratio=span([r['Q']['model_offdiag_frobenius_ratio'] for r in selected]),
            selected_true_coefficient_energy=span([r['selected_true_coefficient_energy'] for r in selected]),
            omitted_energy_floor=span([r['omitted_energy_floor'] for r in selected]),
            coefficient_squared_error=span([r['coefficient_squared_error'] for r in selected]),
            error_square_mean={name:float(np.mean([r['error']['squares'][name] for r in selected])) for name in TERMS},
            error_cross_mean={name:float(np.mean([r['error']['cross'][name] for r in selected]))
                for name in selected[0]['error']['cross']},
            native_waveform_pass_count=sum(r['waveform']['native_pass'] for r in selected),
            true_coefficient_histogram_counts=np.sum([r['histogram']['true_counts'] for r in selected],axis=0).astype(int).tolist(),
            coefficient_error_histogram_counts=np.sum([r['histogram']['coefficient_error_counts'] for r in selected],axis=0).astype(int).tolist())
    return result


def main(args):
    root=args.root.resolve();source=args.source.resolve()
    if sha(Path(__file__))!=args.script_sha256:
        raise ValueError('mechanism extractor script SHA differs')
    contract=root/'contracts/pilot-initial-development-v1.json'
    c=json.loads(contract.read_text())
    if sha(contract)!=args.contract_sha256 or sha(source/'source-manifest.json')!=c['source_sha256']:
        raise ValueError('mechanism source/contract SHA differs')
    sys.path.insert(0,str(source))
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    eng_receipt=root/'evidence/pilot-initial-engineering-v1-engineering-raw-audit-v5.json'
    dev_receipt=root/'evidence/pilot-initial-development-v1-development-raw-audit.json'
    eng_summary=root/'runs/pilot-initial-engineering-v1/engineering/summary-v5.json'
    dev_summary=root/'runs/pilot-initial-development-v1/development/summary.json'
    producer_exit=root/'evidence/pilot-initial-development-v1-development-exit.json'
    audit_exit=root/'evidence/pilot-initial-development-v1-development-raw-audit-v6-exit.json'
    if (sha(eng_receipt)!=args.engineering_receipt_sha256
            or sha(dev_receipt)!=args.development_receipt_sha256
            or sha(dev_summary)!=args.development_summary_sha256):
        raise ValueError('audited mechanism input SHA differs')
    er,dr,es,ds,pe,ae=(json.loads(p.read_text()) for p in
        (eng_receipt,dev_receipt,eng_summary,dev_summary,producer_exit,audit_exit))
    if (er['status']!='PASS' or dr['status']!='PASS'
            or es['status']!='COMPLETE' or ds['status']!='COMPLETE'
            or er['summary_sha256']!=sha(eng_summary)
            or dr['summary_sha256']!=sha(dev_summary)
            or pe['exit_code']!=0 or ae['exit_code']!=0
            or pe['timed_out'] or ae['timed_out']
            or es['calls']!={'A':20,'E':16} or ds['calls']!={'A':300,'E':240}):
        raise ValueError('PILOT-02 producer/audit prerequisite differs')
    rows=[];new_e=0;omp_solves=0
    for summary in (es,ds):
        for entry in summary['records']:
            _,v=verified_record(entry,root)
            if entry['kind']=='A':
                row=row_from_a(v)
                if any(row[k]!=entry[k] for k in ('block','snr','arm')):
                    raise ValueError('saved mechanism A identity differs')
                rows.append(row)
            elif entry['kind']=='E':
                if (len(v['support_ids'])!=24 or v['resource_counts']['initialization_CE']!=1
                        or v['initializer_record']['recipe']['id']!='B0-p2-s0.5'
                        or v['initializer_record']['truth_access']!='none'):
                    raise ValueError('saved mechanism E initializer differs')
                new_e+=1;omp_solves+=v['resource_counts']['OMP_lstsq_solves']
            else:
                raise ValueError('unexpected mechanism call kind')
    keys={(r['block'],r['snr'],r['arm']) for r in rows}
    expected={(b,s,a) for b in range(32) for s in (7,8) for a in ARMS}
    if len(rows)!=320 or keys!=expected or new_e!=256 or omp_solves!=6400:
        raise ValueError('saved mechanism A/E inventory or solve ledger differs')
    report=dict(status='PASS',rows=rows,by_arm=aggregate(rows),
        ledger=dict(saved_A=320,saved_new_E=256,original_P02_reused=64,
            OMP_lstsq_solves=omp_solves,mechanism_new_initialization_CE=0,
            mechanism_new_BP=0,mechanism_new_LDPC=0,mechanism_new_F=0),
        labels=dict(truth='saved simulator H/Frobenius projection used only for scoring and oracle mechanism',
            Q='initial theoretical Q and colored probe were saved but not consumed by first initializer',
            Schur='zero/near-zero residual has explicit undefined mask; increments for undefined are placeholders',
            P1='contract gamma=(pilot energy/K24)*tr(G^-1) recomputed from saved Gram; producer auxiliary gamma omitted /K24 and remains separately exposed; gamma=1 only where actual K24 pilot Gram premises hold'),
        source_sha256=c['source_sha256'],contract_sha256=args.contract_sha256,
        script_sha256=args.script_sha256,
        engineering_receipt_sha256=args.engineering_receipt_sha256,
        development_receipt_sha256=args.development_receipt_sha256,
        development_summary_sha256=args.development_summary_sha256,
        producer_exit_sha256=sha(producer_exit),audit_exit_sha256=sha(audit_exit))
    with args.output.open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps(dict(status='PASS',saved_A=320,saved_new_E=256,
        output_sha256=sha(args.output),new_initialization_CE=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--script-sha256',required=True)
    p.add_argument('--contract-sha256',required=True)
    p.add_argument('--engineering-receipt-sha256',required=True)
    p.add_argument('--development-receipt-sha256',required=True)
    p.add_argument('--development-summary-sha256',required=True)
    main(p.parse_args())
