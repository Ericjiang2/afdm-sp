"""Bounded local quote. No development entry point and no automatic retries."""
import argparse
from collections import Counter
from contextlib import contextmanager
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

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MISSION = ROOT / '.mission/20261003_10-41-29-afdm-structured-inference-exploration'
OLD = ROOT / '.mission/20261001_23-33-35-afdm-innovation-space'
CONTRACT = MISSION / 'pipeline_contract.json'
OUT = MISSION / 'execution/pipeline_quote_v1'
CALLS = ('native_one', 'disabled_replay', 'native_two', 'pair', 'single')
THREAD_KEYS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
               'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def append(path, value):
    with Path(path).open('a') as stream:
        stream.write(json.dumps(value, allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def sources():
    paths = {CONTRACT}
    for name in ('sp_afdm_native_joint_20260921', 'sp_afdm_frozen_20260920'):
        base = ROOT/'experiments'/name
        for folder in ('src', 'tests', 'docs', 'protocol', 'upstream'):
            paths.update(p for p in (base/folder).rglob('*') if p.is_file()
                         and p.suffix != '.pyc' and '__pycache__' not in p.parts)
    folders = [HERE, ROOT/'experiments/afdm_inference_causal_20261002',
               OLD/'experiments', OLD/'acquisition', OLD/'geometry', OLD/'controls',
               ROOT/'issues/20261001-afdm-innovation-exploration/experiments',
               ROOT/'issues/20261001-afdm-innovation-exploration/theory']
    folders += [ROOT/'experiments'/p for p in ('tf_production_gap_audit_20260922',
                'tf_cstate_validation_20260922', 'tf_geometry_reopen_20260922',
                'cstate_necessity_stageA_20260928')]
    for folder in folders:
        paths.update(folder.glob('*.py'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def check_cache():
    up = ROOT/'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff'
    expected = {
        up/'afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz':
            'cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052',
        up/'07_checkpoint/frozen-c2rel-checkpoint.pt':
            '052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91'}
    for path, digest in expected.items():
        if not path.is_file() or sha(path) != digest:
            raise ValueError('frozen cache/checkpoint absent or mismatched; rebuild forbidden: '+str(path))


def validate_contract(contract):
    quote = contract['quote']
    expected = dict(seed=[20261003, 104129, 80, 81], clusters=1, snr_db=[20],
                    max_receiver_calls=5, cpu_cap_seconds=60, wall_cap_seconds=90)
    if any(quote.get(k) != v for k, v in expected.items()) or contract['threads'] != 1:
        raise ValueError('quote allocation/resource contract differs')
    if contract['arms'] != dict(native_two=dict(rounds=2, iterations=20),
                                native_one=dict(rounds=1, iterations=20),
                                pair=dict(rounds=1, block_size=2),
                                single=dict(rounds=1, block_size=1)):
        raise ValueError('registered receiver schedules differ')
    return quote


def finite(tree):
    import numpy as np
    if isinstance(tree, dict):
        for value in tree.values(): finite(value)
    elif isinstance(tree, (tuple, list)):
        for value in tree: finite(value)
    elif isinstance(tree, (np.ndarray, float, complex, np.number)) and not np.isfinite(tree).all():
        raise FloatingPointError('nonfinite receiver output')


def exact_tree(a, b, path=''):
    """Byte equality of numerical arrays; skip only explicit seconds fields."""
    import numpy as np
    if isinstance(a, np.ndarray):
        if not isinstance(b, np.ndarray) or a.dtype != b.dtype or a.shape != b.shape or a.tobytes() != b.tobytes():
            raise AssertionError('default-off array mismatch: '+path)
        return 1
    if isinstance(a, dict):
        if set(a) != set(b): raise AssertionError('default-off key mismatch: '+path)
        return sum(exact_tree(a[k], b[k], path+'/'+k) for k in a if k != 'seconds')
    if isinstance(a, (tuple, list)):
        if len(a) != len(b): raise AssertionError('default-off length mismatch: '+path)
        return sum(exact_tree(x, y, path+'/'+str(i)) for i, (x, y) in enumerate(zip(a, b)))
    if a != b: raise AssertionError('default-off scalar mismatch: '+path)
    return 0


@contextmanager
def observe_operations(native, candidate):
    """Count real invocation sites, not inferred asymptotic FFT budgets."""
    import numpy as np
    import physical
    import twofft
    count = Counter()
    patches = []
    def patch(owner, name, label, extra=None):
        original = getattr(owner, name)
        def wrapped(*args, **kwargs):
            count[label] += 1
            if extra: extra(count, args, kwargs)
            return original(*args, **kwargs)
        patches.append((owner, name, original))
        setattr(owner, name, wrapped)
    try:
        for name in ('pilot_front', 'time_refine', 'scalar_joint', 'decoder_messages'):
            patch(native, name, name)
        patch(candidate, 'gaussian_pair_pass', 'gaussian_pass')
        patch(candidate.GaussianPairLikelihood, 'block', 'gaussian_blocks')
        patch(candidate.GaussianPairLikelihood, 'likelihoods', 'gaussian_likelihood_batches',
              lambda c, a, k: c.update(local_word_likelihoods=len(a[2])))
        patch(physical.Channel, 'regressors', 'channel_regressors',
              lambda c, a, k: c.update(regressor_columns=a[0].p))
        for name in ('apply', 'adjoint'): patch(physical.Channel, name, 'channel_'+name)
        classes = {twofft.TimePathOps, candidate.CollapsedModel.__init__.__globals__['TWOFFT'].TimePathOps}
        for cls in classes:
            for name in ('responses_time', 'adjoint_time'):
                patch(cls, name, 'path_'+name)
        def transforms(c, a, k):
            value = np.asarray(a[0]); axis = k.get('axis', a[2] if len(a)>2 else -1)
            c.update(fft_vector_transforms=value.size//value.shape[axis])
        for name in ('fft', 'ifft'): patch(np.fft, name, 'numpy_'+name, transforms)
        for name in ('solve', 'cholesky'): patch(np.linalg, name, 'numpy_'+name)
        yield count
    finally:
        for owner, name, original in reversed(patches): setattr(owner, name, original)


def scores(decoder, truth, code):
    import numpy as np
    from scipy.special import expit
    bits = np.asarray(truth['coded'], dtype=int)
    decoded = np.asarray(decoder['decoded'], dtype=int)
    llr = np.asarray(decoder['incoming_llr'])
    if bits.shape != (2048,) or decoded.shape != bits.shape or llr.shape != bits.shape:
        raise ValueError('score dimensions differ')
    coded_errors = int(np.count_nonzero(decoded != bits))
    info_errors = int(np.count_nonzero(decoded[code['free_cols']] != truth['info']))
    syndrome = int(np.count_nonzero(code['H']@decoded % 2))
    return dict(bit_log_score=float(np.logaddexp(0, (2*bits-1)*llr).mean()),
                bit_brier=float(np.mean((expit(llr)-(1-bits))**2)), coded_errors=coded_errors,
                coded_FER=int(coded_errors>0), information_errors=info_errors,
                information_BER=info_errors/len(truth['info']), syndrome_weight=syndrome,
                undetected_frame_error=bool(coded_errors and not syndrome),
                decoder_iterations=int(decoder['iterations']), decode_ok=bool(decoder['decode_ok']))


def worker():
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT/'raw').mkdir()
    append(OUT/'attempts.jsonl', dict(event='stage_started', pid=os.getpid(), receiver_calls=0))
    # Cooperative signals preserve partial evidence; kernel/supervisor are backstops.
    def expired(*_): raise TimeoutError('registered quote resource deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGPROF, expired)
    signal.signal(signal.SIGXCPU, expired)
    signal.setitimer(signal.ITIMER_REAL, 88)
    signal.setitimer(signal.ITIMER_PROF, 58)
    resource.setrlimit(resource.RLIMIT_CPU, (59, 60))
    records = []
    calls_started = 0
    phase = 'registration'
    try:
        contract = json.loads(CONTRACT.read_text())
        quote = validate_contract(contract)
        check_cache()
        binding = sources()
        allocation = [dict(split='quote', index=0, snr_centi_db=2000,
                           component_seeds={name: hashlib.sha256(json.dumps(
                               [*quote['seed'], 0, component], separators=(',', ':')).encode()).hexdigest()
                                            for component, name in enumerate(('channel','message','noise'), 1)})]
        write(OUT/'allocation.json', allocation)
        registration = dict(contract=contract, source_files=binding, receiver_calls=list(CALLS),
                            seed_derivation='SHA256 UTF-8 compact JSON [contract seed...,cluster,component1..3]; digest bytes little-endian u32 SeedSequence',
                            allocation_sha256=sha(OUT/'allocation.json'),
                            timing='fresh worker imports/setup/generation/receiver/raw writes/scoring/hash audit included; supervisor startup separately recorded',
                            cost_projection=dict(multiplier=3, reserve_seconds=10, target_receiver_calls=24),
                            evidence_scope='one independent quote observation; no efficacy inference')
        write(OUT/'registration.json', registration)
        phase = 'bootstrap'
        for key in THREAD_KEYS: os.environ[key] = '1'
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        sys.path[:0] = [str(OLD/'experiments'), str(OLD/'controls')]
        import numpy as np
        import torch
        from threadpoolctl import threadpool_limits
        from thread_binding import blas_binding, verify_effective
        # Keep the controller alive until the worker finishes.
        controller = threadpool_limits(limits=1)
        initial_blas = blas_binding()
        import wrapper
        rt = wrapper.bootstrap(ROOT)
        rt.environment['effective_blas_post_bootstrap'] = blas_binding()
        from generate import generate
        sys.path.insert(0, str(ROOT))
        adapter = importlib.import_module('experiments.afdm_structured_inference_20261003.local_receiver')
        candidate = adapter._candidate()
        rt.evidence.verify_runtime_binding()
        verify_effective(rt)
        if any(binding.get(p) != digest for p, digest in rt.required_sources.items()):
            raise ValueError('runtime source set not covered by preregistration')
        runtime_reg = dict(source_files=binding, runtime_binding=wrapper.runtime_binding(rt),
                           candidate_options=wrapper.OPTIONS, allocation_sha256=sha(OUT/'allocation.json'))
        write(OUT/'runtime_registration.json', runtime_reg)
        write(OUT/'threads.json', dict(initial=initial_blas, actual=rt.environment,
                                      controller='threadpool_limits(1) lifetime through worker', pid=os.getpid()))
        setup = dict(wall_seconds=time.perf_counter()-wall_start, cpu_seconds=time.process_time()-cpu_start,
                     context_build_seconds=rt.setup, context_build_calls=1)
        write(OUT/'setup.json', setup)
        phase = 'generation'
        wall, cpu = time.perf_counter(), time.process_time()
        append(OUT/'attempts.jsonl', dict(event='generation_started'))
        generate(rt, OUT/'allocation.json', 'quote', OUT/'population', OUT/'runtime_registration.json')
        generation = dict(wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu)
        append(OUT/'attempts.jsonl', dict(event='generation_complete', **generation))
        results = {}
        for arm in CALLS:
            phase = arm
            if calls_started >= quote['max_receiver_calls']: raise RuntimeError('receiver call cap')
            verify_effective(rt)
            calls_started += 1
            append(OUT/'attempts.jsonl', dict(event='receiver_started', arm=arm, call=calls_started))
            wall, cpu = time.perf_counter(), time.process_time()
            operation_count = Counter()
            try:
                with observe_operations(rt.native, candidate) as operation_count:
                    # Load only observed arrays during receiver execution.
                    observed, _ = rt.evidence.load_artifact(OUT/'population/observed/data/quote_f000000.npz')
                    obs = observed['observation']
                    if arm == 'native_one': result = rt.native.receive(obs, rt.system, rt.code, rounds=1, iterations=20)
                    else:
                        result = adapter.receive(obs, rt.system, rt.code, enabled=arm in ('pair','single'),
                                                 rounds=2 if arm=='native_two' else 1,
                                                 block_size=1 if arm=='single' else 2)
                    finite(result)
                    raw = OUT/'raw'/f'{arm}.npz'
                    digest = rt.evidence.save_artifact(raw, dict(decoder=result[0], arrays=result[1], timing=result[2]),
                                                       dict(arm=arm, registration_sha256=sha(OUT/'registration.json')))
                record = dict(arm=arm, call=calls_started, status='complete',
                              wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
                              operation_calls=dict(operation_count), raw_path=str(raw.relative_to(OUT)), raw_sha256=digest)
                records.append(record)
                results[arm] = result
                append(OUT/'calls.jsonl', record)
                append(OUT/'attempts.jsonl', dict(event='receiver_complete', **record))
            except BaseException as error:
                append(OUT/'calls.jsonl', dict(arm=arm, call=calls_started, status='failed', exception=repr(error),
                                              wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
                                              operation_calls=dict(operation_count)))
                raise
        phase = 'external_scoring'
        exact_arrays = exact_tree(results['native_one'][:2], results['disabled_replay'][:2])
        truth, _ = rt.evidence.load_artifact(OUT/'population/truth/data/quote_f000000.npz')
        metrics = {arm: scores(result[0], truth, rt.code) for arm, result in results.items()}
        base = metrics['native_two']['coded_FER']
        for arm, metric in metrics.items():
            metric.update(rescued_vs_native_two=int(base and not metric['coded_FER']),
                          harmed_vs_native_two=int(not base and metric['coded_FER']))
        verify_effective(rt)
        wrapper.verify_runtime_registration(rt, runtime_reg)
        for path, digest in binding.items():
            if sha(ROOT/path) != digest: raise ValueError('end-of-quote source drift: '+path)
        totals = dict(wall_seconds=time.perf_counter()-wall_start, cpu_seconds=time.process_time()-cpu_start)
        projection = {}
        for key in ('cpu_seconds', 'wall_seconds'):
            measured = sum(r[key] for r in records if r['arm'] != 'disabled_replay')
            other = max(0., totals[key]-setup[key]-generation[key]-sum(r[key] for r in records))
            subtotal = setup[key]+6*generation[key]+6*measured+6*other
            projection[key] = dict(projected=subtotal, with_safety_reserve=3*subtotal+10,
                                   shared_setup=setup[key], generation_per_frame=generation[key],
                                   four_arm_calls=measured, measured_other_quote=other)
        projection['admitted_by_cost'] = (projection['cpu_seconds']['with_safety_reserve']<300
                                          and projection['wall_seconds']['with_safety_reserve']<420)
        output = dict(status='complete', receiver_calls=calls_started, raw_calls=records, metrics=metrics,
                      default_off=dict(status='byte_exact', numerical_arrays=exact_arrays),
                      setup=setup, generation=generation, totals=totals, development_projection=projection,
                      process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      rss_scope='macOS process cumulative high-water mark, includes setup/generation; not method-specific',
                      source_files_verified=len(binding), development_executed=False,
                      inference_scope='quote only; one observation cannot establish transfer/FER efficacy')
        write(OUT/'summary.json', output)
        append(OUT/'attempts.jsonl', dict(event='stage_complete', receiver_calls=calls_started,
                                         wall_seconds=time.perf_counter()-wall_start, cpu_seconds=time.process_time()-cpu_start))
        print(json.dumps(dict(status='complete', totals=totals, development_projection=projection)), flush=True)
    except BaseException as error:
        # Stop expensive work immediately, retaining every started call and partial file.
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
        write(OUT/'failure.json', dict(status='invalid_partial', phase=phase, receiver_calls=calls_started,
                                      completed_receiver_calls=len(records), exception=repr(error), traceback=traceback.format_exc(),
                                      wall_seconds=time.perf_counter()-wall_start, cpu_seconds=time.process_time()-cpu_start))
        append(OUT/'attempts.jsonl', dict(event='stage_failed', phase=phase, receiver_calls=calls_started, exception=repr(error)))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker()
        return
    if OUT.exists(): raise FileExistsError('preserve previous quote; automatic retry forbidden')
    validate_contract(json.loads(CONTRACT.read_text()))
    env = dict(os.environ, **{key:'1' for key in THREAD_KEYS}, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1')
    started = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker'], env=env)
    timed_out = False
    try:
        code = process.wait(timeout=90)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        code = process.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if OUT.exists():
        write(OUT/'supervisor.json', dict(returncode=code, hard_wall_timeout=timed_out,
                                         wall_seconds=time.perf_counter()-started,
                                         child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                                         limits='worker CPU kernel hard cap 60s; supervisor wall kill at90s; no retries'))
    if code != 0: raise SystemExit(code if code>0 else 1)


if __name__ == '__main__':
    main()
