"""Registered known-geometry, correct-prior scale diagnosis; no production calls."""
from pathlib import Path
import hashlib
import json
import os
import platform
import runpy
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
MISSION=ROOT/'.mission/20261003_10-41-29-afdm-structured-inference-exploration'
CONTRACT=MISSION/'transfer_scale_contract.json'
OUTPUT=MISSION/'execution/transfer_scale_v1'
THREAD_HELPER=ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'

from experiments.afdm_structured_inference_20261003.common import dump,hashes


def append_event(path,value):
    with path.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(value,allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_contract(contract):
    required=dict(seed=[20261003,104129,80,83],N=[4,16,64],P=2,draws_per_N=3,
                  noise_variance=.02,pilot_energy=.5,data_energy=.5,
                  arms=['gaussian_pair','gaussian_single','scalar_joint20'],
                  registered_scalar_calls=9,production_calls=0,cpu_cap_seconds=30,
                  wall_cap_seconds=60,no_confirmation=True)
    if any(contract.get(key)!=value for key,value in required.items()):
        raise ValueError('scale diagnosis allocation/config differs from frozen contract')
    if contract['geometry']!=dict(delays=[0,1],dopplers=[.23,-.38],c1='0.37/N',c2='0.13/N^2'):
        raise ValueError('known geometry differs from frozen contract')


def main():
    contract=json.loads(CONTRACT.read_text())
    validate_contract(contract)
    OUTPUT.mkdir(parents=True,exist_ok=False)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS'):
        os.environ[key]='1'
    os.environ['CUDA_VISIBLE_DEVICES']=''
    import numpy as np
    from scipy.special import expit
    from threadpoolctl import threadpool_limits
    from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel,PHYSICAL,TWOFFT,dense_operators,SOURCES
    from experiments.afdm_structured_inference_20261003.gaussian_pair import gaussian_pair_pass
    from experiments.afdm_structured_inference_20261003.pair_message import probability_error
    from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk,exact_posterior
    sources=list(dict.fromkeys(map(str,[*SOURCES,__file__,CONTRACT,THREAD_HELPER,
                   Path(__file__).with_name('gaussian_pair.py'),Path(__file__).with_name('pair_message.py'),
                   Path(__file__).with_name('message.py'),Path(__file__).with_name('common.py')])))
    fingerprint=hashes(sources)
    with threadpool_limits(limits=1):
        binding=runpy.run_path(str(THREAD_HELPER))['blas_binding']()
        dump(OUTPUT/'registration.json',dict(contract=contract,source_sha256=fingerprint,
             contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
             effective_threads=binding,platform=platform.platform(),python=sys.version,numpy=np.__version__,
             pid=os.getpid(),argv=sys.argv,
             scalar_options=dict(iterations=20,damping=.3,pd=.5,gain_mode='joint',observation_domain='time'),
             interpretation='known fixed geometry mathematical model; no production/LDPC; separate independent streams per N/draw',
             timer_scope='per-arm geometry setup + identical observed pilot ridge + detector + raw NPZ/trace write; generation/scoring/oracle excluded from arm cost but included in stage'))
        start=time.monotonic();cpu_start=time.process_time()
        old_handlers={kind:signal.getsignal(kind) for kind in (signal.SIGALRM,signal.SIGPROF)}
        def timeout(_signal,_frame):
            raise TimeoutError('registered scale diagnosis CPU/wall cap exceeded')
        for kind in old_handlers:
            signal.signal(kind,timeout)
        signal.setitimer(signal.ITIMER_REAL,contract['wall_cap_seconds'])
        signal.setitimer(signal.ITIMER_PROF,contract['cpu_cap_seconds'])
        rows=[];scalar_calls=0;local_calls=0
        try:
            for n in contract['N']:
                for draw in range(contract['draws_per_N']):
                    # Explicit independent stream per size and replicate; no
                    # cross-size sample pairing is inferred from equal draw IDs.
                    rng=np.random.default_rng([*contract['seed'],n,draw])
                    bits=rng.integers(0,2,size=2*n)
                    data=.5*((1-2*bits[:n])+1j*(1-2*bits[n:]))
                    gain=(rng.normal(size=2)+1j*rng.normal(size=2))/2
                    pilot=np.sqrt(.5)*np.exp(.3j*np.arange(n))
                    geometry=PHYSICAL.Channel(n,.37/n,.13/n**2,[0,1],[.23,-.38],gain)
                    noise=(rng.normal(size=n)+1j*rng.normal(size=n))*np.sqrt(.02/2)
                    y=geometry.apply(pilot+data)+noise
                    np.savez(OUTPUT/f'input_n{n:03d}_draw{draw}.npz',y=y,pilot=pilot,truth_bits=bits,
                             truth_gain=gain,noise=noise,truth_data=data,delays=geometry.delays,
                             dopplers=geometry.dopplers,c1=geometry.c1,c2=geometry.c2,
                             seed=np.array([*contract['seed'],n,draw]))
                    exact=None;oracle_time=None
                    if n==4:
                        oracle_start=time.perf_counter()
                        words,labels=enumerate_qpsk(n)
                        exact=exact_posterior(y,dense_operators(geometry),pilot,words,[0,0],np.eye(2)/2,.02,bits=labels)
                        oracle_time=time.perf_counter()-oracle_start
                        np.savez(OUTPUT/f'oracle_n004_draw{draw}.npz',exact_llr=exact.llr,
                                 probabilities=exact.probabilities,words=words,bits=labels)
                    initial_reference=None
                    for arm in contract['arms']:
                        append_event(OUTPUT/'events.jsonl',dict(event='arm_started',n=n,draw=draw,arm=arm,
                                     local_calls_started=local_calls+1,scalar_calls_started=scalar_calls+(arm=='scalar_joint20')))
                        local_calls+=1
                        arm_start=time.perf_counter();arm_cpu=time.process_time()
                        # Identical observed-only initialization is paid by all
                        # arms; its gains are ignored by the collapsed candidate.
                        c=PHYSICAL.Channel(n,.37/n,.13/n**2,[0,1],[.23,-.38],[0,0])
                        b=c.regressors(pilot)
                        initial=np.linalg.solve(b.conj().T@b+.02*2*np.eye(2),b.conj().T@y)
                        initialized=PHYSICAL.Channel(n,c.c1,c.c2,c.delays,c.dopplers,initial)
                        if arm=='scalar_joint20':
                            scalar_calls+=1
                            result=TWOFFT.scalar_joint(y,pilot,initialized,.02,pd=.5,prior=np.zeros(2*n),
                                                       iterations=20,damping=.3,gain_mode='joint',record_states=False,
                                                       observation_domain='time')
                            llr=result['app']
                            extra=dict(final_gains=result['gains'],gain_variance=result['gain_variance'],
                                       soft_data_mean=result['mu'],soft_data_variance=result['variance'])
                            dump(OUTPUT/f'trace_n{n:03d}_draw{draw}_{arm}.json',result['trace'])
                        else:
                            model=CollapsedModel(initialized,[0,0],np.eye(2)/2,.02)
                            result=gaussian_pair_pass(model,y,pilot,np.zeros(2*n),
                                                     block_size=2 if arm=='gaussian_pair' else 1)
                            llr=result['app'];extra={}
                        if not np.isfinite(llr).all() or llr.shape!=(2*n,):
                            raise FloatingPointError('nonfinite or invalid detector bit LLRs')
                        np.savez(OUTPUT/f'raw_n{n:03d}_draw{draw}_{arm}.npz',app=llr,
                                 extrinsic=result['extrinsic'],initial_gains=initial,**extra)
                        elapsed=time.perf_counter()-arm_start;cpu=time.process_time()-arm_cpu
                        if initial_reference is None:
                            initial_reference=initial
                        elif not np.array_equal(initial_reference,initial):
                            raise AssertionError('observed pilot-only initialization differs between arms')
                        error_count=int(np.count_nonzero((llr<0).astype(int)!=bits))
                        row=dict(n=n,draw=draw,arm=arm,bit_count=2*n,uncoded_bit_errors=error_count,
                                 uncoded_ber=error_count/(2*n),uncoded_frame_error=bool(error_count),
                                 proper_bit_logscore=float(np.logaddexp(0,(2*bits-1)*llr).mean()),
                                 brier=float(np.mean((expit(llr)-(1-bits))**2)),
                                 full_local_wall_seconds=elapsed,full_local_cpu_seconds=cpu,
                                 known_geometry=True,matched_working_gain_prior=True,
                                 n4_exact_error=None if exact is None else probability_error(exact.llr,llr),
                                 oracle_seconds=oracle_time,
                                 algorithm_counters={key:result[key] for key in ('iterations','fft_count','blocks','likelihood_evaluations') if key in result})
                        rows.append(row)
                        append_event(OUTPUT/'events.jsonl',dict(event='arm_complete',**row))
            if scalar_calls!=9 or local_calls!=27 or len(rows)!=27:
                raise AssertionError('registered scale allocation incomplete')
            if hashes(sources)!=fingerprint:
                raise RuntimeError('bound source changed during scale diagnosis')
            if runpy.run_path(str(THREAD_HELPER))['blas_binding']()!=binding:
                raise RuntimeError('effective thread binding changed')
            summary={}
            for n in contract['N']:
                summary[str(n)]={}
                for arm in contract['arms']:
                    selected=[r for r in rows if r['n']==n and r['arm']==arm]
                    summary[str(n)][arm]=dict(independent_draws=3,
                        bit_count=sum(r['bit_count'] for r in selected),
                        uncoded_bit_errors=sum(r['uncoded_bit_errors'] for r in selected),
                        uncoded_frame_errors=sum(r['uncoded_frame_error'] for r in selected),
                        **{key:float(np.mean([r[key] for r in selected])) for key in
                           ('proper_bit_logscore','brier','uncoded_ber','full_local_wall_seconds','full_local_cpu_seconds')})
                    if n==4:
                        summary[str(n)][arm]['exact_marginal_error']={key:float(np.mean([r['n4_exact_error'][key] for r in selected])) for key in rows[0]['n4_exact_error']}
            dump(OUTPUT/'raw.json',rows)
            dump(OUTPUT/'results.json',dict(summary=summary,scalar_calls=scalar_calls,local_calls=local_calls,
                 production_calls=0,ldpc_calls=0,source_hashes_unchanged=True,
                 timing='complete local arm includes common observed pilot-only initialization/detector/raw write; not production receiver latency',
                 paired_comparison='within each N/draw only; sizes use independent samples',
                 scientific_scope='correct Gaussian working gain prior, uniform uncoded QPSK, fixed known geometry; no scientific candidate modification'))
            dump(OUTPUT/'attempt.json',dict(status='complete',cpu_seconds=time.process_time()-cpu_start,
                 wall_seconds=time.monotonic()-start,scalar_calls=scalar_calls,local_calls=local_calls))
        except BaseException as error:
            dump(OUTPUT/'attempt.json',dict(status='invalid_partial',error=repr(error),
                 cpu_seconds=time.process_time()-cpu_start,wall_seconds=time.monotonic()-start,
                 scalar_calls=scalar_calls,local_calls=local_calls,completed_rows=len(rows)))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.setitimer(signal.ITIMER_PROF,0)
            for kind,handler in old_handlers.items():
                signal.signal(kind,handler)
    print(json.dumps(dict(output=str(OUTPUT),status='complete',scalar_calls=scalar_calls,local_calls=local_calls)))


if __name__=='__main__':
    main()
