"""Bounded operator profiling of unchanged, previously audited CPU references."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from . import classical_joint_unrolled as joint
from . import supplement_feedback as feedback
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha, offline_scores
from .budgeted_support_eval import build_receiver
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .supplement_profile import OperatorProfile
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS, run_arm


def compare_projection(value, reference, optimized):
    errors = {}
    for field in NUMERIC_FIELDS:
        if value[field] is None or reference[field] is None:
            if value[field] is not reference[field]:
                raise AssertionError('optional numeric field differs: '+field)
            continue
        actual, expected = np.asarray(value[field]), np.asarray(reference[field])
        if not optimized or field in ('support', 'x_hard', 'decoded', 'info_hat', 'decode_ok'):
            np.testing.assert_array_equal(actual, expected)
        else:
            np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-6)
            errors[field] = float(np.linalg.norm(actual-expected)/max(np.linalg.norm(expected), 1e-12))
    return errors


def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('profile source or contract changed')
    c = json.loads(args.contract.read_text())
    projection = c['schema'] == 'trans-qpsk-profile-v1'
    development = c.get('stage', 'engineering') == 'development'
    if c.get('stage', 'engineering') not in ('engineering', 'development') or (development and not projection):
        raise ValueError('unknown profile stage')
    names = (['QPSK_MEAN', 'QPSK_REF47'] if development else
             ['MEAN', 'REFRESH47'] + (['QPSK_MEAN', 'QPSK_REF47', 'QPSK_REF47_REPEAT'] if projection else []))
    blocks = list(range(32)) if development else [0, 1]
    if (c['schema'] not in ('trans-structure-profile-v1', 'trans-qpsk-profile-v1') or c['device'] != 'cpu' or c['threads'] != 1
            or c['blocks'] != blocks or c['snrs'] != [7, 8] or c['F_limit'] != 2*len(blocks)*len(names)
            or args.root.name != c['tag'] or sha(c['input_summary']) != c['input_summary_sha256']
            or sha(c['checkpoint_path']) != c['checkpoint_sha256']
            or [a['name'] for a in c['arms']] != names):
        raise ValueError('unregistered profile boundary')
    if development:
        if sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('engineering audit changed')
        admission = json.loads(Path(c['engineering_admission']).read_text())
        if (admission['status'] != 'PASS' or admission['records'] != 20 or admission['CE_states'] != 180
                or admission['source_sha256'] != c['engineering_source_sha256']):
            raise ValueError('incomplete projection engineering audit')
        if sha(c['engineering_source_manifest']) != c['engineering_source_sha256']:
            raise ValueError('qualified engineering source changed')
        for name, digest in json.loads(Path(c['engineering_source_manifest']).read_text()).items():
            if name != 'trans_next_profile_run.py' and sha(Path(__file__).parent/name) != digest:
                raise ValueError('changed qualified projection algorithm: '+name)
    if projection:
        for arm in c['arms']:
            expected = dict(bp_edge_projection='qpsk_tanh') if arm['name'].startswith('QPSK') else {}
            refresh = [4, 7] if arm['name'] in ('REFRESH47', 'QPSK_REF47', 'QPSK_REF47_REPEAT') else []
            if arm['receiver'] != expected or arm.get('feedback', {}).get('refresh_checkpoints', []) != refresh:
                raise ValueError('projection/reference configuration changed')
    guard = setup_guard(args, c)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(args.root, 'profile', dict(F=c['F_limit'], seconds=c['seconds']), c['output_bytes'], guard)
    try:
        cache = run.out / 'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        inputs = json.loads(Path(c['input_summary']).read_text())
        env = json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
        if inputs['status'] != 'COMPLETE' or hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
            raise ValueError('incomplete input or different code')
        exo = {e['block']: e for e in inputs['exogenous']}
        refs = {(r['block'], r['snr'], r['arm']): r for r in inputs['records']}
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        checks = []
        for block in c['blocks']:
            raw = load_state(exo[block]['state'])
            if hashes({k: raw[k] for k in exo[block]['hashes']}) != exo[block]['hashes']:
                raise ValueError('profile input changed')
            for snr in c['snrs']:
                observed = observed_at_snr(raw, snr)
                before = hashes(observed)
                arms = c['arms'] if (block + snr) % 2 else list(reversed(c['arms']))
                repeat = {}
                for arm in arms:
                    def full():
                        with OperatorProfile(torch.device('cpu')) as profile:
                            profile.wrap(joint, 'reconstruct_H_torch', 'dense_H_reconstruction')
                            profile.wrap(joint, 'build_A_for_DALS_torch', 'CE_design')
                            profile.wrap(feedback, 'decoder_messages', 'feedback_LDPC')
                            value = run_arm(receiver, code, observed, arm)
                        if any(r['status'] != 'complete' for r in profile.rows):
                            raise ValueError('incomplete profiled operator')
                        value['operator_profile'] = profile.rows
                        return value
                    identity = dict(block=block, snr=snr, split=exo[block]['split'], arm=arm['name'])
                    value, record = run.call('F', identity, full, lambda v: offline_scores(v, raw, v['H']),
                        dict(observed_hashes=before, configuration=arm, input_summary_sha256=c['input_summary_sha256'],
                            scope=c.get('scope', 'instrumented unchanged receiver; nested times not additive')))
                    if hashes(observed) != before:
                        raise ValueError('profile mutated input')
                    optimized = arm['name'].startswith('QPSK')
                    reference_name = ('MEAN' if arm['name'] == 'QPSK_MEAN' else 'REFRESH47') if optimized else arm['name']
                    reference_record, reference = verified_record(refs[block, snr, reference_name], Path(c['reference_root']))
                    errors = compare_projection(value, reference, optimized)
                    if not optimized and record['scores'] != reference_record['scores']:
                        raise ValueError('profile score differs')
                    _, saved = verified_record(run.records[-1], args.root)
                    for field in NUMERIC_FIELDS:
                        np.testing.assert_array_equal(saved[field], value[field])
                    if offline_scores(saved, raw, saved['H']) != record['scores']:
                        raise ValueError('saved projection scores differ')
                    if saved['operator_profile'] != value['operator_profile']:
                        raise ValueError('saved operator timings differ')
                    counts = {}
                    for row in value['operator_profile']:
                        counts[row['operator']] = counts.get(row['operator'], 0) + 1
                    expected = dict(outer_BP=10, terminal_BP=1, dense_H_reconstruction=10,
                        CE_design=9, DA_LS_feedback_gain=9, feedback_LDPC=1 if reference_name=='MEAN' else 3, LDPC=1)
                    if any(counts.get(k) != v for k, v in expected.items()):
                        raise ValueError('profile call counts differ')
                    collisions = []
                    for state in value['dals']:
                        shifts = (5 * state['support_delays'] + state['support_dopplers']) % 1024
                        collisions.append(len(shifts) - len(np.unique(shifts)))
                    if arm['name'] in ('QPSK_REF47', 'QPSK_REF47_REPEAT'):
                        repeat[arm['name']] = {field: saved[field] for field in NUMERIC_FIELDS}
                    checks.append(dict(**identity, numeric_fields_exact=not optimized, hard_fields_exact=True,
                        continuous_relative_errors=errors, raw_readback_exact=True,
                        operator_counts=counts, displacement_collisions=collisions,
                        seconds=record['seconds'], operators=value['operator_profile']))
                    print(json.dumps(dict(**identity, calls=run.counts)), flush=True)
                if projection and not development:
                    compare_projection(repeat['QPSK_REF47'], repeat['QPSK_REF47_REPEAT'], False)
        guard.verify()
        if sha(c['input_summary']) != c['input_summary_sha256'] or sha(c['checkpoint_path']) != c['checkpoint_sha256']:
            raise ValueError('profile input identity changed')
        if development and sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('engineering admission changed during development')
        run.write('summary.json', dict(status='COMPLETE', records=run.records, checks=checks, calls=run.counts,
            contract_sha256=args.contract_sha256, source_sha256=args.source_sha256,
            input_summary_sha256=c['input_summary_sha256'], wall_seconds=time.time()-run.started,
            projection_repeat_exact=True if projection and not development else None,
            scope=c.get('scope', 'bounded operator diagnosis and unchanged replay, not formal COST or optimized implementation')))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--' + name, required=True)
    execute(parser.parse_args())
