"""Re-read stopping prefixes, actual CE/SISO states, and real LDPC messages."""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
from .bottleneck_pilot import hashes, load_state, observed_at_snr, offline_scores, sha
from .budgeted_support_diagnostics import array_hash
from .light_gap_replay import CODE_KEYS, verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS
from .light_gap_receiver_audit import check_ce, check_feedback
from .trans_next_siso_audit import finite_arrays, check_siso_state
from .trans_next_stop_run import check_calls, check_prefix, same_state, same_receiver_state, load_recovery, retained_terminal_records, retained_reference, check_retained_full
from .e1_ldpc import build_code, decode_llr, demap_llr, extract_info
from .supplement_messages import decoder_messages
from .trans_next_terminal_prior import check_finite_prior_message
from .trans_next_profile_run import compare_projection
from .trans_next_stop_run import projection_reference_records


def audit(root, contract_path, source_manifest):
    started = time.time()
    c = json.loads(contract_path.read_text())
    if c['schema'] not in ('trans-stop-engineering-v1', 'trans-retained-stop-v1'):
        raise ValueError('unknown stop audit contract')
    stage = c.get('stage', 'engineering')
    if stage not in ('engineering', 'development'):
        raise ValueError('unknown stop audit stage')
    development = stage == 'development'
    retained = c['schema'] == 'trans-retained-stop-v1'
    projection = c.get('bp_edge_projection')
    if projection not in (None, 'qpsk_tanh') or (projection is not None and (not retained or development or c.get('outer_bp_graph') != 'integer')):
        raise ValueError('unregistered projection audit boundary')
    projection_refs = projection_reference_records(c)
    terminals = retained_terminal_records(c)
    path = root/'runs'/c['tag']/stage/'summary.json'
    summary = json.loads(path.read_text())
    exit_record = json.loads((root/'evidence'/(c['tag']+'-exit.json')).read_text())
    if (summary['status'] != 'COMPLETE' or exit_record['exit_code'] != 0 or exit_record['timed_out']
            or summary['contract_sha256'] != sha(contract_path) or summary['source_sha256'] != sha(source_manifest)):
        raise ValueError('incomplete or mismatched producer evidence')
    for key in ('input_summary', 'reference_summary'):
        if sha(c[key]) != c[key+'_sha256']:
            raise ValueError('changed bound input')
    inputs = json.loads(Path(c['input_summary']).read_text())
    exo = {e['block']: e for e in inputs['exogenous']}
    old = json.loads(Path(c['reference_summary']).read_text())
    old_refs = {(r['block'], r['snr'], r['arm']): r for r in old['records']}
    if development:
        old_refs.update({(r['block'], r['snr'], r['arm']): r for r in inputs['records']})
    refs = {(r['block'], r['snr'], r['arm']): r for r in summary['records']}
    configs = {a['name']: a for a in c['arms']}
    recovery = load_recovery(c)
    cache = Path(os.environ['TMPDIR'])/'audit-code'
    cache.mkdir()
    code = build_code(cache_dir=cache)
    env = json.loads(path.with_name('environment.json').read_text())
    if hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
        raise ValueError('changed audit LDPC')
    seen, rows, resources = set(), [], {}
    arrays = ce_count = siso_count = nested_count = terminal_count = stops = valid_wrong = 0
    for item in summary['records']:
        key = item['block'], item['snr'], item['arm']
        if key in seen:
            raise ValueError('duplicate engineering item')
        seen.add(key)
        record, value = verified_record(item, root)
        reservation = json.loads(Path(item['record']).with_name(record['token']+'-reserve.json').read_text())
        if any(reservation[k] != record[k] for k in ('token', 'block', 'snr', 'arm', 'split', 'kind')):
            raise ValueError('reservation identity differs')
        config = configs[item['arm']]
        if record['configuration'] != config:
            raise ValueError('changed receiver configuration')
        expected_graph = c.get('outer_bp_graph') if retained and 'RETAIN' in item['arm'] else None
        if value.get('outer_bp_graph') != expected_graph:
            raise ValueError('integer graph execution differs from the bound arm')
        expected_projection = projection if retained and 'RETAIN' in item['arm'] else None
        if value.get('bp_edge_projection') != expected_projection:
            raise ValueError('projection execution differs from the bound arm')
        raw = load_state(exo[item['block']]['state'])
        if hashes({k: raw[k] for k in exo[item['block']]['hashes']}) != exo[item['block']]['hashes']:
            raise ValueError('changed exogenous input')
        observed = observed_at_snr(raw, item['snr'])
        if (hashes(observed) != record['observed_hashes']
                or offline_scores(value, raw, value['H']) != record['scores'] or record['scores'] != item['scores']):
            raise ValueError('observation or raw score mismatch')
        arrays += finite_arrays(value)
        detail = check_calls(value)
        if detail['resources'] != value['resource_counts']:
            raise ValueError('saved resource counts differ')
        for k, v in detail['resources'].items():
            resources[k] = resources.get(k, 0)+v
        consumers = {r['iteration']: r for r in value['code_feedback_records'] if r['stage'] == 'CE_consume'}
        for state in value['dals']:
            check_ce(state, observed, raw['params'], consumers[state['outer_iter']], config['receiver'])
            ce_count += 1
        check_feedback(value, config)
        terminal = value.get('terminal_executed', True)
        decoders = [r for r in value['code_feedback_records'] if r['stage'] == 'decoder']
        for decoder in decoders:
            message = decoder_messages(code, decoder['channel_llr'], maxiter=50)
            for actual, expected in [('decoder_input', 'incoming_llr'), ('raw_app', 'raw_app'),
                                     ('raw_check_extrinsic', 'raw_check_extrinsic')]:
                np.testing.assert_array_equal(decoder[actual], message[expected])
            if 'decode_ok' in decoder and (decoder['decode_ok'] != bool(message['decode_ok'])
                    or decoder['unsatisfied_checks'] != message['syndrome_trace'][-1]['unsatisfied_checks']):
                raise ValueError('recorded stop decision differs from real decoder')
            nested_count += 1
        if terminal:
            decoded, ok = decode_llr(code, value['llr'], maxiter=50)
            np.testing.assert_array_equal(decoded, value['decoded'])
            if bool(ok) != value['decode_ok']:
                raise ValueError('terminal decoder status differs')
            terminal_count += 1
        else:
            stops += 1
            stop = value['checkpoint_stop']
            np.testing.assert_array_equal(value['decoded'], (decoders[-1]['raw_app'] < 0).astype(np.uint8))
            np.testing.assert_array_equal((code['H'].astype(np.int32)@value['decoded'].astype(np.int32)) % 2, 0)
            if (array_hash(value['mu']) != decoders[-1]['ce_mean_sha256']
                    or array_hash(value['var']) != decoders[-1]['ce_variance_sha256']):
                raise ValueError('stopped moments differ from actual delivered moments')
            same_state(stop['raw_app'], decoders[-1]['raw_app'])
            valid_wrong += int(np.any(value['decoded'] != raw['coded']))
        np.testing.assert_array_equal(value['info_hat'], extract_info(code, value['decoded']))
        if value.get('detector') == 'siso_mmse':
            states = value['siso_states']+([value['terminal_siso_state']] if terminal else [])
            for state in states:
                check_siso_state(state)
                siso_count += 1
            detector_records = [r for r in value['code_feedback_records'] if r['stage'] == 'detector_consume']
            for state, consumed in zip(value['siso_states'], detector_records):
                if consumed['channel_sha256'] != array_hash(state['channel_llr']):
                    raise ValueError('decoder did not consume actual SISO likelihood')
                if consumed['prior_sha256'] != array_hash(state['consumed_prior']):
                    raise ValueError('SISO consumed another prior')
            if terminal:
                state = value['terminal_siso_state']
                np.testing.assert_array_equal(state['H'], value['H'])
                np.testing.assert_array_equal(state['y'], observed['y']-value['H']@observed['pilot'])
                if state['sigma2'] != value['sigma2_terminal']:
                    raise ValueError('terminal SISO noise differs')
                np.testing.assert_array_equal(value['llr'], np.clip(state['channel_llr'], -20, 20))
        elif terminal:
            if config['receiver'].get('terminal_check_prior') == 'retain':
                if not value['terminal_check_prior_consumed']:
                    raise ValueError('missing retained terminal prior consumption')
                check_finite_prior_message(value, decoders[-1]['prior_after'])
            else:
                np.testing.assert_array_equal(value['llr'], demap_llr(value['mu'], value['var'], .5, clip=20.))
        if retained and 'RETAIN' in item['arm'] and value['terminal_check_prior_consumed'] != terminal:
            raise ValueError('terminal prior consumption does not match actual execution')
        family = 'SISO' if item['arm'].startswith('SISO') else 'BP'
        if 'STOP' in item['arm']:
            old_name = 'SISO_REF47' if family == 'SISO' else 'REFRESH47'
            base_name = 'BP_RETAIN' if retained else family+'_REF47'
            base_entry = old_refs[item['block'], item['snr'], old_name] if development else refs[item['block'], item['snr'], base_name]
            _, base = verified_record(base_entry, root)
            if retained and development:
                base = retained_reference(c, base, terminals, item['block'], item['snr'])
            detail.update(check_prefix(value, base))
            if item['arm'].endswith('_REPEAT'):
                repeat_name = 'BP_RETAIN_STOP' if retained else family+'_STOP'
                _, repeated = verified_record(refs[item['block'], item['snr'], repeat_name], root)
                same_receiver_state(value, repeated)
        else:
            old_name = 'SISO_REF47' if family == 'SISO' else 'REFRESH47'
            _, base = verified_record(old_refs[item['block'], item['snr'], old_name], Path(c['reference_root']))
            if retained and 'RETAIN' in item['arm']:
                base = retained_reference(c, base, terminals, item['block'], item['snr'])
                detail.update(check_retained_full(value, base, projection=projection is not None))
            else:
                for field in NUMERIC_FIELDS:
                    np.testing.assert_array_equal(value[field], base[field])
        if projection is not None:
            _, projected_base = verified_record(projection_refs[key], root)
            detail['composition_reference_errors'] = compare_projection(value, projected_base, 'RETAIN' in item['arm'])
        rows.append(dict(block=item['block'], snr=item['snr'], arm=item['arm'], scores=item['scores'], **detail))
        print(json.dumps(dict(records=len(seen), CE=ce_count, SISO=siso_count)), flush=True)
    expected = {(b, s, a) for b in c['blocks'] for s in c['snrs'] for a in configs}
    if projection_reference_records(c) != projection_refs:
        raise ValueError('projection reference changed during audit')
    if (seen != expected or summary['calls'] != {'F': len(seen)-len(recovery)}
            or summary.get('recovered_calls', 0) != len(recovery) or resources != summary['resource_totals']):
        raise ValueError('incomplete stop engineering inventory')
    return dict(status='PASS', records=len(seen), new_F=len(seen)-len(recovery), recovered_F=len(recovery), arrays_audited=arrays, CE_states=ce_count,
        SISO_states=siso_count, cavity_symbol_checks=3*siso_count, nested_LDPC_replays=nested_count,
        terminal_LDPC_replays=terminal_count, actual_stops=stops, valid_but_wrong_stops=valid_wrong,
        resources=resources, rows=rows, summary_sha256=sha(path), contract_sha256=sha(contract_path),
        source_sha256=sha(source_manifest), auditor_sha256=sha(__file__), wall_seconds=time.time()-started,
        scope=stage+' raw prefix/decoder/CE/SISO qualification; not CONF, COST or proof of no undetected errors')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.contract, args.source_manifest)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
