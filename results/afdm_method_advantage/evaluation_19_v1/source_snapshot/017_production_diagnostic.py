"""Saved-observation diagnostics; never modifies the frozen receiver or campaign.

The fixed-H block control changes the gain model to an observed point estimate.
It is not exact shared-channel inference and does not isolate Gaussianization.
"""
import argparse
from contextlib import contextmanager
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.special import logsumexp

from experiments.afdm_shared_channel_20261004.common import ROOT, dump, run

OLD = ROOT / '.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/pipeline_development_v1'
WRAPPER = ROOT / '.mission/20261001_23-33-35-afdm-innovation-space/experiments'
ARMS = ('joint20', 'pair', 'joint1', 'fixed1', 'fixed20', 'observed_H_pair')
CONFIG = dict(seed=[20261004, 110000, 1], observations=6, independent_clusters=3,
              snr_db=[10, 20], arms=list(ARMS), receiver_calls=36, decoder_calls=36,
              outer_rounds=1, inner_iterations=[1, 20], pd=.5, noise='saved physical sigma2',
              new_observations=0, truth_access='offline scoring after all receivers',
              parity=dict(continuous_atol=1e-9, continuous_rtol=1e-10, decoded='exact'),
              interventions='same observed frontend; native joint/fixed inner1/20; point-estimate H pair',
              wall_cap_seconds=1200, timing='instrumented shared-machine diagnostic, not deployment latency')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_operators(channel):
    """Direct finite-DFT/CPP matrices, independent of the fast path helpers."""
    n = channel.n
    k = np.arange(n)
    f = np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)
    a = np.diag(np.exp(2j*np.pi*channel.c2*k*k)) @ f @ np.diag(np.exp(2j*np.pi*channel.c1*k*k))
    result = []
    for delay, doppler in zip(channel.delays, channel.dopplers):
        t = np.zeros((n, n), complex)
        for row in range(n):
            source = row - int(delay)
            wrap = np.exp(2j*np.pi*channel.c1*(n*n+2*n*source)) if source < 0 else 1
            t[row, source % n] = wrap*np.exp(2j*np.pi*doppler*row/n)
        result.append(a @ t @ a.conj().T)
    return np.stack(result)


def independent_words(n):
    if not 0 <= n <= 4:
        raise ValueError('bounded independent enumeration requires 0 <= n <= 4')
    bits = np.array(list(itertools.product((0, 1), repeat=2*n)), dtype=int).reshape(4**n, 2*n)
    return .5*((1-2*bits[:, :n])+1j*(1-2*bits[:, n:])), bits


def dense_gaussian(y, covariance, mean=None):
    residual = y if mean is None else y-mean
    sign, determinant = np.linalg.slogdet(covariance)
    if abs(sign-1) > 1e-10:
        raise ValueError('nonpositive covariance')
    return float(-len(y)*np.log(np.pi)-determinant-np.vdot(residual, np.linalg.solve(covariance, residual)).real)


def arithmetic_case(n, noise, block_size):
    from experiments.afdm_structured_inference_20261003.gaussian_pair import GaussianPairLikelihood
    from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel, PHYSICAL
    c = PHYSICAL.Channel(n, .37/n, .13/n**2, [0, n-1], [.23, -.38], [1, 1])
    model = CollapsedModel(c, np.zeros(2), np.eye(2)/2, noise)
    ops = independent_operators(c)
    pilot = np.sqrt(.5)*np.exp(.3j*np.arange(n))
    y = np.cos(.7*np.arange(n)) + 1j*np.sin(.4+.9*np.arange(n))
    ids = np.arange(block_size)
    outside = np.arange(block_size, n)
    local, bits = independent_words(block_size)
    external, _ = independent_words(len(outside))
    kernel = GaussianPairLikelihood(model, y, pilot)
    fast = kernel.likelihoods(kernel.block(ids), local)
    dense, moments, enumerated = [], [], []
    for word in local:
        x = pilot.copy(); x[ids] += word
        b = np.column_stack([u@x for u in ops])
        rest = sum(u[:, outside]@u[:, outside].conj().T for u in ops)*.25
        covariance = noise*np.eye(n)+rest+b@b.conj().T/2
        total = np.zeros((n, n), complex)
        for ext in external:
            full = x.copy(); full[outside] += ext
            response = np.column_stack([u@full for u in ops])
            total += noise*np.eye(n)+response@response.conj().T/2
        moments.append(covariance); enumerated.append(total/len(external))
        dense.append(dense_gaussian(y, covariance))
    raw = dict(y=y, pilot=pilot, operators=ops, ids=ids, words=local, bits=bits,
               fast_likelihood=fast, dense_likelihood=np.array(dense),
               conditional_covariance=np.array(moments), enumerated_second_moment=np.array(enumerated))
    result = dict(n=n, noise=noise, block_size=block_size, outside_words=len(external),
                  likelihood_max_abs=float(np.max(abs(fast-dense))),
                  moment_max_abs=float(np.max(abs(np.array(moments)-enumerated))))
    return result, raw


def calculate_audit(output):
    results = []
    for n, noise, block in itertools.product((2, 4), (.02, 2.), (1, 2)):
        result, raw = arithmetic_case(n, noise, block)
        np.savez_compressed(output/f'case_{len(results):02d}.npz', **raw)
        results.append(result)
    if max(r['likelihood_max_abs'] for r in results) > 1e-9 or max(r['moment_max_abs'] for r in results) > 1e-10:
        raise AssertionError('independent arithmetic contract failed')
    return dict(cases=results, receiver_calls=0, decoder_calls=0,
                conclusion='declared Gaussian arithmetic and conditional second moments verified; distribution exactness not implied')


def fixed_h_pair(y, pilot, h_matrix, noise, block_size=2):
    """Exact Gaussian-outside block calculation conditional on a fixed H.

    S_B = sigma2 I + pd H_O H_O^H. One full factorization followed by
    rank <= 2 downdates; all local normalized likelihood constants retained.
    H is the observed frontend point estimate, not a known true channel.
    """
    y, pilot, h_matrix = np.asarray(y), np.asarray(pilot), np.asarray(h_matrix)
    n = len(y)
    if (y.shape != (n,) or pilot.shape != (n,) or h_matrix.shape != (n, n)
            or block_size not in (1, 2) or n % block_size or noise <= 0
            or not all(np.isfinite(v).all() for v in (y, pilot, h_matrix, noise))):
        raise ValueError('invalid fixed-H block inputs')
    base = noise*np.eye(n)+.5*h_matrix@h_matrix.conj().T
    factor = cho_factor(base, lower=True)
    inverse_h = cho_solve(factor, h_matrix)
    residual = y-h_matrix@pilot
    inverse_y = cho_solve(factor, residual)
    base_logdet = 2*np.log(np.diag(factor[0]).real).sum()
    base_quad = np.vdot(residual, inverse_y).real
    app = np.empty(2*n)
    local_scores = []
    for start in range(0, n, block_size):
        ids = np.arange(start, min(n, start+block_size))
        words, bits = independent_words(len(ids))
        v, inv_v = h_matrix[:, ids], inverse_h[:, ids]
        gram = v.conj().T@inv_v
        matched = v.conj().T@inverse_y
        r = np.eye(len(ids))-.5*gram
        small = cho_factor(r, lower=True)
        logdet = base_logdet+2*np.log(np.diag(small[0]).real).sum()
        scores = []
        for word in words:
            eta = matched-gram@word
            quadratic = (base_quad-2*np.vdot(word, matched).real+np.vdot(word, gram@word).real
                         +.5*np.vdot(eta, cho_solve(small, eta)).real)
            scores.append(-n*np.log(np.pi)-logdet-quadratic)
        scores = np.asarray(scores)
        bit_ids = np.r_[ids, ids+n]
        app[bit_ids] = [logsumexp(scores[bits[:, j] == 0])-logsumexp(scores[bits[:, j] == 1])
                        for j in range(2*len(ids))]
        local_scores.append(scores)
    if not np.isfinite(app).all():
        raise FloatingPointError('nonfinite fixed-H block probabilities')
    return dict(app=app, extrinsic=app.copy(), log_likelihood=np.array(local_scores),
                full_factorizations=1, block_downdates=len(local_scores),
                likelihood_evaluations=sum(len(v) for v in local_scores))


def source_paths():
    registration = json.loads((OLD/'registration.json').read_text())
    paths = [ROOT/p for p in registration['source_files']]
    paths += [__file__, Path(__file__).with_name('test_production_diagnostic.py')]
    paths += [p for p in OLD.rglob('*') if p.is_file()]
    return paths


def verify_saved_sources():
    registration = json.loads((OLD/'registration.json').read_text())
    for name, expected in registration['source_files'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('frozen source changed: '+name)
    for domain in ('observed', 'truth'):
        base = OLD/'population'/domain
        seal = json.loads((base/(domain+'_seal.json')).read_text())
        for name, expected in seal['files'].items():
            if sha(base/name) != expected:
                raise ValueError('saved population seal mismatch: '+name)


def compare_saved(actual, expected):
    """Exact discrete parity and explicitly quantified continuous differences."""
    errors = {}
    for group in ('decoder', 'arrays'):
        keys = set(expected[group]) if group == 'arrays' else {'decoded', 'incoming_llr', 'raw_app', 'raw_check_extrinsic'}
        for key in keys:
            old, new = expected[group][key], actual[group][key]
            if not isinstance(old, np.ndarray):
                continue  # JSON trace dictionaries are compared via the live recorded states.
            if old.shape != new.shape or old.dtype != new.dtype:
                raise AssertionError('saved shape/dtype parity failed: '+key)
            error = float(np.max(abs(new-old))) if old.size else 0.
            errors[group+'/'+key] = error
            if old.dtype.kind in 'biu' or key.endswith('decoded'):
                if not np.array_equal(new, old):
                    raise AssertionError('saved discrete parity failed: '+key)
            elif not np.allclose(new, old, rtol=CONFIG['parity']['continuous_rtol'], atol=CONFIG['parity']['continuous_atol']):
                raise AssertionError('saved continuous parity failed: '+key)
    return errors


@contextmanager
def capture_front_and_detector(native):
    """Observe real API boundaries without altering any receiver argument."""
    captured = {}
    front, refine, scalar = native.pilot_front, native.time_refine, native.scalar_joint
    def traced_front(*args, **kwargs):
        value = front(*args, **kwargs)
        captured['front'] = {k:v.copy() for k, v in value.items() if isinstance(v, np.ndarray)}
        return value
    def traced_refine(*args, **kwargs):
        channel, detail = refine(*args, **kwargs)
        captured['channel'] = dict(delays=channel.delays.copy(), dopplers=channel.dopplers.copy(), gains=channel.gains.copy())
        return channel, detail
    def traced_scalar(*args, **kwargs):
        value = scalar(*args, **kwargs)
        captured['detector'] = value
        return value
    native.pilot_front, native.time_refine, native.scalar_joint = traced_front, traced_refine, traced_scalar
    try:
        yield captured
    finally:
        native.pilot_front, native.time_refine, native.scalar_joint = front, refine, scalar


def observed_h_receive(observation, rt):
    native = rt.native
    start = time.perf_counter()
    state = native.pilot_front(observation, rt.system, rt.code)
    channel, detail = native.time_refine(observation['y'], observation['pilot'], state['mu'], state['v'],
        state['delays'], state['dopplers'], state['gains'], rt.system.c1, rt.system.c2,
        observation['sigma2'], mode='soft', max_paths=8, rounds=2)
    # Full matrix construction is intentionally charged to this dense diagnostic.
    matrix = np.column_stack([channel.apply(e) for e in np.eye(channel.n)])
    detector = fixed_h_pair(observation['y'], observation['pilot'], matrix, observation['sigma2'])
    dec = native.decoder_messages(rt.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
    arrays = dict(r0_delays=channel.delays, r0_dopplers=channel.dopplers, r0_ce_gains=channel.gains,
                  r0_detector_app=detector['app'], r0_detector_extrinsic=detector['extrinsic'],
                  block_log_likelihood=detector['log_likelihood'], h_matrix=matrix)
    return dec, arrays, dict(seconds=time.perf_counter()-start, ce_evaluations=detail['evaluations'],
        full_factorizations=1, block_downdates=detector['block_downdates'],
        likelihood_evaluations=detector['likelihood_evaluations'],
        model='observed point-estimate H, uniform Gaussian outside; no gain integration')


def recount(rt, output):
    from experiments.afdm_structured_inference_20261003.pipeline_screen import scores
    records = [json.loads(line) for line in (OLD/'calls.jsonl').read_text().splitlines()]
    saved = json.loads((OLD/'scores_from_raw.json').read_text())
    if len(records) != 24 or len(saved) != 24:
        raise ValueError('incomplete saved production allocation')
    original = {(r['observation_id'], r['arm']):r for r in saved}
    rows = []
    for record in records:
        path = OLD/record['raw_path']
        if record['status'] != 'complete' or sha(path) != record['raw_sha256']:
            raise ValueError('saved call status/hash mismatch')
        payload, _ = rt.evidence.load_artifact(path)
        truth, _ = rt.evidence.load_artifact(OLD/'population/truth/data'/(record['observation_id']+'.npz'))
        if truth['observation_hash'] != record['observation_hash']:
            raise ValueError('saved truth identity mismatch')
        result = scores(payload['decoder'], truth, rt.code)
        reference = original[(record['observation_id'], record['arm'])]
        differences = {key:abs(float(value)-float(reference[key])) for key, value in result.items()}
        if max(differences.values()) > 1e-12:
            raise AssertionError('saved score recount mismatch')
        rows.append(dict(record, **result, recount_differences=differences))
    dump(output/'saved_recount.json', rows)
    return rows


def aggregate(rows):
    return {arm:dict(observations=len(selected), frame_errors=sum(r['coded_FER'] for r in selected),
                    coded_errors=sum(r['coded_errors'] for r in selected),
                    bit_log_score=float(np.mean([r['bit_log_score'] for r in selected])),
                    bit_brier=float(np.mean([r['bit_brier'] for r in selected])),
                    complete_wall_seconds=sum(r['wall_seconds'] for r in selected))
            for arm in sorted({r['arm'] for r in rows})
            if (selected := [r for r in rows if r['arm'] == arm])}


def prepare_runtime():
    """Build the actual frozen context and record its effective BLAS state."""
    sys.path[:0] = [str(WRAPPER), str(WRAPPER.parent/'controls')]
    import wrapper
    rt = wrapper.bootstrap(ROOT)
    sys.path.insert(0, str(ROOT))
    from thread_binding import verify_effective, blas_binding
    # bootstrap owns Torch binding; this caller owns the BLAS evidence field,
    # as in the original pipeline_development bootstrap sequence.
    rt.environment['effective_blas_post_bootstrap'] = blas_binding()
    verify_effective(rt)
    return rt


def calculate_production(output):
    verify_saved_sources()
    rt = prepare_runtime()
    import wrapper
    from thread_binding import verify_effective, blas_binding
    from analyze_reopening import observation_hash
    from experiments.afdm_structured_inference_20261003 import local_receiver as adapter
    from experiments.afdm_structured_inference_20261003 import pipeline_screen as shared
    candidate = adapter._candidate()
    verify_effective(rt)
    dump(output/'runtime.json', dict(binding=wrapper.runtime_binding(rt), effective=blas_binding(), setup_seconds=rt.setup))
    observed_rows = [json.loads(line) for line in (OLD/'population/observed/ledger.jsonl').read_text().splitlines()]
    if len(observed_rows) != 6 or len({r['observation_id'] for r in observed_rows}) != 6:
        raise ValueError('exactly six distinct saved observations required')
    records, baselines = [], {}

    def execute(row, arm):
        call = len(records)+1
        shared.append(output/'calls.jsonl', dict(event='started', call=call, arm=arm, observation_id=row['observation_id']))
        start, cpu = time.perf_counter(), time.process_time()
        count = {}
        try:
            observed, _ = rt.evidence.load_artifact(OLD/'population/observed'/row['observation_path'])
            obs = observed['observation']; before = observation_hash(obs)
            if before != row['observation_hash'] or sha(OLD/'population/observed'/row['observation_path']) != row['observation_sha256']:
                raise ValueError('saved observation identity mismatch')
            with shared.observe_operations(rt.native, candidate) as count:
                with capture_front_and_detector(rt.native) as capture:
                    if arm == 'pair':
                        result = adapter.receive(obs, rt.system, rt.code, enabled=True, rounds=1)
                    elif arm == 'observed_H_pair':
                        result = observed_h_receive(obs, rt)
                    else:
                        result = rt.native.receive(obs, rt.system, rt.code, rounds=1,
                            iterations=20 if arm.endswith('20') else 1,
                            gain_mode='fixed' if arm.startswith('fixed') else 'joint', record_states=True)
            payload = dict(decoder=result[0], arrays=result[1], timing=result[2], captured=capture)
            if observation_hash(obs) != before:
                raise AssertionError('receiver mutated observed input')
            shared.finite(payload)
            raw = output/'raw'/(row['observation_id']+'_'+arm+'.npz')
            if raw.exists():
                raise FileExistsError('preserve existing diagnostic output')
            digest = rt.evidence.save_artifact(raw, payload, dict(observation_id=row['observation_id'], arm=arm, observation_sha256=row['observation_sha256']))
            record = dict(call=call, observation_id=row['observation_id'], cluster=row['frame']//2,
                snr_centi_db=row['snr_centi_db'], arm=arm, status='complete',
                observation_hash=before, raw_path=str(raw.relative_to(output)), raw_sha256=digest,
                wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu, operation_calls=dict(count))
            if count['decoder_messages'] != 1:
                raise AssertionError('exactly one actual decoder call per arm required')
            records.append(record); shared.append(output/'calls.jsonl', dict(event='complete', **record))
            return payload
        except BaseException as error:
            shared.append(output/'calls.jsonl', dict(event='failed', call=call, arm=arm,
                observation_id=row['observation_id'], error=repr(error), wall_seconds=time.perf_counter()-start,
                cpu_seconds=time.process_time()-cpu, operation_calls=dict(count)))
            raise

    # Every saved baseline is verified before any intervention is evaluated.
    parity = []
    for row in observed_rows:
        for arm, old_arm in (('joint20', 'native_one'), ('pair', 'pair')):
            actual = execute(row, arm)
            saved, _ = rt.evidence.load_artifact(OLD/'raw'/(row['observation_id']+'_'+old_arm+'.npz'))
            differences = compare_saved(actual, saved)
            parity.append(dict(observation_id=row['observation_id'], arm=arm, differences=differences))
            if arm == 'joint20':
                baselines[row['observation_id']] = actual['captured']
            else:
                baseline = baselines[row['observation_id']]
                for group in ('front', 'channel'):
                    for key, value in baseline[group].items():
                        if not np.array_equal(value, actual['captured'][group][key]):
                            raise AssertionError('pair/native observed frontend differs')
    dump(output/'baseline_parity.json', parity)
    fronts = []
    for row in observed_rows:
        baseline = baselines[row['observation_id']]
        for arm in ARMS[2:]:
            actual = execute(row, arm)
            captured = actual['captured']
            differences = {}
            for group in ('front', 'channel'):
                for key, original in baseline[group].items():
                    current = captured[group][key]
                    differences[group+'/'+key] = float(np.max(abs(current-original)))
                    if not np.array_equal(current, original):
                        raise AssertionError('observed frontend changed between paired arms')
            fronts.append(dict(observation_id=row['observation_id'], arm=arm, differences=differences))
    dump(output/'frontend_pairing.json', fronts)
    if len(records) != CONFIG['receiver_calls']:
        raise AssertionError('full registered receiver allocation not completed')
    # Open truth only after the whole observed-only run is durably saved.
    old_scores = recount(rt, output)
    scored = []
    for record in records:
        truth, _ = rt.evidence.load_artifact(OLD/'population/truth/data'/(record['observation_id']+'.npz'))
        if truth['observation_hash'] != record['observation_hash']:
            raise ValueError('diagnostic truth identity mismatch')
        if sha(output/record['raw_path']) != record['raw_sha256']:
            raise ValueError('diagnostic raw hash mismatch')
        payload, _ = rt.evidence.load_artifact(output/record['raw_path'])
        scored.append(dict(record, **shared.scores(payload['decoder'], truth, rt.code)))
    dump(output/'scores.json', scored)
    paired = []
    for row in observed_rows:
        arms = {r['arm']:r for r in scored if r['observation_id'] == row['observation_id']}
        for high, low in (('joint20', 'joint1'), ('fixed20', 'fixed1'), ('observed_H_pair', 'pair')):
            paired.append(dict(observation_id=row['observation_id'], contrast=high+' minus '+low,
                coded_errors=arms[high]['coded_errors']-arms[low]['coded_errors'],
                bit_log_score=arms[high]['bit_log_score']-arms[low]['bit_log_score']))
    dump(output/'paired_differences.json', paired)
    verify_saved_sources(); rt.evidence.verify_runtime_binding()
    return dict(receiver_calls=len(records), decoder_calls=sum(r['operation_calls']['decoder_messages'] for r in records),
        new_observations=0, observations=6, independent_clusters=3, old=aggregate(old_scores), actual=aggregate(scored),
        max_saved_parity_error=max(max(r['differences'].values()) for r in parity),
        frontend_pairing='exact for every observed front/refine array',
        conclusion='bounded causal-development evidence; no broad FER or single-cause attribution',
        confounds=['joint/fixed changes both gain updates and gain variance',
                   'observed-H pair changes the gain prior to a data-dependent point estimate',
                   'geometry error, gain prior mismatch, outside Gaussianization and schedule remain distinct'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['audit', 'production'])
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    config = CONFIG if args.mode == 'production' else dict(seed=CONFIG['seed'], n=[2, 4], noise=[.02, 2.], block_size=[1, 2], receiver_calls=0)
    return run(args.stage, config, source_paths(), calculate_production if args.mode == 'production' else calculate_audit,
               wall_seconds=1200 if args.mode == 'production' else 600)


if __name__ == '__main__':
    main()
