"""Offline geometry of captured G1 CE matrices; no new receiver or fitting."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np


def geometry(matrix):
    a = np.asarray(matrix, dtype=np.complex128)
    assert a.ndim == 2 and 0 < a.shape[1] <= a.shape[0] and np.isfinite(a).all()
    norms = np.linalg.norm(a, axis=0)
    assert np.all(norms > 0)
    normalized = a / norms
    gram = normalized.conj().T @ normalized
    eigenvalues = np.linalg.eigvalsh(gram)
    singular = np.linalg.svd(normalized, compute_uv=False)
    np.testing.assert_allclose(eigenvalues, singular[::-1]**2, atol=2e-12, rtol=2e-12)
    rank_threshold = np.finfo(float).eps * max(a.shape) * singular[0]
    rank = int(np.count_nonzero(singular > rank_threshold))
    full_rank = rank == a.shape[1] and eigenvalues[0] > 0
    correlations = abs(gram).copy(); np.fill_diagonal(correlations, 0)
    stats = dict(columns=a.shape[1], rank=rank, full_rank=bool(full_rank),
        max_coherence=float(correlations.max()), lambda_min=float(eigenvalues[0]),
        lambda_max=float(eigenvalues[-1]),
        gram_condition=float(eigenvalues[-1]/eigenvalues[0]) if full_rank else None,
        white_ls_geometry_factor=float(np.mean(1/eigenvalues)) if full_rank else None,
        mean_column_energy=float(np.mean(norms**2)),
        column_norm_ratio=float(norms.max()/norms.min()),
        gram_svd_max_error=float(np.max(abs(eigenvalues-singular[::-1]**2))))
    return dict(gram=gram, eigenvalues=eigenvalues, column_norms=norms, metrics=stats)


def main(args):
    root = args.root; source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch, build_A_for_DALS_torch
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays

    contract = root/'contracts'/(args.tag+'.json'); c = json.loads(contract.read_text())
    manifest = source/'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == args.tag == 'g1-active-observability-v1'
    assert c['blocks'] == list(range(32)) and c['snrs'] == [7, 8]
    assert c['bounds'] == dict(A=32, seconds=300) and c['device'] == 'cpu' and c['threads'] == 1
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for sp, ap in c['audited_inputs'].items():
        a = json.loads((root/ap).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root/sp)
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root/'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    index = {(e['kind'], e['block'], e['snr'], e['arm']):e for e in upstream['records']}
    assert len(index) == len(upstream['records']) == 288
    out = root/'runs'/args.tag/'analysis'

    def calculate(block):
        pe = index['A', block, 7, 'G1_PROPAGATION']; _, physical = verified_record(pe, root)
        raw = physical['raw']; params = raw['params']; c1, c2 = params['c1'], params['c2']
        assert len(raw['pilot']) == 1024 and 2*1024*c1 == 5
        pt = torch.tensor(raw['pilot'], dtype=torch.complex64)
        phi = construct_sensing_matrix_torch(1024, pt, c1, c2, 102, 2, cdtype=torch.complex64).numpy()
        values = {}; rows = []
        for snr in c['snrs']:
            ref = index['F', block, snr, 'G1_FULL']; _, state = verified_record(ref, root)
            assert state['initial_estimator']['truth_access'] == 'none'
            init_ids = np.asarray(state['initial_estimator']['support'], dtype=np.int64)
            assert len(init_ids) == 24 and len(set(init_ids.tolist())) == 24
            assert set(init_ids.tolist()) == set(state['support'])
            assert [d['outer_iter'] for d in state['dals']] == list(range(1, 10))
            initial = geometry(phi[:, init_ids]); values[f'{snr}_initial'] = initial
            rows.append(dict(block=block, snr=snr, iteration=0, kind='reconstructed_initial_pilot',
                metrics=initial['metrics'], support_ids=init_ids.tolist(),
                reference_record_sha256=ref['sha256'], scores=ref['scores']))
            for d in state['dals']:
                ids = d['support_delays']*5+d['support_dopplers']+2
                assert len(ids) == 24 and set(ids.tolist()) == set(state['support'])
                assert d['mode'] == 'mean' and not d['oracle_mean'] and d['moment_source'] == 'code_feedback.ce'
                assert not any(k in d for k in ('covariance', 'Q'))
                assert d['A'].dtype == d['mu'].dtype == np.dtype('complex64')
                native = build_A_for_DALS_torch(1024, torch.from_numpy(d['support_delays']),
                    torch.from_numpy(d['support_dopplers']), pt+torch.from_numpy(d['mu']),
                    c1, c2, 2, cdtype=torch.complex64).numpy()
                np.testing.assert_array_equal(native, d['A'])
                detail = geometry(d['A']); values[f'{snr}_ce_{d["outer_iter"]}'] = detail
                rows.append(dict(block=block, snr=snr, iteration=d['outer_iter'], kind='captured_DALS',
                    metrics=detail['metrics'], support_ids=ids.tolist(),
                    regularization=float(d['regularization']),
                    relative_regularization=float(d['regularization'])/detail['metrics']['mean_column_energy'],
                    working_sigma2=float(d['sigma2']), mean_finite_variance=float(np.mean(d['finite_variance'])),
                    moments_source=d['feedback_moments_source'],
                    consumer_hashes=hashes({k:d[k] for k in ('A','mu','y','support_delays','support_dopplers','regularization')}),
                    native_design_exact=True, reference_record_sha256=ref['sha256'], scores=ref['scores']))
        return dict(geometry=values, rows=rows, physical_record_sha256=pe['sha256'])

    def audit(summary):
        assert summary['status'] == 'COMPLETE' and summary['calls'] == dict(A=32)
        assert summary['source_sha256'] == sha(manifest) and summary['script_sha256'] == args.script_sha256
        assert summary['contract_sha256'] == args.contract_sha256
        assert len(summary['records']) == 32 and {r['block'] for r in summary['records']} == set(range(32))
        arrays = 0; rows = []
        for entry in summary['records']:
            record, value = verified_record(entry, root)
            assert entry['kind'] == 'A' and entry['arm'] == 'ACTUAL_SUPPORT_GRAM' and entry['snr'] == 7
            expected_split = index['A', entry['block'], 7, 'G1_PROPAGATION']['split']
            assert entry['split'] == expected_split and record['scope'] == c['scope']
            reservation = json.loads(Path(entry['record']).with_name(record['token']+'-reserve.json').read_text())
            assert all(reservation[k] == record[k] == entry[k] for k in ('kind','block','snr','arm','split'))
            fresh = calculate(entry['block'])
            assert value['physical_record_sha256'] == fresh['physical_record_sha256']
            assert value['rows'] == fresh['rows']
            for key in fresh['geometry']:
                for field in ('gram','eigenvalues','column_norms'):
                    np.testing.assert_array_equal(value['geometry'][key][field], fresh['geometry'][key][field])
                assert value['geometry'][key]['metrics'] == fresh['geometry'][key]['metrics']
            arrays += finite_arrays(value); rows.extend(value['rows'])
        assert len(rows) == 640 and sum(r.get('native_design_exact',False) for r in rows) == 576
        return dict(rows=rows, arrays=arrays, saved_records=32, native_design_exact=576, reconstructed_initial_designs=64)

    if args.mode == 'audit':
        start = time.time(); end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out/'summary.json').read_text()); detail = audit(summary)
        assert detail == summary['raw_checks']; guard.verify()
        detail.update(status='PASS', summary_sha256=sha(out/'summary.json'), source_sha256=sha(manifest),
            script_sha256=args.script_sha256, contract_sha256=args.contract_sha256, wall_seconds=time.time()-start,
            new_receiver_terminal_decoder_estimator_calls=0, scope=c['scope'], independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(detail,f,indent=2)
        print(json.dumps({k:v for k,v in detail.items() if k != 'rows'})); return
    run = LightRun(root/'runs'/args.tag,'analysis',c['bounds'],c['output_bytes'],guard)
    try:
        for block in c['blocks']:
            split = index['A',block,7,'G1_PROPAGATION']['split']
            run.call('A',dict(block=block,snr=7,split=split,arm='ACTUAL_SUPPORT_GRAM'),
                lambda:calculate(block),lambda value:{},dict(scope=c['scope']))
            print(json.dumps(dict(block=block,calls=run.counts)),flush=True)
        summary = dict(status='COMPLETE',calls=run.counts,records=run.records,source_sha256=sha(manifest),
            script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,scope=c['scope'])
        summary['raw_checks'] = audit(summary); guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time()-run.started; run.write('summary.json',summary)
    except BaseException as exc:
        run.fail(exc); raise


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True)
    p.add_argument('--tag',required=True);p.add_argument('--mode',choices=['run','audit'],default='run')
    p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
