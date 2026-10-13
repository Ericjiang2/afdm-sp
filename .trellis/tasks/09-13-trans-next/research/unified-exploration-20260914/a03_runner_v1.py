"""Bounded full receiver engineering and independent saved-array qualification."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

import ab_receiver_v1 as receiver
from ab_model_v1 import physical_module
from a02_runner_v1 import check_equal
from afdm_sp_joint_unrolled.bandlimited_basis import BasisGeometry
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
from afdm_sp_joint_unrolled.light_gap_replay import LightRun, verified_record
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles


def without_times(value):
    if isinstance(value, dict):
        return {k: without_times(v) for k, v in value.items() if k != 'times'}
    if isinstance(value, list):
        return [without_times(v) for v in value]
    return value


def default_replay(value, old):
    for key in ('H', 'x_soft', 'sigma2_final', 'gains', 'delays', 'dopplers', 'bits'):
        np.testing.assert_array_equal(value[key], old[key], err_msg='old default ' + key)
    for key in ('support_trace', 'bp_schedule', 'nomination', 'cluster_extension', 'soft_decisions'):
        check_equal(value[key], old[key])
    for key, expected in old['counts'].items():
        assert value['counts'][key] == expected, key


def score(value, raw):
    norm = lambda x: float(np.vdot(x, x).real)
    schedule = value['bp_schedule']['calls']
    return dict(errors=int(np.count_nonzero(value['bits'] != raw['bits'])), bits=len(raw['bits']),
                channel_nmse=norm(value['H'] - raw['H']) / norm(raw['H']),
                active_coefficients=len(value['gains']),
                edges=[item['edges'] for item in schedule],
                bp_iterations=sum(item['executed_iterations'] for item in schedule),
                counts=value['counts'])


def operator_check(value):
    if value['arm'] not in receiver.BASES:
        return None
    saved = value['representation']
    public = saved['public']
    geometry = BasisGeometry(saved['basis'], c1=public['c1'], c2=public['c2'],
                             delay_cap=public['delay_cap'], prefix_length=public['prefix_length'])
    delays = saved['selection']['delays']
    design = geometry.sensing(saved['last_symbols'], delays)
    channel = geometry.channel(delays, saved['last_coefficients'])
    left = channel @ saved['last_symbols']
    right = design @ saved['last_coefficients']
    closure = float(np.linalg.norm(left-right) / max(np.linalg.norm(left), 1e-30))
    assert closure <= 1e-10
    np.testing.assert_array_equal(design.astype(np.complex64), saved['last_design'])
    np.testing.assert_array_equal(channel.astype(np.complex64), saved['last_channel'])
    initial = geometry.sensing(saved['initial_pilot'], delays).astype(np.complex64)
    np.testing.assert_array_equal(initial, saved['initial_design'])
    assert np.array_equal(saved['initial_fit']['coefficients'].dtype, np.dtype('complex64'))
    return closure


def main(args):
    root = args.root
    contract_path = root / 'contracts' / (args.tag + '.json')
    contract = json.loads(contract_path.read_text())
    source = root / contract['source_directory']
    helpers = source / 'helpers'
    manifest = source / 'source-manifest.json'
    assert contract['schema'] == 'a03-v1' and contract['stage'] == 'engineering'
    assert sha(manifest) == contract['source_sha256']
    files = {source/'afdm_sp_joint_unrolled'/name: digest for name, digest in json.loads(manifest.read_text()).items()}
    files.update({helpers/name: digest for name, digest in contract['helper_hashes'].items()})
    files.update({Path(name): digest for name, digest in contract['bound_inputs'].items()})
    files.update({contract_path: sha(contract_path), manifest: contract['source_sha256'],
                  root/'contracts/ab-contract-v1.json': contract['ab_contract_sha256'],
                  root/'contracts/a03-protocol-v1.md': contract['protocol_sha256']})
    guard = BoundFiles(files)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    physical = physical_module(helpers/'physical_transfer_model_v1.py', 0)
    old_root = root.parent/'outputs_trans_next_20260913'
    old_summary = json.loads((old_root/'runs/physical-transfer-engineering-v1/engineering/summary.json').read_text())
    old_entries = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in old_summary['records']}
    new_root = root/'runs/a02-engineering-v2'
    new_summary = json.loads((new_root/'engineering/summary.json').read_text())
    new_entries = {e['block']: e for e in new_summary['records'] if e['arm'] == 'INPUT'}
    assert set(new_entries) == {0, 1}
    expected = dict(F=125, T=13)
    assert {k: v for k, v in contract['bounds'].items() if k != 'seconds'} == expected
    output = root/'runs'/args.tag
    summary_path = output/'engineering/summary.json'

    def input_for(block, legacy):
        entry = old_entries['A', block, 10, 'uwa_INPUT'] if legacy else new_entries[block]
        _, raw = verified_record(entry, old_root if legacy else new_root)
        return entry, raw

    if args.mode == 'audit':
        end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads(summary_path.read_text())
        assert summary['status'] == 'COMPLETE' and summary['calls'] == expected
        entries = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in summary['records']}
        assert len(entries) == 138
        closure, checked, defaults, repeats, terminals = [], 0, 0, 0, 0
        for entry in summary['records']:
            record, value = verified_record(entry, output)
            pilot, arm, *suffix = entry['arm'].split('__')
            legacy = suffix == ['LEGACY']
            parent, raw = input_for(entry['block'], legacy)
            obs = physical.observed(raw, pilot, entry['snr'])
            assert record['observed_hashes'] == hashes(obs) and record['input_sha256'] == parent['sha256']
            if entry['kind'] == 'T':
                reference = entries['F', entry['block'], entry['snr'], pilot+'__'+arm]
                _, full = verified_record(reference, output)
                assert record['full_record_sha256'] == reference['sha256'] and value['actual_bp_calls'] == 1
                for key, array in value['outputs'].items():
                    np.testing.assert_array_equal(array, full['last_bp'][key])
                terminals += 1
                continue
            receiver.check(value)
            assert record['scores'] == entry['scores'] == score(value, raw)
            np.testing.assert_array_equal(value['last_bp']['H'], value['H'])
            actual_y = obs['y'].astype(np.complex64) - value['H'] @ obs['pilot'].astype(np.complex64)
            np.testing.assert_allclose(value['last_bp']['y'], actual_y, atol=2e-5, rtol=2e-5)
            check = operator_check(value)
            if check is not None:
                closure.append(check)
            if legacy:
                old = old_entries['F', entry['block'], entry['snr'], pilot+'__'+arm]
                _, prior = verified_record(old, old_root)
                default_replay(value, prior)
                defaults += 1
            if suffix == ['REPEAT']:
                original = entries['F', entry['block'], entry['snr'], pilot+'__'+arm]
                _, earlier = verified_record(original, output)
                check_equal(without_times(value), without_times(earlier))
                repeats += 1
            checked += 1
        assert (checked, defaults, repeats, terminals) == (125, 8, 13, 13)
        guard.verify()
        report = dict(status='PASS', records=len(entries), full_records=checked,
                      exact_default_replays=defaults, matched_repeat_pairs=repeats,
                      saved_exact_last_detector_replays=terminals, max_operator_closure=max(closure),
                      new_audit_receiver_calls=0, new_audit_detector_calls=0,
                      summary_sha256=sha(summary_path), contract_sha256=sha(contract_path),
                      source_sha256=sha(manifest), recipe=contract['recipe'],
                      scope='saved raw + operator audit, no new receiver performance experiment')
        with (root/'evidence'/(args.tag+'-audit.json')).open('x') as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report), flush=True)
        return

    run = LightRun(output, 'engineering', contract['bounds'], contract['output_bytes'], guard)
    try:
        setup_start = time.perf_counter()
        model, setup = receiver.registered.build(contract['checkpoint_path'], physical.config('uwa'))
        setup_seconds = time.perf_counter()-setup_start
        run.write('environment.json', dict(numpy=np.__version__, torch=torch.__version__, device='cpu', threads=1,
                  coefficient_dtype='complex64', bp_work_dtype='complex128', geometry_dtype='complex128',
                  lstsq_driver='gels', setup=setup, setup_seconds=setup_seconds,
                  timing_scope='observed adapter includes public basis, dictionary, CE, graph/BP and validation; nested component timers'))
        for snr in (10, 20):
            for pilot in ('p0', 'pZ'):
                parent, raw = input_for(0, True)
                obs = physical.observed(raw, pilot, snr)
                for arm in ('OMP_BASE', 'F2P_RESID'):
                    old = old_entries['F', 0, snr, pilot+'__'+arm]
                    _, prior = verified_record(old, old_root)
                    value, _ = run.call('F', dict(block=0, snr=snr, arm=pilot+'__'+arm+'__LEGACY', split=-1),
                        lambda: receiver.receive(model, obs, arm), lambda v: score(v, raw),
                        dict(observed_hashes=hashes(obs), input_sha256=parent['sha256'], reference_record_sha256=old['sha256']))
                    default_replay(value, prior)
                print(json.dumps(dict(stage='default', pilot=pilot, snr=snr, calls=run.counts)), flush=True)
        for block in (0, 1):
            parent, raw = input_for(block, False)
            physical.validate(raw, 'uwa', block)
            for snr in (10, 20):
                for pilot_index, pilot in enumerate(('p0', 'pZ')):
                    obs = physical.observed(raw, pilot, snr)
                    before = hashes(obs)
                    order = list(receiver.ARMS)
                    np.random.default_rng([20260914, 125851, 0, 0, block, 7, snr, pilot_index]).shuffle(order)
                    for arm in order:
                        identity = dict(block=block, snr=snr, arm=pilot+'__'+arm, split=0)
                        provenance = dict(observed_hashes=before, input_sha256=parent['sha256'], order=order)
                        value, _ = run.call('F', identity, lambda: receiver.receive(model, obs, arm),
                                            lambda v: score(v, raw), provenance)
                        assert hashes(obs) == before
                        full_entry = run.records[-1]
                        if block == 0 and pilot == 'p0' and snr == 20:
                            repeated, _ = run.call('F', dict(identity, arm=identity['arm']+'__REPEAT'),
                                lambda: receiver.receive(model, obs, arm), lambda v: score(v, raw), provenance)
                            check_equal(without_times(value), without_times(repeated))
                            run.call('T', dict(identity, arm=identity['arm']+'__LAST_BP'),
                                lambda: receiver.replay_last_detector(value), lambda _: {},
                                dict(provenance, full_record_sha256=full_entry['sha256']))
                    print(json.dumps(dict(block=block, pilot=pilot, snr=snr, calls=run.counts,
                                           wall_seconds=time.time()-run.started)), flush=True)
        assert run.counts == expected
        guard.verify()
        run.write('summary.json', dict(status='COMPLETE', calls=run.counts, records=run.records,
                  source_sha256=sha(manifest), contract_sha256=sha(contract_path), recipe=contract['recipe'],
                  setup_seconds=setup_seconds, wall_seconds=time.time()-run.started))
        print(json.dumps(dict(status='COMPLETE', calls=run.counts)), flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--mode', choices=('run', 'audit'), default='run')
    main(parser.parse_args())
