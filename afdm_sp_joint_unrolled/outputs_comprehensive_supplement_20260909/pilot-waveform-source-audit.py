"""Tiny deterministic physical-contract audit; production channel code is unmodified."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import numpy as np
from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin


def relative(a,b):return float(np.linalg.norm(a-b)/np.linalg.norm(b))


def physical_matrix(env,delay,nu):
    """Propagate every actual IDAFT basis waveform through explicit CPP samples."""
    N=env.N_total;A,AH=env.build_daft_matrix();out=np.empty_like(AH)
    for n in range(N):
        index=n-delay
        sample=AH[index%N,:].copy()
        if index<0:sample*=np.exp(2j*np.pi*env.c1*(N*N+2*N*index))
        out[n,:]=np.exp(2j*np.pi*nu*n/N)*sample
    return A@out


def actual_expansion(env,delay,nu):
    # Inject only a deterministic physical path draw; execute the real expansion,
    # pruning, clipping, normalization and gen_h_daft body without reimplementation.
    env.generate_uwa_channel=lambda:(np.array([delay*env.delay_resolution]),np.array([1.+0j]),
        np.array([1]),np.array([1.]),np.array([nu/env.N_total*env.fs/env.fc]),np.array([0.]),1)
    H,_,params=env.generate_channel_matrix()
    return H,params


def run():
    rows=[]
    for N in (16,32):
        env=AFDMEnvMixin(N=N,M=1)
        for delay,kbase,kappa in ((0,0,0.),(1,1,0.),(3,-1,0.),
                                  (0,0,.25),(1,1,.25),(3,-1,-.25),
                                  (2,0,.4),(2,0,-.4)):
            nu=kbase+kappa;target=physical_matrix(env,delay,nu)
            offsets=np.arange(N)
            plus=np.array([env.dirichlet_alpha(int(m),kappa,N) for m in offsets])
            corrected=np.array([env.dirichlet_alpha(-int(m),kappa,N) for m in offsets])
            original_full=env.gen_h_daft(plus,np.full(N,delay),kbase+offsets)
            sign_diagnostic_full=env.gen_h_daft(corrected,np.full(N,delay),kbase+offsets)
            generated,params=actual_expansion(env,delay,nu)
            # The actual code returns globally scaled virtual gains; undo only
            # its reported scalar to distinguish pre/post global normalization.
            actual_pre=generated/params['fro_scale']
            chosen=params['k_exp'];mchosen=chosen-kbase
            trunc_corrected=env.gen_h_daft(np.array([env.dirichlet_alpha(-int(m),kappa,N) for m in mchosen]),
                np.full(len(chosen),delay),chosen)
            truncated_norm=trunc_corrected*np.sqrt(N)/np.linalg.norm(trunc_corrected)
            # Independent Fourier projection of actual physical positive Doppler.
            n=np.arange(N);positive=np.exp(2j*np.pi*kappa*n/N)
            projection=np.array([np.mean(positive*np.exp(-2j*np.pi*m*n/N)) for m in offsets])
            # Complete residue classes are interchangeable for integer Doppler
            # matrices; test a centered class independently of the original span.
            centered=np.arange(-N//2,N//2)
            centered_full=env.gen_h_daft(
                np.array([env.dirichlet_alpha(-int(m),kappa,N) for m in centered]),
                np.full(N,delay),kbase+centered)
            envelope=np.exp(2j*np.pi*np.outer(n,offsets)/N)@plus
            reversed_envelope=np.exp(2j*np.pi*kappa*((-n)%N)/N)
            renamed=physical_matrix(env,delay,kbase-kappa)
            best_gain=np.vdot(renamed,original_full)/np.vdot(renamed,renamed)
            row=dict(N=N,delay=delay,kbase=kbase,kappa=kappa,c1=env.c1,c2=env.c2,
                lambda_positive_error=relative(env.build_lambda_matrix(env.c1),np.diag(np.exp(2j*np.pi*env.c1*n*n))),
                dft_negative_sign_error=relative(env.F_N,np.exp(-2j*np.pi*np.outer(n,n)/N)/np.sqrt(N)),
                centered_full_N_diagnostic_error=relative(centered_full,target),
                integer_matrix_period_N_error=relative(env.gen_h_daft(plus,np.full(N,delay),kbase+offsets+N),original_full),
                current_cyclic_time_reversal_error=relative(envelope,reversed_envelope),
                renamed_negative_fraction_best_complex_gain_error=relative(original_full,best_gain*renamed),
                helper_period_N_at_zero_error=float(abs(env.dirichlet_alpha(N,0.,N)-1.)),
                helper_period_N_noninteger_error=float(max(abs(env.dirichlet_alpha(int(m)+N,kappa,N)-env.dirichlet_alpha(int(m),kappa,N)) for m in centered)) if kappa else None,
                unitarity_error=float(np.linalg.norm(env._A@env._A_H-np.eye(N))),
                full_N_current_alpha_plus_error=relative(original_full,target),
                full_N_diagnostic_alpha_minus_m_error=relative(sign_diagnostic_full,target),
                alpha_current_vs_physical_projection_error=relative(plus,projection),
                alpha_minus_m_vs_physical_projection_error=relative(corrected,projection),
                actual_truncated_prenormalization_error=relative(actual_pre,target),
                actual_truncated_global_normalized_error=relative(generated,target),
                diagnostic_sign_corrected_same_retained_bins_error=relative(trunc_corrected,target),
                diagnostic_sign_corrected_same_bins_normalized_error=relative(truncated_norm,target),
                actual_virtual_k=chosen.tolist(),actual_P=int(params['P_actual']),
                actual_fro_scale=float(params['fro_scale']),k_leak=env.k_leak,
                prune_relative_power=env.frac_prune_rel_thres,k_clip=env.k_max_cap,
                full_N_current_weight_energy=float(np.vdot(plus,plus).real))
            if kappa==0:
                direct=env.gen_h_daft(np.array([1.+0j]),np.array([delay]),np.array([kbase]))
                row['integer_gen_h_daft_vs_CPP_error']=relative(direct,target)
                if row['integer_gen_h_daft_vs_CPP_error']>1e-11:raise AssertionError('integer CPP contract mismatch')
            if row['full_N_diagnostic_alpha_minus_m_error']>1e-11:raise AssertionError('diagnostic positive Doppler projection mismatch')
            for field in ('dft_negative_sign_error','centered_full_N_diagnostic_error',
                          'integer_matrix_period_N_error','current_cyclic_time_reversal_error'):
                if row[field]>1e-11:raise AssertionError(field)
            if kappa and row['renamed_negative_fraction_best_complex_gain_error']<1e-3:
                raise AssertionError('fractional sign relabel unexpectedly explains current expansion')
            rows.append(row)
    source=ROOT/'afdm_sp_joint_unrolled/afdm_env.py'
    return dict(schema='pilot-waveform-source-audit-v2',scope='deterministic N16/32 contract diagnostics only; not N1024 or receiver performance',
        source=dict(path=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        derivation=dict(DAFT='A=Lambda_c2 F Lambda_c1 with positive-j Lambdas; F[p,n]=exp(-j2pi*p*n/N)/sqrt(N); s=A^H x',
            CPP='s_ext[n]=s[n+N] exp(+j2pi c1(N^2+2Nn)) for -delay<=n<0',
            propagation='r[n]=exp(+j2pi nu n/N) s_ext[n-delay]',
            integer='output m=(input q+2Nc1*delay+k) mod N; phase 2pi[-c1 delay^2+c2(m^2-q^2)-delay*q/N]',
            projection='coefficient at virtual kbase+m is mean_n exp(+j2pi(kappa-m)n/N)=dirichlet_alpha(-m,kappa,N)',
            current='dirichlet_alpha(m,kappa,N) instead projects onto the opposite integer offset; all-N discrepancy survives without truncation',
            period='Integer channel matrices are N-periodic in k; 0..N-1 and centered complete residue classes agree. The finite-sum Dirichlet coefficient is also N-periodic, but the production singular branch at x=N returns -1 for even N instead of +1; tested residue classes do not hit this singularity.',
            relabel='Current full-N envelope is exp(j2pi*kappa*((-n) mod N)/N). For n>0 it equals exp(j2pi*kappa)*exp(-j2pi*kappa*n/N), but at n=0 equals 1. Thus relabeling nu=kbase-kappa, even with a free global complex gain, cannot reproduce a noninteger path over the entire block.',
            diagnostic_only='minus-m comparisons change no production code or frozen G0 data; same-retained-bin residual isolates truncation but does not rerun a revised pruning selection'),
        limitations=['Default environment full support cap77 exceeds N16/32 and constructor prints FAIL; these are isolated single-path algebra checks, not full-support identifiability or deployable tiny-system configs.',
            'actual_truncated_prenormalization_error removes final global Frobenius scale only; actual per-path leakage normalization, clipping and pruning remain.',
            'CPP propagation is an independently constructed reference contract, not an executed production transmit/receive waveform chain. Integer consistency assumes 2*N*c1 is the tested integer; arbitrary chirps and MATLAB convention are outside scope.',
            'No finite-sample performance, pilot identifiability, N1024 or statistical claim follows from these checks.'],
        source_symbols=['AFDMEnvMixin.build_lambda_matrix','AFDMEnvMixin.build_daft_matrix','AFDMEnvMixin.gen_h_daft','AFDMEnvMixin.dirichlet_alpha','AFDMEnvMixin.generate_channel_matrix'],
        cases=rows,conclusion='Integer positive-Lambda/CPP/gen_h_daft contract matches. Fractional alpha(m+kappa) paired with virtual kbase+m has an offset-sign mismatch for positive physical Doppler; it is not solely truncation or global renormalization.',
        policy='No production edits, no frozen G0 changes, no halt to independent authorized BASE/H work.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();started=time.perf_counter();result=run();result['wall_seconds']=time.perf_counter()-started
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'cases':len(result['cases']),'maximum_integer_error':max(r.get('integer_gen_h_daft_vs_CPP_error',0) for r in result['cases']),
        'maximum_full_N_current_fractional_error':max(r['full_N_current_alpha_plus_error'] for r in result['cases']),
        'maximum_full_N_diagnostic_error':max(r['full_N_diagnostic_alpha_minus_m_error'] for r in result['cases'])}))


if __name__=='__main__':main()
