"""Fixed 64-channel development, reusing saved A02 inputs and qualified core."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

import ab_receiver_v1 as receiver
from ab_model_v1 import physical_module
from a03_runner_v1 import operator_check, score
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
from afdm_sp_joint_unrolled.light_gap_replay import LightRun, verified_record
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles


def main(args):
    root = args.root
    contract_path = root/'contracts'/(args.tag+'.json')
    contract = json.loads(contract_path.read_text())
    source = root/contract['source_directory']
    helpers = source/'helpers'
    manifest = source/'source-manifest.json'
    assert contract['schema'] == 'a04-v1' and contract['stage'] == 'development'
    assert sha(manifest) == contract['source_sha256']
    engineering = json.loads((root/contract['engineering_audit']).read_text())
    assert engineering['status'] == 'PASS' and engineering['recipe'] == contract['engineering_recipe']
    admission = json.loads((root/'evidence/a04-development-admission-v1.json').read_text())
    assert admission['status'] == 'ADMIT' and args.tag in admission['jobs']
    files = {source/'afdm_sp_joint_unrolled'/name: digest for name, digest in json.loads(manifest.read_text()).items()}
    files.update({helpers/name: digest for name, digest in contract['helper_hashes'].items()})
    files.update({Path(name): digest for name, digest in contract['bound_inputs'].items()})
    files.update({contract_path: sha(contract_path), manifest: contract['source_sha256'],
                  root/'evidence/a04-development-admission-v1.json': sha(root/'evidence/a04-development-admission-v1.json')})
    guard = BoundFiles(files)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    physical = physical_module(helpers/'physical_transfer_model_v1.py', 1)
    parents = {}
    for tag in ('a02-development-00-31-v2', 'a02-development-32-63-v2'):
        parent_root = root/'runs'/tag
        summary = json.loads((parent_root/'development/summary.json').read_text())
        audit = json.loads((root/'evidence'/(tag+'-audit.json')).read_text())
        assert audit['status'] == 'PASS' and audit['summary_sha256'] == sha(parent_root/'development/summary.json')
        for entry in summary['records']:
            if entry['arm'] == 'INPUT':
                assert entry['block'] not in parents
                parents[entry['block']] = (parent_root, entry)
    assert set(parents) == set(range(64))
    expected = dict(F=52*len(contract['blocks']))
    assert {k: v for k, v in contract['bounds'].items() if k != 'seconds'} == expected
    output = root/'runs'/args.tag
    summary_path = output/'development/summary.json'

    def input_for(block):
        parent_root, entry = parents[block]
        _, raw = verified_record(entry, parent_root)
        physical.validate(raw, 'uwa', block)
        return entry, raw

    if args.mode == 'audit':
        end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads(summary_path.read_text())
        assert summary['status'] == 'COMPLETE' and summary['calls'] == expected
        entries = {(e['block'], e['snr'], e['arm']): e for e in summary['records']}
        assert len(entries) == expected['F']
        rows, closures, bits_seen = [], [], 0
        for block in contract['blocks']:
            parent, raw = input_for(block)
            for snr in (10, 20):
                for pilot in ('p0', 'pZ'):
                    obs = physical.observed(raw, pilot, snr)
                    values, records, errors = {}, {}, {}
                    for arm in receiver.ARMS:
                        entry = entries[block, snr, pilot+'__'+arm]
                        record, value = verified_record(entry, output)
                        assert entry['kind'] == 'F' and entry['split'] == 1
                        assert record['observed_hashes'] == hashes(obs) and record['input_sha256'] == parent['sha256']
                        receiver.check(value)
                        assert record['scores'] == entry['scores'] == score(value, raw)
                        np.testing.assert_array_equal(value['last_bp']['H'], value['H'])
                        actual_y = (torch.tensor(obs['y'], dtype=torch.complex64)
                                    - torch.from_numpy(value['H']) @ torch.tensor(obs['pilot'], dtype=torch.complex64)).numpy()
                        np.testing.assert_array_equal(value['last_bp']['y'], actual_y)
                        closure = operator_check(value)
                        if closure is not None:
                            closures.append(closure)
                        values[arm], records[arm] = value, record
                        errors[arm] = value['bits'] != raw['bits']
                        bits_seen += len(raw['bits'])
                    for arm in receiver.ARMS:
                        entry = entries[block, snr, pilot+'__'+arm]
                        value, record = values[arm], records[arm]
                        by_reference = {}
                        for reference in receiver.CLASSICS:
                            rescued = int(np.count_nonzero(errors[reference] & ~errors[arm]))
                            added = int(np.count_nonzero(~errors[reference] & errors[arm]))
                            by_reference[reference] = dict(rescued=rescued, added=added,
                                                           reference_errors=int(errors[reference].sum()))
                            assert added-rescued == int(errors[arm].sum())-int(errors[reference].sum())
                        rows.append(dict(block=block, snr=snr, pilot=pilot, arm=arm,
                            scores=record['scores'], seconds=record['seconds'], cpu_seconds=record['CPU_seconds'],
                            times=value['times'], representation_times=(value['representation']['times'] if arm in receiver.BASES else None),
                            representation_counts=(value['representation']['counts'] if arm in receiver.BASES else None),
                            selection_condition=(value['representation']['selection']['geometry']['condition'] if arm in receiver.BASES else None),
                            by_reference=by_reference, input_sha256=parent['sha256'], record_sha256=entry['sha256']))
            print(json.dumps(dict(audited_block=block, rows=len(rows))), flush=True)
        guard.verify()
        metrics_path = root/'evidence'/(args.tag+'-metrics.json')
        with metrics_path.open('x') as stream:
            json.dump(dict(rows=rows, summary_sha256=sha(summary_path), source_sha256=sha(manifest)), stream)
        report = dict(status='PASS', records=len(entries), bits_checked=bits_seen,
                      blocks=contract['blocks'], metrics_sha256=sha(metrics_path),
                      max_operator_closure=max(closures), summary_sha256=sha(summary_path),
                      source_sha256=sha(manifest), contract_sha256=sha(contract_path),
                      new_audit_receiver_calls=0, new_audit_detector_calls=0,
                      scope='complete saved-array + physical pairing + operator + counts + scores audit; development only')
        with (root/'evidence'/(args.tag+'-audit.json')).open('x') as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report), flush=True)
        return

    run = LightRun(output, 'development', contract['bounds'], contract['output_bytes'], guard)
    try:
        setup_start = time.perf_counter()
        model, setup = receiver.registered.build(contract['checkpoint_path'], physical.config('uwa'))
        setup_seconds = time.perf_counter()-setup_start
        run.write('environment.json', dict(numpy=np.__version__, torch=torch.__version__, device='cpu', threads=1,
                  coefficient_dtype='complex64', bp_work_dtype='complex128', geometry_dtype='complex128',
                  lstsq_driver='gels', setup=setup, setup_seconds=setup_seconds,
                  timing_scope='same instrumented observed adapter as A03; archival I/O and external scoring outside frame timer'))
        for block in contract['blocks']:
            parent, raw = input_for(block)
            for snr in (10, 20):
                for pilot_index, pilot in enumerate(('p0', 'pZ')):
                    obs = physical.observed(raw, pilot, snr)
                    before = hashes(obs)
                    order = list(receiver.ARMS)
                    np.random.default_rng([20260914, 125851, 1, 0, block, 7, snr, pilot_index]).shuffle(order)
                    for arm in order:
                        run.call('F', dict(block=block, snr=snr, arm=pilot+'__'+arm, split=1),
                            lambda: receiver.receive(model, obs, arm), lambda value: score(value, raw),
                            dict(observed_hashes=before, input_sha256=parent['sha256'], order=order))
                        assert hashes(obs) == before
            print(json.dumps(dict(block=block, calls=run.counts, wall_seconds=time.time()-run.started)), flush=True)
        assert run.counts == expected
        guard.verify()
        run.write('summary.json', dict(status='COMPLETE', calls=run.counts, records=run.records,
                  source_sha256=sha(manifest), contract_sha256=sha(contract_path),
                  setup_seconds=setup_seconds, wall_seconds=time.time()-run.started,
                  scope='fixed 64-channel development, reused A02 observations, not independent confirmation'))
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
