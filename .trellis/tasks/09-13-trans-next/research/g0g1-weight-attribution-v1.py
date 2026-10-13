"""Attribute saved G0/G1 operator differences; truth-only, no receiver or decoder."""
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
    from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin

    contract = root / 'contracts' / (args.tag + '.json')
    c = json.loads(contract.read_text())
    manifest = source / 'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == args.tag == 'g0g1-weight-attribution-v1'
    assert c['blocks'] == [0, 20] and c['snrs'] == [7, 8]
    assert c['bounds'] == dict(A=2, seconds=180) and c['device'] == 'cpu'
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        a = json.loads((root / audit_path).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root / summary_path)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    eng = json.loads((root / 'runs/g1-strong-engineering-v1/engineering/summary.json').read_text())
    previous = json.loads((root / 'runs/g0g1-error-accounting-v1/analysis/summary.json').read_text())
    g1 = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in eng['records']}
    previous_records = {r['block']: r for r in previous['records']}
    stage_names = ['FULL_DOMAIN', 'EXACT_WINDOW', 'LEGACY_WEIGHT',
                   'CLUSTER_NORMALIZED', 'PRUNED', 'SAVED_G0']
    assert c['stages'] == stage_names and c['prune_relative_power'] == .01
    assert c['normalization_order'] == 'window_energy_before_domain_clip_and_prune'
    assert c['numeric_rtol'] == 1e-10 and c['threads'] == 1
    assert c['auxiliary'] == 'sign_consistent_weights_with_same_window_normalization_pruning_rule'

    def energy(x):
        return float(np.vdot(x, x).real)

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
        _, previous_value = verified_record(previous_records[block], root)
        raw = physical['raw']
        h1 = raw['H']; h0 = raw['g0_reference']['H']; pilot = raw['pilot']
        params = raw['g0_reference']['params']
        n = len(h1); c1, c2 = params['c1'], params['c2']
        assert n == 1024 and 2*n*c1 == 5 and params['k_leak'] == 2
        assert params['use_frac_doppler'] and len(params['g_i']) == 8
        delays = np.asarray(params['l_i'], dtype=np.int64)
        nu = np.asarray(params['k_real'])
        gains = np.asarray(params['g_i'])
        scale = float(params['fro_scale'])
        assert np.isfinite(scale) and scale > 0 and np.all(abs(nu) <= 2)
        assert np.all((delays >= 0) & (delays <= 102))
        np.testing.assert_array_equal(gains, np.asarray(params['g_i_raw'])*scale)
        samples = np.arange(n)
        qvalues = np.arange(-2, 3)
        mvalues = np.arange(-2, 3)
        centers = np.round(nu).astype(int)
        residuals = nu-centers
        alpha = AFDMEnvMixin.dirichlet_alpha
        # No simulator instance: only its frozen deterministic coefficient and
        # integer reconstruction functions are used on already-saved path data.
        shell = SimpleNamespace(N_total=n, c1=c1, c2=c2, gen_h_daft_convention='python')

        def matrix(coeff):
            return AFDMEnvMixin.gen_h_daft(shell, coeff.reshape(-1),
                np.repeat(delays, len(qvalues)), np.tile(qvalues, len(delays)))

        coefficients = {name: np.zeros((len(gains), len(qvalues)), complex)
                        for name in stage_names[:-1]}
        signed_coeff = np.zeros_like(coefficients['PRUNED'])
        weights = []; normalized_weights = []; signed_weights = []
        legacy_kept = []; signed_kept = []; normalizers = []
        replay_delays = []; replay_q = []; replay_gains = []
        max_formula_error = 0.
        for i, (center, residual, gain) in enumerate(zip(centers, residuals, gains)):
            exact = np.fft.fft(np.exp(2j*np.pi*nu[i]*samples/n))/n
            legacy = np.array([alpha(int(m), residual, n) for m in mvalues])
            signed = np.array([alpha(-int(m), residual, n) for m in mvalues])
            np.testing.assert_allclose(signed, exact[(center+mvalues) % n], rtol=1e-10, atol=1e-12)
            max_formula_error = max(max_formula_error,
                float(np.max(abs(signed-exact[(center+mvalues) % n]))))
            norm = np.sqrt(np.sum(abs(legacy)**2)+1e-300)
            signed_norm = np.sqrt(np.sum(abs(signed)**2)+1e-300)
            normalized = legacy/norm
            signed_normalized = signed/signed_norm
            keep = abs(normalized)**2 >= .01*np.max(abs(normalized)**2)
            signed_keep = abs(signed_normalized)**2 >= .01*np.max(abs(signed_normalized)**2)
            weights.append(legacy); normalized_weights.append(normalized)
            signed_weights.append(signed_normalized); normalizers.append(float(norm))
            legacy_kept.append(keep); signed_kept.append(signed_keep)
            coefficients['FULL_DOMAIN'][i] = gain*exact[qvalues % n]
            for j, q in enumerate(qvalues):
                m = int(q-center)
                if abs(m) > 2:
                    continue
                mm = m+2
                coefficients['EXACT_WINDOW'][i, j] = gain*exact[q % n]
                coefficients['LEGACY_WEIGHT'][i, j] = gain*legacy[mm]
                coefficients['CLUSTER_NORMALIZED'][i, j] = gain*normalized[mm]
                if keep[mm]:
                    coefficients['PRUNED'][i, j] = gain*normalized[mm]
                    replay_delays.append(int(delays[i])); replay_q.append(int(q))
                    # Preserve the original gain multiplication order exactly.
                    replay_gains.append(params['g_i_raw'][i]*normalized[mm]*scale)
                if signed_keep[mm]:
                    signed_coeff[i, j] = gain*signed_normalized[mm]
        np.testing.assert_array_equal(replay_delays, params['l_exp'])
        np.testing.assert_array_equal(replay_q, params['k_exp'])
        np.testing.assert_allclose(replay_gains, params['chan_coef_exp'], rtol=1e-12, atol=1e-14)
        matrices = {name: matrix(coeff) for name, coeff in coefficients.items()}
        matrices['SAVED_G0'] = np.array(h0, copy=True)
        matrices['SIGN_CONSISTENT'] = matrix(signed_coeff)
        d1 = previous_value['matrices']['domain_g1']
        np.testing.assert_allclose(matrices['FULL_DOMAIN'], d1, rtol=1e-10, atol=1e-11)
        np.testing.assert_allclose(matrices['PRUNED'], h0, rtol=1e-10, atol=1e-12)
        denominator = energy(h1)
        parts = [matrices[left]-matrices[right]
                 for left, right in zip(stage_names[:-1], stage_names[1:])]
        within = split_energy(parts, matrices['FULL_DOMAIN']-h0, denominator)
        full = split_energy([h1-matrices['FULL_DOMAIN']]+parts, h1-h0, denominator)
        pilot_split = split_energy([v@pilot for v in parts],
            (matrices['FULL_DOMAIN']-h0)@pilot, energy(h1@pilot))
        per_stage = {name: dict(to_full_g1_nmse=energy(h1-value)/denominator,
                                to_domain_g1_nmse=energy(d1-value)/denominator)
                     for name, value in matrices.items()}
        unscaled_nmse = energy(h1/scale-h0/scale)/energy(h1/scale)
        np.testing.assert_allclose(unscaled_nmse, full['total'], rtol=1e-12, atol=1e-14)
        np.testing.assert_allclose(full['total'], previous_value['metrics']['generator_difference']['total'],
                                   rtol=1e-10, atol=1e-12)
        assert all(np.isfinite(v).all() for v in matrices.values())
        return dict(matrices=matrices, coefficients=dict(coefficients,
                    SIGN_CONSISTENT=signed_coeff, legacy_window=np.asarray(weights),
                    normalized_window=np.asarray(normalized_weights),
                    sign_consistent_normalized_window=np.asarray(signed_weights),
                    legacy_keep=np.asarray(legacy_kept), sign_consistent_keep=np.asarray(signed_kept)),
            metrics=dict(block=block, physical_record_sha256=entry['sha256'],
                prior_accounting_record_sha256=previous_records[block]['sha256'],
                stages=per_stage, within_domain=within, full_difference=full,
                within_domain_pilot=pilot_split, component_order=[f'{a} minus {b}'
                    for a,b in zip(stage_names[:-1], stage_names[1:])],
                normalizers=normalizers, fro_scale=scale, unscaled_relative_nmse=unscaled_nmse,
                legacy_virtual_taps=len(replay_gains),
                g0_reconstruction_max_abs=float(np.max(abs(matrices['PRUNED']-h0))),
                projection_reconstruction_max_abs=float(np.max(abs(matrices['FULL_DOMAIN']-d1))),
                signed_formula_max_abs=max_formula_error,
                interpretation='Ordered telescoping attribution with all cross terms, not independent variance shares; '
                               'SIGN_CONSISTENT is a truth-side counterfactual, not a legal estimate or new generator.'))

    def audit(summary):
        assert summary['calls'] == dict(A=2) and len(summary['records']) == 2
        rows = []
        for entry in summary['records']:
            _, saved = verified_record(entry, root)
            fresh = calculate(entry['block'])
            for key in saved['matrices']:
                np.testing.assert_allclose(saved['matrices'][key], fresh['matrices'][key], rtol=1e-11, atol=1e-12)
            for key in saved['coefficients']:
                np.testing.assert_allclose(saved['coefficients'][key], fresh['coefficients'][key], rtol=1e-11, atol=1e-12)
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
            wall_seconds=time.time()-started, saved_records=2, repeated_attribution_analyses=2,
            new_generator_receiver_terminal_decoder_calls=0, scope=c['scope'])
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
        print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
        return
    run = LightRun(root/'runs'/args.tag, 'analysis', c['bounds'], c['output_bytes'], guard)
    try:
        for block in c['blocks']:
            run.call('A', dict(block=block, snr=7, split=2, arm='EXISTING_STATE_WEIGHT_ATTRIBUTION'),
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
