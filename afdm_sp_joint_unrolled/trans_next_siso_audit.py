"""Raw full-chain audit with separate per-symbol Gaussian cavity systems."""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
from scipy.linalg import solve
from .bottleneck_pilot import hashes, load_state, observed_at_snr, offline_scores, sha
from .budgeted_support_diagnostics import array_hash
from .light_gap_replay import CODE_KEYS, verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS, receiver_resources
from .light_gap_receiver_audit import check_ce, check_feedback
from .e1_ldpc import build_code, decode_llr
from .supplement_messages import decoder_messages


def finite_arrays(value):
    if isinstance(value, np.ndarray):
        if not np.isfinite(value).all():
            raise ValueError('nonfinite raw array')
        return 1
    if isinstance(value, dict):
        return sum(finite_arrays(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(finite_arrays(v) for v in value)
    return 0


def check_siso_state(state, *, cavity=True):
    """Audit all scalar messages; directly exclude 3 predetermined symbols.

    The cavity solves reconstruct C without symbol j, avoiding the producer's
    Sherman-Morrison denominator. This is an independent numerical identity
    check, not an independent scientific reviewer or a discrete MAP oracle.
    """
    H, y = state['H'].astype(np.complex128), state['y'].astype(np.complex128)
    n = len(y)
    prior = state['consumed_prior']
    mean = .5*(np.tanh(prior[:n]/2)+1j*np.tanh(prior[n:]/2))
    variance = np.maximum(.5-abs(mean)**2, 0.)
    np.testing.assert_allclose(state['prior_mean'], mean, rtol=0, atol=1e-15)
    np.testing.assert_allclose(state['prior_variance'], variance, rtol=0, atol=1e-15)
    channel = state['channel_llr']
    natural = state['extrinsic_natural']
    np.testing.assert_array_equal(channel, 2*np.concatenate((natural.real, natural.imag)))
    np.testing.assert_allclose(state['extrinsic_denominator'], 1-variance*state['leverage'], rtol=0, atol=1e-15)
    np.testing.assert_allclose(state['extrinsic_precision'],
        state['leverage']/state['extrinsic_denominator'], rtol=1e-14, atol=1e-14)
    np.testing.assert_array_equal(state['posterior_llr'], channel+prior)
    app = channel+prior
    posterior = .5*(np.tanh(app[:n]/2)+1j*np.tanh(app[n:]/2))
    np.testing.assert_allclose(state['posterior_mean'], posterior, rtol=0, atol=1e-15)
    np.testing.assert_allclose(state['posterior_variance'], np.maximum(.5-abs(posterior)**2, 0.), rtol=0, atol=1e-15)
    if (state['linear_solves'] != 1 or state['linear_rhs'] != n+1
            or state['factorization_dimension'] != n or state['linear_relative_residual'] > 1e-9
            or np.any(state['extrinsic_denominator'] <= 0)):
        raise ValueError('invalid SISO solve evidence')
    errors = []
    for j in sorted(set((0, n//2, n-1))) if cavity else []:
        other_v, other_m = variance.copy(), mean.copy()
        other_v[j], other_m[j] = 0., 0.
        covariance = (H*other_v)@H.conj().T+state['sigma2']*np.eye(n)
        rhs = np.column_stack((y-H@other_m, H[:, j]))
        solution = solve(covariance, rhs, assume_a='pos', check_finite=True)
        eta = np.vdot(H[:, j], solution[:, 0])
        precision = np.vdot(H[:, j], solution[:, 1])
        expected = 2*np.array([eta.real, eta.imag])
        actual = channel[[j, n+j]]
        np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-9)
        np.testing.assert_allclose(state['extrinsic_precision'][j], precision, rtol=1e-9, atol=1e-9)
        errors.append(float(np.max(abs(actual-expected))))
    return max(errors) if errors else None


def audit(root, contract_path, source_manifest):
    started = time.time()
    c = json.loads(contract_path.read_text())
    stage = c.get('stage', 'engineering')
    if stage not in ('engineering', 'development'):
        raise ValueError('unknown SISO audit stage')
    engineering = stage == 'engineering'
    summary_path = root/'runs'/c['tag']/stage/'summary.json'
    summary = json.loads(summary_path.read_text())
    exit_record = json.loads((root/'evidence'/(c['tag']+('-engineering' if engineering else '')+'-exit.json')).read_text())
    if (summary['status'] != 'COMPLETE' or exit_record['exit_code'] != 0 or exit_record['timed_out']
            or summary['contract_sha256'] != sha(contract_path) or summary['source_sha256'] != sha(source_manifest)
            or sha(c['input_summary']) != c['input_summary_sha256']):
        raise ValueError('incomplete or mismatched SISO engineering evidence')
    inputs = json.loads(Path(c['input_summary']).read_text())
    exo = {e['block']: e for e in inputs['exogenous']}
    refs = {(r['block'], r['snr'], r['arm']): r for r in inputs['records']}
    configs = {a['name']: a for a in c['arms']}
    code_cache = Path(os.environ['TMPDIR'])/'audit-code'
    code_cache.mkdir()
    code = build_code(cache_dir=code_cache)
    env = json.loads(summary_path.with_name('environment.json').read_text())
    if hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
        raise ValueError('audit LDPC identity differs')
    seen, repeat = set(), {}
    arrays = ce_count = siso_count = nested_decodes = cavity_count = 0
    comparisons, resources = [], {}
    for item in summary['records']:
        key = (item['block'], item['snr'], item['arm'])
        if key in seen:
            raise ValueError('duplicate full-chain record')
        seen.add(key)
        r, value = verified_record(item, root)
        reservation = json.loads(Path(item['record']).with_name(r['token']+'-reserve.json').read_text())
        if any(reservation[k] != r[k] for k in ('token', 'block', 'snr', 'arm', 'split', 'kind')):
            raise ValueError('full-chain reservation differs')
        config = configs[r['arm']]
        if r['configuration'] != config:
            raise ValueError('record differs from contracted arm')
        raw = load_state(exo[r['block']]['state'])
        observed = observed_at_snr(raw, r['snr'])
        if hashes(observed) != r['observed_hashes'] or offline_scores(value, raw, value['H']) != r['scores'] or r['scores'] != item['scores']:
            raise ValueError('paired observation or raw score differs')
        arrays += finite_arrays(value)
        consumers = {x['iteration']: x for x in value['code_feedback_records'] if x['stage'] == 'CE_consume'}
        for state in value['dals']:
            check_ce(state, observed, raw['params'], consumers[state['outer_iter']], config['receiver'])
            ce_count += 1
        check_feedback(value, config)
        decoded, ok = decode_llr(code, value['llr'], maxiter=50)
        np.testing.assert_array_equal(decoded, value['decoded'])
        if bool(ok) != value['decode_ok']:
            raise ValueError('terminal LDPC status differs')
        if receiver_resources(value) != value['resource_counts']:
            raise ValueError('raw operation counts differ')
        for k, v in value['resource_counts'].items():
            resources[k] = resources.get(k, 0)+v
        max_error = None
        if value.get('detector') == 'siso_mmse':
            states = value['siso_states']+[value['terminal_siso_state']]
            if len(states) != 11 or [v['outer_iter'] for v in states[:-1]] != list(range(10)):
                raise ValueError('incomplete SISO state sequence')
            current = np.zeros(len(value['llr']))
            decoders = {r['iteration']: r for r in value['code_feedback_records'] if r['stage'] == 'decoder'}
            detector_records = [r for r in value['code_feedback_records'] if r['stage'] == 'detector_consume']
            errors = []
            for i, state in enumerate(states):
                np.testing.assert_array_equal(state['consumed_prior'], current)
                # Development keeps all raw/message/consumer checks, with an
                # a-priori numerical subset covering pre/post-checkpoint and terminal states.
                cavity = engineering or i in (0, 2, 9, 10)
                error = check_siso_state(state, cavity=cavity)
                if cavity:
                    errors.append(error)
                    cavity_count += 3
                siso_count += 1
                if i < 10:
                    if detector_records[i]['channel_sha256'] != array_hash(state['channel_llr']):
                        raise ValueError('feedback did not consume captured SISO channel')
                    # Check the actually rounded outer cancellation against an
                    # independent product with a float32 accumulation bound.
                    z = observed['y'].astype(np.complex64)-state['H']@observed['pilot'].astype(np.complex64)
                    scale = abs(observed['y'])+abs(state['H'])@abs(observed['pilot'])
                    bound = 8*len(z)*np.finfo(np.float32).eps*np.maximum(scale, np.finfo(float).tiny)
                    if np.any(abs(state['y']-z) > bound):
                        raise ValueError('outer SISO pilot cancellation differs')
                    expected_sigma = float(np.float32(observed['sigma2'])) if i == 0 else float(value['dals'][i-1]['sigma2'])
                    if state['sigma2'] != expected_sigma:
                        raise ValueError('SISO noise state differs from actual CE input')
                    if i < 9:
                        np.testing.assert_array_equal(state['H'], value['dals'][i]['H'])
                    if i in decoders:
                        record = decoders[i]
                        np.testing.assert_array_equal(record['channel_llr'], state['channel_llr'])
                        message = decoder_messages(code, state['channel_llr'], maxiter=50)
                        for actual, expected in [('decoder_input', 'incoming_llr'), ('raw_app', 'raw_app'), ('raw_check_extrinsic', 'raw_check_extrinsic')]:
                            np.testing.assert_array_equal(record[actual], message[expected])
                        current = record['prior_after']
                        nested_decodes += 1
                    elif i < 9:
                        np.testing.assert_array_equal(value['dals'][i]['mu'], state['posterior_mean'].astype(np.complex64))
            terminal = states[-1]
            np.testing.assert_array_equal(terminal['H'], value['H'])
            if terminal['sigma2'] != value['sigma2_terminal']:
                raise ValueError('terminal SISO noise differs')
            np.testing.assert_array_equal(terminal['y'], observed['y']-value['H']@observed['pilot'])
            np.testing.assert_array_equal(value['llr'], np.clip(terminal['channel_llr'], -20, 20))
            max_error = max(errors)
            if engineering and r['arm'] != 'SISO_MEAN':
                repeat[key] = {k: value[k] for k in NUMERIC_FIELDS}
        else:
            _, reference = verified_record(refs[key], Path(c['reference_root']))
            for field in NUMERIC_FIELDS:
                np.testing.assert_array_equal(value[field], reference[field])
        comparisons.append(dict(block=r['block'], snr=r['snr'], arm=r['arm'],
            max_cavity_channel_error=max_error, scores=r['scores']))
        print(json.dumps(dict(record=len(seen), SISO_states=siso_count)), flush=True)
    expected = {(b, s, a) for b in c['blocks'] for s in c['snrs'] for a in configs}
    if seen != expected or summary['calls'] != {'F': len(expected)} or resources != summary['resource_totals']:
        raise ValueError('incomplete full-chain inventory or resource summary')
    if engineering:
        for b in c['blocks']:
            for snr in c['snrs']:
                for k in NUMERIC_FIELDS:
                    np.testing.assert_array_equal(repeat[b, snr, 'SISO_REF47'][k], repeat[b, snr, 'SISO_REF47_REPEAT'][k])
    result = dict(status='PASS', records=len(seen), arrays_audited=arrays, CE_states=ce_count,
        SISO_states=siso_count, cavity_symbol_checks=cavity_count, terminal_LDPC_replays=len(seen),
        cavity_state_indices=list(range(11)) if engineering else [0, 2, 9, 10],
        nested_LDPC_replays=nested_decodes, resources=resources, comparisons=comparisons,
        summary_sha256=sha(summary_path), contract_sha256=sha(contract_path), source_sha256=sha(source_manifest),
        auditor_sha256=sha(__file__), wall_seconds=time.time()-started,
        scope='raw '+stage+' and fixed Gaussian cavity numerical subset; no performance confirmation')
    out = root/'evidence'/(c['tag']+'-raw-audit.json')
    with out.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ('status', 'records', 'SISO_states', 'wall_seconds')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    audit(args.root, args.contract, args.source_manifest)
