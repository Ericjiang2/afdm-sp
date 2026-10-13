"""Fixed six-observation/24-call development cohort, following a passed quote."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback

import pipeline_screen as shared

ROOT, OLD, MISSION = shared.ROOT, shared.OLD, shared.MISSION
OUT = MISSION/'execution/pipeline_development_v1'
QUOTE = MISSION/'execution/pipeline_quote_v1'
ARMS = ('native_two', 'native_one', 'pair', 'single')


def allocation(contract):
    cfg = contract['development']
    expected = dict(seed=[20261003, 104129, 80, 82], clusters=3, snr_db=[10, 20],
                    max_receiver_calls=24, cpu_cap_seconds=300, wall_cap_seconds=420)
    if any(cfg.get(k) != v for k, v in expected.items()):
        raise ValueError('development contract differs')
    shared.validate_contract(contract)
    rows = []
    for cluster in range(3):
        seeds = {name: hashlib.sha256(json.dumps([*cfg['seed'], cluster, component],
                  separators=(',', ':')).encode()).hexdigest()
                 for component, name in enumerate(('channel','message','noise'), 1)}
        for snr_index, snr in enumerate(cfg['snr_db']):
            index = 2*cluster+snr_index
            shift = index % 4
            rows.append(dict(split='development', index=index, cluster=cluster,
                             snr_centi_db=100*snr, component_seeds=seeds,
                             arm_order=list(ARMS[shift:]+ARMS[:shift])))
    return rows


def continuation_gate(aggregate):
    pair, base = aggregate['pair'], aggregate['native_two']
    soft = pair['bit_log_score'] <= .98*base['bit_log_score'] and pair['frame_errors'] <= base['frame_errors']
    rescue = pair['rescues'] > pair['harms'] and pair['bit_log_score'] <= base['bit_log_score']
    return dict(passed=bool(soft or rescue), soft_score_and_no_extra_errors=bool(soft),
                net_rescue_and_no_worse_score=bool(rescue),
                pair_log_score=pair['bit_log_score'], native_two_log_score=base['bit_log_score'],
                pair_frame_errors=pair['frame_errors'], native_two_frame_errors=base['frame_errors'],
                paired_rescues=pair['rescues'], paired_harms=pair['harms'])


def summarize(rows):
    import numpy as np
    result = {}
    for arm in ARMS:
        selected = [row for row in rows if row['arm']==arm]
        n = len(selected)
        if not n: raise ValueError('missing registered arm')
        result[arm] = dict(observations=n,
            bit_log_score=float(np.mean([r['bit_log_score'] for r in selected])),
            bit_brier=float(np.mean([r['bit_brier'] for r in selected])),
            frame_errors=sum(r['coded_FER'] for r in selected),
            coded_FER=float(np.mean([r['coded_FER'] for r in selected])),
            coded_errors=sum(r['coded_errors'] for r in selected),
            undetected_frame_errors=sum(r['undetected_frame_error'] for r in selected),
            information_errors=sum(r['information_errors'] for r in selected),
            information_BER=float(np.mean([r['information_BER'] for r in selected])),
            rescues=sum(r['rescued_vs_native_two'] for r in selected),
            harms=sum(r['harmed_vs_native_two'] for r in selected),
            timing={key:dict(mean=float(np.mean([r[key] for r in selected])),
                             sample_max=float(np.max([r[key] for r in selected])),
                             p95=float(np.quantile([r[key] for r in selected], .95)))
                    for key in ('cpu_seconds','wall_seconds')})
    return result


def array_sha(value):
    import numpy as np
    value = np.asarray(value)
    header = json.dumps(dict(dtype=str(value.dtype),shape=list(value.shape)),sort_keys=True).encode()
    return hashlib.sha256(header+value.tobytes()).hexdigest()


def external_audit(rt, rows, records):
    """Only after all receivers finish: reconstruct exogenous noise and score raw."""
    import numpy as np
    from afdm_sp_joint_unrolled.budgeted_support_eval import qpsk_map
    from afdm_sp_joint_unrolled.supplement_g1 import transform, propagate_cpp
    from analyze_reopening import observation_hash
    scores = []
    exogenous = []
    for row in rows:
        stem = f"development_f{row['index']:06d}"
        truth, _ = rt.evidence.load_artifact(OUT/'population/truth/data'/f'{stem}.npz')
        observed, _ = rt.evidence.load_artifact(OUT/'population/observed/data'/f'{stem}.npz')
        obs = observed['observation']
        if observation_hash(obs) != observed['observation_hash'] or truth['observation_hash'] != observed['observation_hash']:
            raise ValueError('saved truth/observation identity mismatch')
        words = np.frombuffer(bytes.fromhex(row['component_seeds']['noise']),dtype='<u4').astype(np.uint32).tolist()
        rng = np.random.default_rng(np.random.SeedSequence(words))
        noise = (rng.standard_normal(1024)+1j*rng.standard_normal(1024))/np.sqrt(2)
        data = np.sqrt(1-rt.system.rho)*qpsk_map(truth['coded'], scale=1)
        waveform = transform(obs['pilot']+data, rt.system.c1, rt.system.c2, inverse=True)
        noiseless = transform(propagate_cpp(waveform, rt.system.c1, truth['l_i'], truth['k_real'],
                                          truth['g_i'], prefix_length=rt.system.l_max_cap), rt.system.c1, rt.system.c2)
        reconstructed = noiseless+np.sqrt(obs['sigma2'])*noise
        error = float(np.max(np.abs(reconstructed-obs['y'])))
        if not np.isfinite(error) or error > 1e-11:
            raise ValueError('saved observation does not close under registered exogenous noise')
        hashes = {key:array_sha(truth[key]) for key in ('coded','info','l_i','k_real','g_i')}
        hashes.update(pilot=array_sha(obs['pilot']), noise=array_sha(noise), noiseless=array_sha(noiseless))
        exogenous.append(dict(cluster=row['cluster'], snr_centi_db=row['snr_centi_db'], hashes=hashes,
                              observation_hash=observed['observation_hash'], closure_max_abs_error=error,
                              noise_evidence='registered noise draw reconstructed only for external scoring; observed waveform closure verified'))
        current = [r for r in records if r['observation_id']==stem]
        if len(current)!=4 or {r['arm'] for r in current}!=set(ARMS):
            raise ValueError('incomplete or duplicate arm cohort')
        frame_scores = {}
        for record in current:
            if record['observation_hash']!=observed['observation_hash']:
                raise ValueError('arms did not receive identical observed arrays')
            path = OUT/record['raw_path']
            if shared.sha(path)!=record['raw_sha256']: raise ValueError('raw result hash mismatch')
            payload, _ = rt.evidence.load_artifact(path)
            shared.finite(payload)
            frame_scores[record['arm']] = dict(record, **shared.scores(payload['decoder'],truth,rt.code))
        base = frame_scores['native_two']['coded_FER']
        for record in frame_scores.values():
            record.update(rescued_vs_native_two=int(base and not record['coded_FER']),
                          harmed_vs_native_two=int(not base and record['coded_FER']))
            scores.append(record)
    for cluster in range(3):
        paired = [r for r in exogenous if r['cluster']==cluster]
        if len(paired)!=2 or paired[0]['hashes']!=paired[1]['hashes']:
            raise ValueError('cross-SNR exogenous array hashes differ')
    if len({r['hashes']['noise'] for r in exogenous})!=3:
        raise ValueError('independent clusters share noise stream')
    return scores, exogenous


def worker():
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT/'raw').mkdir()
    shared.append(OUT/'attempts.jsonl', dict(event='stage_started', pid=os.getpid(), receiver_calls=0))
    def expired(*_): raise TimeoutError('development resource deadline')
    for sig in (signal.SIGALRM, signal.SIGPROF, signal.SIGXCPU): signal.signal(sig, expired)
    signal.setitimer(signal.ITIMER_REAL, 418)
    signal.setitimer(signal.ITIMER_PROF, 298)
    resource.setrlimit(resource.RLIMIT_CPU, (299,300))
    records = []
    calls_started = 0
    phase = 'registration'
    try:
        contract = json.loads(shared.CONTRACT.read_text())
        rows = allocation(contract)
        quote = json.loads((QUOTE/'summary.json').read_text())
        if quote['status']!='complete' or quote['receiver_calls']!=5 or not quote['development_projection']['admitted_by_cost']:
            raise ValueError('complete passing quote cost gate required')
        shared.check_cache()
        binding = shared.sources()
        quote_reg = json.loads((QUOTE/'registration.json').read_text())
        if any(binding.get(p)!=digest for p,digest in quote_reg['source_files'].items()):
            raise ValueError('frozen quote sources changed')
        binding.update({str((QUOTE/name).relative_to(ROOT)):shared.sha(QUOTE/name)
                        for name in ('summary.json','registration.json','supervisor.json')})
        shared.write(OUT/'allocation.json', rows)
        registration = dict(contract=contract, source_files=binding, allocation_sha256=shared.sha(OUT/'allocation.json'),
            seed_derivation='SHA256 compact JSON [contract seed...,cluster,component1..3]; little-endian u32 SeedSequence; no SNR in seed',
            arm_order='cyclic rotation of native_two,native_one,pair,single by observation index modulo4; frozen before generation',
            observation_pairing='same physical channel, coded message, normalized noise and pilot across SNR in each cluster',
            external_audit='reconstruct normalized noise from registered seed; verify CPP waveform closure and cross-SNR array hashes after all receivers',
            timing='complete call includes observed load, verification, all inference/decoder operations and durable raw save; setup, generation and output audits separately retained',
            precision='3 independent clusters, 2 paired SNR per cluster; fixed feasibility screen, no powered efficacy test; sample p95 n6 is not reliable tail inference')
        shared.write(OUT/'registration.json', registration)
        phase = 'bootstrap'
        sys.path[:0] = [str(OLD/'experiments'),str(OLD/'controls')]
        import numpy as np
        import torch
        from threadpoolctl import threadpool_limits
        from thread_binding import blas_binding, verify_effective
        controller = threadpool_limits(limits=1)
        initial_blas = blas_binding()
        import wrapper
        rt = wrapper.bootstrap(ROOT)
        rt.environment['effective_blas_post_bootstrap'] = blas_binding()
        from generate import generate
        from analyze_reopening import observation_hash
        sys.path.insert(0,str(ROOT))
        adapter = importlib.import_module('experiments.afdm_structured_inference_20261003.local_receiver')
        candidate = adapter._candidate()
        rt.evidence.verify_runtime_binding()
        verify_effective(rt)
        if any(binding.get(p)!=digest for p,digest in rt.required_sources.items()):
            raise ValueError('runtime source binding incomplete')
        runtime_reg = dict(source_files=binding,runtime_binding=wrapper.runtime_binding(rt),
                           candidate_options=wrapper.OPTIONS,allocation_sha256=shared.sha(OUT/'allocation.json'))
        shared.write(OUT/'runtime_registration.json',runtime_reg)
        shared.write(OUT/'threads.json',dict(initial=initial_blas,actual=rt.environment,pid=os.getpid()))
        setup = dict(wall_seconds=time.perf_counter()-wall_start,cpu_seconds=time.process_time()-cpu_start,
                     context_build_seconds=rt.setup,context_build_calls=1)
        shared.write(OUT/'setup.json',setup)
        phase = 'generation'
        wall,cpu = time.perf_counter(),time.process_time()
        shared.append(OUT/'attempts.jsonl',dict(event='generation_started',observations=6))
        generate(rt,OUT/'allocation.json','development',OUT/'population',OUT/'runtime_registration.json')
        generation = dict(wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu)
        shared.append(OUT/'attempts.jsonl',dict(event='generation_complete',**generation))
        for row in rows:
            stem = f"development_f{row['index']:06d}"
            for arm in row['arm_order']:
                phase = f'{stem}/{arm}'
                if calls_started>=24: raise RuntimeError('development call cap')
                calls_started += 1
                shared.append(OUT/'attempts.jsonl',dict(event='receiver_started',call=calls_started,arm=arm,observation_id=stem))
                wall,cpu = time.perf_counter(),time.process_time()
                count = Counter()
                try:
                    verify_effective(rt)
                    with shared.observe_operations(rt.native,candidate) as count:
                        observed,_ = rt.evidence.load_artifact(OUT/'population/observed/data'/f'{stem}.npz')
                        obs = observed['observation']
                        digest_obs = observation_hash(obs)
                        if digest_obs!=observed['observation_hash']: raise ValueError('observation hash drift')
                        result = adapter.receive(obs,rt.system,rt.code,enabled=arm in ('pair','single'),
                                                 rounds=2 if arm=='native_two' else 1,block_size=1 if arm=='single' else 2)
                        if observation_hash(obs)!=digest_obs: raise ValueError('receiver mutated observation')
                        shared.finite(result)
                        raw = OUT/'raw'/f'{stem}_{arm}.npz'
                        digest = rt.evidence.save_artifact(raw,dict(decoder=result[0],arrays=result[1],timing=result[2]),
                            dict(observation_id=stem,arm=arm,registration_sha256=shared.sha(OUT/'registration.json')))
                    record = dict(observation_id=stem,cluster=row['cluster'],snr_centi_db=row['snr_centi_db'],arm=arm,
                                  call=calls_started,status='complete',wall_seconds=time.perf_counter()-wall,
                                  cpu_seconds=time.process_time()-cpu,operation_calls=dict(count),
                                  observation_hash=digest_obs,raw_path=str(raw.relative_to(OUT)),raw_sha256=digest)
                    records.append(record)
                    shared.append(OUT/'calls.jsonl',record)
                    shared.append(OUT/'attempts.jsonl',dict(event='receiver_complete',**record))
                except BaseException as error:
                    shared.append(OUT/'calls.jsonl',dict(observation_id=stem,arm=arm,call=calls_started,status='failed',
                        exception=repr(error),wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                        operation_calls=dict(count)))
                    raise
        phase = 'external_scoring_and_pairing'
        scored,exogenous = external_audit(rt,rows,records)
        shared.write(OUT/'scores_from_raw.json',scored)
        shared.write(OUT/'pairing_audit.json',dict(status='pass',clusters=3,rows=exogenous))
        counts = Counter()
        for record in records: counts.update(record['operation_calls'])
        required_counts = dict(pilot_front=24,time_refine=30,scalar_joint=18,decoder_messages=30,gaussian_pass=12,
                               channel_regressors=24,regressor_columns=12360,gaussian_blocks=9216,local_word_likelihoods=73728)
        if calls_started!=24 or any(counts[k]!=v for k,v in required_counts.items()):
            raise ValueError('actual operation/call accounting differs from registered cohort')
        verify_effective(rt)
        wrapper.verify_runtime_registration(rt,runtime_reg)
        for path,digest in binding.items():
            if shared.sha(ROOT/path)!=digest: raise ValueError('final source hash drift: '+path)
        aggregate = summarize(scored)
        gate = continuation_gate(aggregate)
        summary = dict(status='complete',receiver_calls=calls_started,observations=6,independent_clusters=3,
            aggregate=aggregate,
            by_cluster={str(c):summarize([r for r in scored if r['cluster']==c]) for c in range(3)},
            by_snr_db={str(s):summarize([r for r in scored if r['snr_centi_db']==100*s]) for s in (10,20)},
            transfer_gate=gate,setup=setup,generation=generation,operation_calls=dict(counts),
            totals=dict(wall_seconds=time.perf_counter()-wall_start,cpu_seconds=time.process_time()-cpu_start),
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            rss_scope='macOS whole process high-water mark including setup, generation and external scoring; no per-arm peak claim',
            source_files_verified=len(binding),pairing='all exogenous hashes equal across SNR within each cluster; all four arms observation-identical',
            probability_scores='negative log probability and Brier from saved clipped decoder incoming LLR; lower is better',
            tail_precision='six observations per arm in three independent clusters; empirical p95 is not a reliable population tail estimate',
            development_only=True,confirmation_stream90_opened=False,
            continuation='eligible to plan mechanism/powered confirmation' if gate['passed'] else 'MECH and FRESH not admitted; no qualified candidate in this fixed screen, not zero effect proof')
        shared.write(OUT/'summary.json',summary)
        shared.append(OUT/'attempts.jsonl',dict(event='stage_complete',receiver_calls=calls_started,
                      wall_seconds=time.perf_counter()-wall_start,cpu_seconds=time.process_time()-cpu_start))
        print(json.dumps(dict(status='complete',transfer_gate=gate,totals=summary['totals'])),flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.setitimer(signal.ITIMER_PROF,0)
        shared.write(OUT/'failure.json',dict(status='invalid_partial',phase=phase,receiver_calls=calls_started,
            completed_receiver_calls=len(records),exception=repr(error),traceback=traceback.format_exc(),
            wall_seconds=time.perf_counter()-wall_start,cpu_seconds=time.process_time()-cpu_start))
        shared.append(OUT/'attempts.jsonl',dict(event='stage_failed',phase=phase,exception=repr(error)))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.setitimer(signal.ITIMER_PROF,0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker()
        return
    if OUT.exists(): raise FileExistsError('preserve existing development; retries require a new explicit audit')
    allocation(json.loads(shared.CONTRACT.read_text()))
    env = dict(os.environ,**{key:'1' for key in shared.THREAD_KEYS},CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
    started = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--worker'],env=env)
    timed_out = False
    try: code = process.wait(timeout=420)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        code = process.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if OUT.exists():
        shared.write(OUT/'supervisor.json',dict(returncode=code,hard_wall_timeout=timed_out,
            wall_seconds=time.perf_counter()-started,child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            limits='kernel hard CPU300s; supervisor hard wall420s; no retries'))
    if code!=0: raise SystemExit(code if code>0 else 1)


if __name__=='__main__':
    main()
