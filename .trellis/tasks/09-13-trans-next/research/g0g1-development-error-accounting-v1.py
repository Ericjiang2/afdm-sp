"""Offline projections of existing engineering states; no receiver or decoder."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(args):
    root = args.root
    source = root / 'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support

    contract = root / 'contracts' / (args.tag + '.json')
    c = json.loads(contract.read_text())
    manifest = source / 'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == args.tag == 'g0g1-development-error-accounting-v1'
    assert c['blocks'] == list(range(32)) and c['snrs'] == [7, 8]
    assert c['bounds'] == dict(A=32, seconds=360) and c['device'] == 'cpu'
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        a = json.loads((root / audit_path).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root / summary_path)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    eng = json.loads((root / 'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    old = json.loads((root / 'runs/terminal-controls-development-recovery-v1/development/summary.json').read_text())
    g1 = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in eng['records']}
    g0 = {(r['block'], r['snr']): r for r in old['records'] if r['kind'] == 'F' and r['arm'] == 'UNTEMPERED'}
    domain = np.arange(515, dtype=np.int64)

    def energy(x):
        return float(np.vdot(x, x).real)

    def project(h, ids, c1, c2):
        value, _ = project_channel_on_support(torch.as_tensor(h, dtype=torch.complex128),
            torch.from_numpy(ids // 5), torch.from_numpy(ids % 5 - 2), c1, c2, 2)
        return value.numpy()

    def split_energy(parts, target, denominator):
        assert denominator > 0 and np.isfinite(denominator)
        np.testing.assert_allclose(sum(parts), target, rtol=1e-11, atol=1e-12)
        terms = [energy(x) / denominator for x in parts]
        crosses = {f'{i}:{j}': float(2 * np.vdot(parts[i], parts[j]).real / denominator)
                   for i in range(len(parts)) for j in range(i + 1, len(parts))}
        total = energy(target) / denominator
        closure = total - sum(terms) - sum(crosses.values())
        assert abs(closure) <= 1e-10 * max(1., total)
        return dict(total=total, terms=terms, cross_terms=crosses, closure=closure)

    def calculate(block):
        entry = g1['A', block, 7, 'G1_PROPAGATION']
        _, physical = verified_record(entry, root)
        raw = physical['raw']
        h1 = raw['H']; h0 = raw['g0_reference']['H']; p = raw['pilot']
        params = raw['g0_reference']['params']
        c1, c2 = params['c1'], params['c2']
        assert len(h1) == 1024 and 2 * 1024 * c1 == 5
        assert np.all((params['l_exp'] >= 0) & (params['l_exp'] <= 102))
        assert np.all(abs(params['k_exp']) <= 2)
        d0 = project(h0, domain, c1, c2)
        d1 = project(h1, domain, c1, c2)
        outside0 = energy(h0 - d0) / energy(h0)
        assert outside0 < 1e-20
        model_parts = [h1 - d1, d1 - h0]
        model = split_energy(model_parts, h1 - h0, energy(h1))
        diag = physical['diagnostics']
        np.testing.assert_allclose(model['total'], diag['g0_reference_operator_nmse'], rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(model['terms'][0], diag['finite_dictionary_projection_nmse'], rtol=1e-10, atol=1e-12)
        assert abs(model['cross_terms']['0:1']) < 1e-10
        probe = np.exp(.137j * np.arange(1024))
        model_pilot = split_energy([v @ p for v in model_parts], (h1-h0) @ p, energy(h1 @ p))
        rows = []; matrices = dict(domain_g0=d0, domain_g1=d1)
        for label, h, hd in [('G0', h0, d0), ('G1', h1, d1)]:
            for snr in c['snrs']:
                ref = g0[block, snr] if label == 'G0' else g1['F', block, snr, 'G1_FULL']
                _, state = verified_record(ref, root)
                ids = np.asarray(state['support'], dtype=np.int64)
                assert len(ids) == len(set(ids.tolist())) and np.all((ids >= 0) & (ids < 515))
                estimate = np.asarray(state['H'], dtype=np.complex128)
                hs = project(h, ids, c1, c2)
                estimate_s = project(estimate, ids, c1, c2)
                # Fourth term retains any damping/mask/numerical subspace deviation.
                parts = [h-hd, hd-hs, hs-estimate_s, estimate_s-estimate]
                fm = split_energy(parts, h-estimate, energy(h))
                for pair in ['0:1', '0:2', '1:2']:
                    assert abs(fm['cross_terms'][pair]) < 1e-10
                pilot = split_energy([v @ p for v in parts], (h-estimate) @ p, energy(h @ p))
                probe_stats = split_energy([v @ probe for v in parts], (h-estimate) @ probe, energy(h @ probe))
                rows.append(dict(block=block, generator=label, snr=snr,
                    support_size=len(ids), reference_record_sha256=ref['sha256'],
                    reference_scores=ref['scores'], frobenius=fm, pilot_response=pilot,
                    fixed_probe_response=probe_stats))
                matrices[f'{label}_{snr}_truth_on_support'] = hs
                matrices[f'{label}_{snr}_estimate_on_support'] = estimate_s
        return dict(matrices=matrices, metrics=dict(block=block, g0_outside_domain_nmse=outside0,
            generator_difference=model, generator_difference_pilot=model_pilot, rows=rows))

    def audit(summary):
        assert summary['calls'] == dict(A=32) and len(summary['records']) == 32
        rows = []
        for entry in summary['records']:
            _, saved = verified_record(entry, root)
            fresh = calculate(entry['block'])
            for key in saved['matrices']:
                np.testing.assert_allclose(saved['matrices'][key], fresh['matrices'][key], rtol=1e-11, atol=1e-12)
            assert saved['metrics'] == fresh['metrics']
            rows.append(saved['metrics'])
        return rows

    out = root / 'runs' / args.tag / 'analysis'
    if args.mode == 'audit':
        started = time.time()
        end = json.loads((root / 'evidence' / (args.tag + '-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out / 'summary.json').read_text())
        assert summary['script_sha256'] == args.script_sha256 and summary['contract_sha256'] == args.contract_sha256
        rows = audit(summary); guard.verify()
        result = dict(status='PASS', rows=rows, summary_sha256=sha(out/'summary.json'),
            source_sha256=sha(manifest), script_sha256=args.script_sha256,
            wall_seconds=time.time()-started, saved_records=32, repeated_projection_analyses=32,
            new_generator_receiver_terminal_decoder_calls=0, scope=c['scope'])
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(result,f,indent=2)
        print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
        return
    run = LightRun(root/'runs'/args.tag, 'analysis', c['bounds'], c['output_bytes'], guard)
    try:
        for block in c['blocks']:
            run.call('A', dict(block=block, snr=7, split=g1['A', block, 7, 'G1_PROPAGATION']['split'], arm='EXISTING_STATE_PROJECTIONS'),
                lambda: calculate(block), lambda v: {}, dict(scope=c['scope']))
        summary = dict(status='COMPLETE', calls=run.counts, records=run.records,
            source_sha256=sha(manifest), contract_sha256=args.contract_sha256,
            script_sha256=args.script_sha256, scope=c['scope'])
        summary['rows'] = audit(summary)
        guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json', summary)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--mode', choices=['run', 'audit'], default='run')
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--script-sha256', required=True)
    main(parser.parse_args())
