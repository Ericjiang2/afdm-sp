"""Raw projection qualification: original CE, prior and decoder consumers."""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
from .bottleneck_pilot import hashes, load_state, observed_at_snr, offline_scores, sha
from .light_gap_replay import CODE_KEYS, verified_record
from .light_gap_receiver_audit import check_ce, check_feedback
from .light_gap_receiver_run import NUMERIC_FIELDS, receiver_resources
from .trans_next_profile_run import compare_projection
from .trans_next_siso_audit import finite_arrays
from .e1_ldpc import build_code, decode_llr, demap_llr
from .supplement_messages import decoder_messages


def audit(root, contract_path, source_manifest):
    started = time.time()
    c = json.loads(contract_path.read_text())
    assert c['schema'] == 'trans-qpsk-profile-v1'
    development = c.get('stage', 'engineering') == 'development'
    path = root/'runs'/c['tag']/'profile/summary.json'
    summary = json.loads(path.read_text())
    exit_record = json.loads((root/'evidence'/(c['tag']+'-exit.json')).read_text())
    assert summary['status'] == 'COMPLETE' and exit_record['exit_code'] == 0 and not exit_record['timed_out']
    assert summary['contract_sha256'] == sha(contract_path) and summary['source_sha256'] == sha(source_manifest)
    assert sha(c['input_summary']) == c['input_summary_sha256']
    inputs = json.loads(Path(c['input_summary']).read_text())
    exo = {e['block']: e for e in inputs['exogenous']}
    refs = {(r['block'], r['snr'], r['arm']): r for r in inputs['records']}
    configs = {a['name']: a for a in c['arms']}
    cache = Path(os.environ['TMPDIR'])/'audit-code'
    cache.mkdir()
    code = build_code(cache_dir=cache)
    env = json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
    assert hashes({k: code[k] for k in CODE_KEYS}) == env['code_identity']
    seen, repeat, rows = set(), {}, []
    arrays = ce_count = nested_count = 0
    resources = {}
    for item in summary['records']:
        key = item['block'], item['snr'], item['arm']
        assert key not in seen
        seen.add(key)
        record, value = verified_record(item, root)
        reservation = json.loads(Path(item['record']).with_name(record['token']+'-reserve.json').read_text())
        assert all(reservation[k] == record[k] for k in ('token', 'block', 'snr', 'arm', 'split', 'kind'))
        config = configs[item['arm']]
        assert record['configuration'] == config
        raw = load_state(exo[item['block']]['state'])
        assert hashes({k: raw[k] for k in exo[item['block']]['hashes']}) == exo[item['block']]['hashes']
        observed = observed_at_snr(raw, item['snr'])
        assert hashes(observed) == record['observed_hashes']
        assert offline_scores(value, raw, value['H']) == record['scores'] == item['scores']
        arrays += finite_arrays(value)
        consumers = {r['iteration']: r for r in value['code_feedback_records'] if r['stage'] == 'CE_consume'}
        assert len(value['dals']) == 9
        for state in value['dals']:
            check_ce(state, observed, raw['params'], consumers[state['outer_iter']], config['receiver'])
            ce_count += 1
        check_feedback(value, config)
        for decoder in value['code_feedback_records']:
            if decoder['stage'] != 'decoder' or 'channel_llr' not in decoder:
                continue
            message = decoder_messages(code, decoder['channel_llr'], maxiter=50)
            for actual, expected in [('decoder_input', 'incoming_llr'), ('raw_app', 'raw_app'),
                                     ('raw_check_extrinsic', 'raw_check_extrinsic')]:
                np.testing.assert_array_equal(decoder[actual], message[expected])
            nested_count += 1
        np.testing.assert_array_equal(value['llr'], demap_llr(value['mu'], value['var'], .5, clip=20.))
        decoded, ok = decode_llr(code, value['llr'], maxiter=50)
        np.testing.assert_array_equal(decoded, value['decoded'])
        assert bool(ok) == value['decode_ok']
        counts = receiver_resources(value)
        assert counts['outer_BP_calls'] == 10 and counts['outer_BP_iterations'] == 120
        assert counts['terminal_BP_calls'] == 1 and counts['terminal_BP_iterations'] == 20
        assert counts['LDPC_calls'] == 2+len(config.get('feedback', {}).get('refresh_checkpoints', []))
        for k, v in counts.items(): resources[k] = resources.get(k, 0)+v
        optimized = item['arm'].startswith('QPSK')
        assert value.get('bp_edge_projection') == ('qpsk_tanh' if optimized else None)
        reference_name = ('MEAN' if item['arm'] == 'QPSK_MEAN' else 'REFRESH47') if optimized else item['arm']
        _, reference = verified_record(refs[item['block'], item['snr'], reference_name], Path(c['reference_root']))
        errors = compare_projection(value, reference, optimized)
        if item['arm'] in ('QPSK_REF47', 'QPSK_REF47_REPEAT'):
            repeat[key] = {k: value[k] for k in NUMERIC_FIELDS}
        rows.append(dict(block=item['block'], snr=item['snr'], arm=item['arm'], scores=item['scores'],
                         hard_exact=True, continuous_relative_errors=errors))
    assert seen == {(b, s, a) for b in c['blocks'] for s in c['snrs'] for a in configs}
    assert len(seen) == c['F_limit'] == (128 if development else 20)
    assert summary['calls'] == {'F': len(seen)}
    if not development:
        for b in c['blocks']:
            for snr in c['snrs']:
                compare_projection(repeat[b, snr, 'QPSK_REF47'], repeat[b, snr, 'QPSK_REF47_REPEAT'], False)
    assert nested_count == (256 if development else 28)
    return dict(status='PASS', records=len(seen), arrays_audited=arrays, CE_states=ce_count,
                terminal_LDPC_replays=len(seen), retained_nested_LDPC_replays=nested_count,
                rows=rows, resources=resources, summary_sha256=sha(path), contract_sha256=sha(contract_path),
                source_sha256=sha(source_manifest), auditor_sha256=sha(Path(__file__)),
                wall_seconds=time.time()-started, scope='raw projection qualification and existing algebra gate; not CONF or COST')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.contract, args.source_manifest)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
