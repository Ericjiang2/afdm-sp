"""Bounded saved-terminal prior controls; no new full receiver or input draws."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time
import numpy as np
import torch
from . import direction_receiver as receiver
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha
from .e1_ldpc import build_code, decode_llr, extract_info
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores
from .supplement_profile import OperatorProfile
from .trans_next_stop_run import same_state
from .trans_next_siso_audit import finite_arrays

FIELDS = ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard', 'decode_ok')


def validate_contract(c):
    development = c.get('stage') == 'development'
    expected_arms = ['LEGACY', 'ZERO', 'RETAIN']+([] if development else ['RETAIN_REPEAT'])
    if (c.get('schema') != 'trans-terminal-prior-v1' or c.get('stage') not in ('engineering', 'development')
            or c.get('device') != 'cpu' or c.get('threads') != 1 or c.get('snrs') != [7, 8]
            or c.get('blocks') != list(range(32 if development else 2))
            or c.get('arms') != expected_arms or c.get('T_limit') != (192 if development else 16)
            or c.get('temperature') != 2. or c.get('reference_arm') != 'REFRESH47'):
        raise ValueError('unregistered terminal-prior contract')
    for name in ('input_summary', 'input_audit'):
        if sha(c[name]) != c[name+'_sha256']:
            raise ValueError('changed terminal-prior input binding')
    audit = json.loads(Path(c['input_audit']).read_text())
    if audit['status'] != 'PASS' or audit['summary_sha256'] != c['input_summary_sha256']:
        raise ValueError('reference input lacks bound raw PASS')
    if development:
        for name in ('engineering_admission', 'engineering_source_manifest'):
            if sha(c[name]) != c[name+'_sha256']:
                raise ValueError('changed terminal engineering admission')
        admission = json.loads(Path(c['engineering_admission']).read_text())
        if admission['status'] != 'PASS' or admission['records'] != 16:
            raise ValueError('terminal engineering must pass before development')
        current = Path(__file__).resolve().parent
        original = json.loads(Path(c['engineering_source_manifest']).read_text())
        if set(original) != {str(p.relative_to(current)) for p in current.rglob('*.py')}:
            raise ValueError('terminal development source inventory changed')
        for name, digest in original.items():
            if sha(current/name) != digest:
                raise ValueError('terminal development source changed: '+name)


def inputs(c, code):
    source = json.loads(Path(c['input_summary']).read_text())
    env = json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
    if source['status'] != 'COMPLETE' or hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
        raise ValueError('changed terminal reference/code identity')
    refs = {(r['block'], r['snr']): r for r in source['records'] if r['arm'] == c['reference_arm']}
    expected = {(b, s) for b in c['blocks'] for s in c['snrs']}
    if set(refs) != expected or len(refs) != sum(r['arm'] == c['reference_arm'] for r in source['records']):
        raise ValueError('reference terminal set incomplete/duplicated')
    return {e['block']: e for e in source['exogenous']}, refs


def terminal_inputs(c, exo, reference, block, snr):
    raw = load_state(exo[block]['state'])
    if hashes({k: raw[k] for k in exo[block]['hashes']}) != exo[block]['hashes']:
        raise ValueError('terminal exogenous identity changed')
    observed = observed_at_snr(raw, snr)
    _, state = verified_record(reference, c['reference_root'])
    checkpoints = [r for r in state['code_feedback_records'] if r['stage'] == 'decoder']
    if [r['iteration'] for r in checkpoints] != [1, 4, 7]:
        raise ValueError('wrong terminal prior source schedule')
    last = checkpoints[-1]
    np.testing.assert_array_equal(last['prior_after'], np.clip(last['raw_check_extrinsic'], -20., 20.))
    H = state['H']; z = observed['y']-H@observed['pilot']
    return raw, observed, state, dict(H=H, z=z, sigma2_terminal=state['sigma2_terminal'],
                                    last_check_prior=last['prior_after'])


def check_value(value, expected, arm):
    for key in expected:
        np.testing.assert_array_equal(value[key], expected[key])
    counts = Counter(row['operator'] for row in value['operator_profile'])
    target = Counter(terminal_BP=1, LDPC=1)
    if arm == 'LEGACY':
        target['LLR'] = 1
    if counts != target or any(row['status'] != 'complete' for row in value['operator_profile']):
        raise ValueError('actual terminal operator count differs')
    if value['resource_counts'] != dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0):
        raise ValueError('terminal resource record differs')
    if arm != 'LEGACY':
        prior = np.zeros_like(expected['last_check_prior']) if arm == 'ZERO' else expected['last_check_prior']
        check_finite_prior_message(value, prior)


def check_finite_prior_message(value, prior):
    """Check actual consumer message and independent circular-QPSK APP moments."""
    message = value['finite_message']
    np.testing.assert_array_equal(message['prior_llr'], prior)
    np.testing.assert_array_equal(message['channel_llr'], value['raw_llr'])
    np.testing.assert_array_equal(value['llr'], np.clip(value['raw_llr'], -20, 20))
    np.testing.assert_array_equal(value['mu'], message['posterior_mean'])
    np.testing.assert_array_equal(value['var'], message['posterior_variance'])
    # Independent circular-QPSK APP projection from the actual delivered LLR.
    app = value['raw_llr']+prior; n = len(app)//2
    mean = .5*np.tanh(app[:n]/2)+.5j*np.tanh(app[n:]/2)
    np.testing.assert_allclose(value['mu'], mean, atol=2e-12, rtol=2e-12)
    np.testing.assert_allclose(value['var'], np.maximum(.5-abs(mean)**2, 0), atol=2e-12, rtol=2e-12)

def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('terminal run identity changed')
    c = json.loads(args.contract.read_text()); validate_contract(c)
    if args.root.name != c['tag']:
        raise ValueError('terminal run tag differs')
    guard = setup_guard(args, c)
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    run = LightRun(args.root, c['stage'], dict(T=c['T_limit'], seconds=c['seconds']), c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        exo, refs = inputs(c, code)
        run.write('environment.json', dict(code_identity=hashes({k: code[k] for k in CODE_KEYS})))
        for b in c['blocks']:
            for snr in c['snrs']:
                raw, observed, state, expected = terminal_inputs(c, exo, refs[b, snr], b, snr)
                before = hashes(expected); saved = {}
                for arm in c['arms']:
                    prior = None if arm == 'LEGACY' else (np.zeros_like(expected['last_check_prior']) if arm == 'ZERO' else expected['last_check_prior'])
                    def terminal():
                        with OperatorProfile(torch.device('cpu')) as profile:
                            value = receiver.terminal_decode(expected['z'], expected['H'], expected['sigma2_terminal'],
                                observed['constellation'], code, audit=True, code_prior=prior, bp_temperature=None)
                        value.update({k: v.copy() if isinstance(v, np.ndarray) else v for k, v in expected.items()})
                        value.update(operator_profile=profile.rows, resource_counts=dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0),
                            scope='saved terminal counterfactual; not full receiver', baseline_eligible=False)
                        return value
                    value, record = run.call('T', dict(block=b, snr=snr, split=exo[b]['split'], arm=arm), terminal,
                        lambda v: decoder_scores(v, raw), dict(reference_record_sha256=refs[b, snr]['sha256'],
                            terminal_input_hashes=before, observed_hashes=hashes(observed), temperature=2.,
                            truth_access='external scoring only'))
                    check_value(value, expected, arm)
                    if hashes(expected) != before:
                        raise ValueError('terminal input mutated')
                    if arm == 'LEGACY':
                        for key in FIELDS: np.testing.assert_array_equal(value[key], state[key])
                    if arm == 'RETAIN_REPEAT': same_state(value, saved['RETAIN'])
                    saved[arm] = value
                    print(json.dumps(dict(block=b, snr=snr, arm=arm, calls=run.counts, scores=record['scores'])), flush=True)
        guard.verify(); validate_contract(c)
        run.write('summary.json', dict(status='COMPLETE', calls=run.counts, records=run.records,
            source_sha256=args.source_sha256, contract_sha256=args.contract_sha256,
            input_summary_sha256=c['input_summary_sha256'], wall_seconds=time.time()-run.started,
            scope='fixed existing inputs; terminal counterfactual, not full receiver/CONF/COST'))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc); raise


def audit(args):
    start = time.time()
    c = json.loads(args.contract.read_text()); validate_contract(c)
    guard = setup_guard(args, c)
    path = args.root/c['stage']/'summary.json';summary = json.loads(path.read_text())
    campaign = Path(c['reference_root'])
    exit_record = json.loads((campaign/'evidence'/(c['tag']+'-exit.json')).read_text())
    if (summary['status'] != 'COMPLETE' or summary['calls'] != {'T': c['T_limit']}
            or summary['source_sha256'] != sha(args.source_manifest) or summary['contract_sha256'] != sha(args.contract)
            or exit_record['exit_code'] != 0 or exit_record['timed_out']):
        raise ValueError('incomplete terminal producer')
    cache = Path(os.environ['TMPDIR'])/'audit-code';cache.mkdir();code = build_code(cache_dir=cache)
    exo, refs = inputs(c, code)
    seen = set(); arrays = 0; rows = []
    for b in c['blocks']:
        for snr in c['snrs']:
            raw, observed, old, expected = terminal_inputs(c, exo, refs[b, snr], b, snr)
            saved = {}
            for entry in (r for r in summary['records'] if r['block'] == b and r['snr'] == snr):
                arm = entry['arm'];key = b, snr, arm
                if key in seen: raise ValueError('duplicate terminal audit record')
                seen.add(key)
                record, value = verified_record(entry, args.root)
                reservation = json.loads(Path(entry['record']).with_name(record['token']+'-reserve.json').read_text())
                if any(reservation[k] != record[k] for k in ('token', 'block', 'snr', 'arm', 'split', 'kind')):
                    raise ValueError('terminal reservation mismatch')
                if (record['reference_record_sha256'] != refs[b, snr]['sha256']
                        or record['terminal_input_hashes'] != hashes(expected)
                        or record['observed_hashes'] != hashes(observed) or record['temperature'] != 2.):
                    raise ValueError('terminal provenance mismatch')
                check_value(value, expected, arm); arrays += finite_arrays(value)
                scores = decoder_scores(value, raw)
                if scores != entry['scores'] or scores != record['scores']:
                    raise ValueError('terminal score mismatch')
                decoded, ok = decode_llr(code, value['llr'], maxiter=50)
                np.testing.assert_array_equal(decoded, value['decoded'])
                np.testing.assert_array_equal(extract_info(code, decoded), value['info_hat'])
                if bool(ok) != value['decode_ok']: raise ValueError('terminal LDPC status differs')
                if arm == 'LEGACY':
                    for field in FIELDS: np.testing.assert_array_equal(value[field], old[field])
                saved[arm] = value
                rows.append(dict(block=b, snr=snr, arm=arm, scores=scores))
            if 'RETAIN_REPEAT' in c['arms']:same_state(saved['RETAIN_REPEAT'], saved['RETAIN'])
    expected_set = {(b, s, a) for b in c['blocks'] for s in c['snrs'] for a in c['arms']}
    if seen != expected_set or len(summary['records']) != len(expected_set):
        raise ValueError('terminal audit coverage differs')
    guard.verify()
    return dict(status='PASS', records=len(seen), arrays_audited=arrays, LDPC_replays=len(seen), rows=rows,
        summary_sha256=sha(path), contract_sha256=sha(args.contract), source_sha256=sha(args.source_manifest),
        auditor_sha256=sha(Path(__file__)), wall_seconds=time.time()-start,
        scope='terminal raw/input/prior/operator/decoder verification; no new F or BP/T calls')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):p.add_argument('--'+name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):p.add_argument('--'+name, required=True)
    p.add_argument('--audit-output', type=Path)
    args = p.parse_args()
    if args.audit_output:
        result = audit(args)
        with args.audit_output.open('x') as f:json.dump(result, f, indent=2, allow_nan=False)
        print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
    else:execute(args)
