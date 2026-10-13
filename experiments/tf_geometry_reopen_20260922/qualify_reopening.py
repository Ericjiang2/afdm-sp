"""Zero-receiver qualification of the supplied control and production adapter."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tf_production_gap_audit_20260922'))
import audit_io


def qualify(args):
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError('preserve prior qualification attempt')
    out.mkdir(parents=True)
    reference = Path(__file__).resolve().parent / 'reference'
    scratch = out / 'reference_execution'
    scratch.mkdir()
    for path in reference.glob('*.py'):
        shutil.copyfile(path, scratch / path.name)
    command = [sys.executable, '-B', str(scratch / 'verify_research.py')]
    audit_io.write_json(out / 'reference_argv.json', command)
    with (out / 'reference_stdout.log').open('w') as stdout, (out / 'reference_stderr.log').open('w') as stderr:
        process = subprocess.run(command, cwd=scratch, stdout=stdout, stderr=stderr, timeout=600)
    (out / 'reference_exit_code.txt').write_text(str(process.returncode) + '\n')
    if process.returncode:
        raise RuntimeError('supplied verify_research.py failed; see preserved logs')

    evidence = audit_io.attach(args.source, args.baseline)
    manifest = json.loads((args.run / 'manifest.json').read_text())
    audit_io.verify_sources(manifest, args.source, args.baseline, evidence)
    from physical import Channel, daft, projected_variance
    from messages import moments
    from twofft import TimePathOps
    import geometry_reopen as adapter

    spec = importlib.util.spec_from_file_location('supplied_geometry_reference', reference / 'geometry_exchange.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('reference module loader unavailable')
    ref = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ref
    spec.loader.exec_module(ref)
    errors = {}

    def check(name, actual, expected, tolerance):
        a, b = np.asarray(actual), np.asarray(expected)
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError(f'invalid comparison: {name}')
        difference = float(np.max(abs(a - b)))
        errors[name] = dict(max_absolute_difference=difference, tolerance=tolerance)
        if difference >= tolerance:
            raise AssertionError((name, difference, tolerance))

    def compare_case(label, y, x, v, ls, nus, c1, c2, ridge, candidate_ls, candidate_nus):
        n = len(y)
        Y = daft(y, c1, c2, True)
        xt = daft(x, c1, c2, True)
        check(label + '/Y', Y, ref.idaft(y, c1, c2), 2e-12)
        check(label + '/mean_transform', xt, ref.idaft(x, c1, c2), 2e-12)
        paths = [ref.Path(int(l), float(nu)) for l, nu in zip(ls, nus)]
        candidates = [ref.Path(int(l), float(nu)) for l, nu in zip(candidate_ls, candidate_nus)]
        channel = Channel(n, c1, c2, ls, nus, np.ones(len(ls)))
        candidate_channel = Channel(n, c1, c2, candidate_ls, candidate_nus, np.ones(len(candidate_ls)))
        B = TimePathOps(channel).responses_time(xt)
        U = TimePathOps(candidate_channel).responses_time(xt)
        check(label + '/active_actions', B, ref.responses(xt, paths, c1), 2e-12)
        check(label + '/candidate_actions', U, ref.responses(xt, candidates, c1), 2e-12)
        gamma = projected_variance(v, ls, nus, c1)
        check(label + '/Gamma', gamma, ref.gamma_cross(paths, paths, v, c1), 2e-10)
        all_ls = np.r_[ls, candidate_ls]
        all_nus = np.r_[nus, candidate_nus]
        cross = projected_variance(v, all_ls, all_nus, c1)[:len(ls), len(ls):]
        check(label + '/Gamma_cross', cross, ref.gamma_cross(paths, candidates, v, c1), 2e-10)
        Q = B.conj().T @ B + gamma + ridge * np.eye(len(ls))
        b = B.conj().T @ Y
        h = np.linalg.solve(Q, b)
        objective = float(np.vdot(Y, Y).real - np.vdot(b, h).real)
        _, refQ, refb, refh, refvalue = ref.system(Y, xt, v, paths, c1, ridge)
        check(label + '/Q', Q, refQ, 2e-10)
        check(label + '/b', b, refb, 2e-10)
        check(label + '/objective', objective, refvalue, 2e-10)
        check(label + '/predicted_signal', B @ h, B @ refh, 2e-10)
        if np.linalg.cond(Q) < 1e4:
            check(label + '/gains', h, refh, 2e-10)
        gradient = np.linalg.norm(Q @ refh - b) / max(np.linalg.norm(b), 1.)
        check(label + '/normal_equation_relative_residual', gradient, 0., 2e-10)
        for i in range(len(ls)):
            keep = np.arange(len(ls)) != i
            qr, br = Q[np.ix_(keep, keep)], b[keep]
            hr = np.linalg.solve(qr, br)
            reduced = np.vdot(Y, Y).real - np.vdot(br, hr).real
            for j, path in enumerate(candidates):
                q = B[:, keep].conj().T @ U[:, j] + cross[keep, j]
                bu = np.vdot(U[:, j], Y)
                diagonal = np.vdot(x, x).real + sum(v) + ridge
                schur = float(diagonal - np.vdot(q, np.linalg.solve(qr, q)).real)
                if schur <= 0:
                    raise FloatingPointError('qualification nonpositive Schur')
                value = reduced - abs(bu - np.vdot(q, hr))**2 / schur
                trial = paths.copy()
                trial[i] = path
                *_, direct = ref.system(Y, xt, v, trial, c1, ridge)
                check(f'{label}/Schur/{i}/{j}', value, direct, 2e-10)
        return dict(Q_condition=float(np.linalg.cond(Q)), coefficient_power=float(np.vdot(h, h).real),
                    receiver_calls=0, active_paths=len(ls), candidate_paths=len(candidate_ls))

    rng = np.random.default_rng(20260922)
    cn = lambda n: (rng.normal(size=n) + 1j * rng.normal(size=n)) / np.sqrt(2)
    fixture = compare_case('small_repeated_delay', cn(19), cn(19), rng.random(19),
                           np.array([1, 1, 7, 4]), np.array([.31, -.47, 1.19, -2.11]),
                           .037, .011, .22, np.array([1, 4, 7, 0]), np.array([.25, -.5, 1., 0.]))

    _, records = audit_io.read_records(args.run)
    record = next(x for x in records if x['snr_centi_db'] == 650 and x['frame'] == 0)
    obs = audit_io.load_bound(evidence, args.run / 'frames/s650_f0000_input.npz', record['input_sha256'])
    cp = record['checkpoints'][-1]
    saved = audit_io.load_bound(evidence, args.run / cp['path'], cp['artifact_sha256'])['snapshot']
    header = json.loads((args.run / 'context_header.json').read_text())['system']
    if header['n_total'] != 1024 or header['l_max_cap'] != 102:
        raise ValueError('frozen production delay domain differs')
    mu, v, _ = moments(np.clip(saved['app'], -20, 20), 1 - header['rho'])
    ls, nus = np.asarray(saved['delays']), np.asarray(saved['dopplers'])
    x = obs['pilot'] + mu
    production = compare_case('s650_f0000_r1', obs['y'], x, v, ls, nus,
                              header['c1'], header['c2'], obs['sigma2'],
                              np.array([ls[0], ls[0], 0, 102]), np.array([-3., 3., .25, -.5]))
    common = dict(c1=header['c1'], c2=header['c2'], ridge=obs['sigma2'],
                  max_delay=header['l_max_cap'], max_edits=2, local_passes=2)
    ref_result = ref.reopen_geometry(daft(obs['y'], header['c1'], header['c2'], True), x, v,
                     [ref.Path(int(l), float(nu)) for l, nu in zip(ls, nus)], **common)
    result = adapter.reopen_geometry(daft(obs['y'], header['c1'], header['c2'], True), x, v,
                     [adapter.Path(int(l), float(nu)) for l, nu in zip(ls, nus)], top_k=20, **common)
    check('adapter/reference_delays', [p.delay for p in result.paths], [p.delay for p in ref_result.paths], 1e-12)
    check('adapter/reference_dopplers', [p.doppler for p in result.paths], [p.doppler for p in ref_result.paths], 2e-10)
    check('adapter/reference_objective', result.objective_after, ref_result.objective_after, 2e-10)
    channel = Channel(1024, header['c1'], header['c2'], [p.delay for p in result.paths],
                      [p.doppler for p in result.paths], result.gains)
    B = TimePathOps(channel).responses_time(daft(x, header['c1'], header['c2'], True))
    check('adapter/reference_prediction', B @ result.gains, B @ ref_result.gains, 2e-10)
    reference_result = json.loads((scratch / 'verification_results.json').read_text())
    receipt = dict(status='pass', receiver_calls=0, original_manifest_sha256=audit_io.sha256(args.run / 'manifest.json'),
                   a_receipt_sha256=audit_io.sha256(args.a_receipt), original_checkpoint_sha256=cp['artifact_sha256'],
                   original_input_sha256=record['input_sha256'], reference_verification=reference_result,
                   reference_source_hashes={p.name: audit_io.sha256(p) for p in reference.glob('*.py')},
                   source_hashes={'geometry_reopen.py': audit_io.sha256(Path(adapter.__file__))},
                   qualifier_sha256=audit_io.sha256(Path(__file__)), comparisons=errors,
                   small_fixture=fixture, production_checkpoint=production,
                   adapter_reference_accepted_edits=len(result.edits),
                   note='Known-waveform finite-budget NMSE is diagnostic, not algebra gate; no true production file opened')
    audit_io.write_json(out / 'receipt.json', receipt)
    print(json.dumps(dict(status='pass', comparisons=len(errors), receiver_calls=0,
                          max_absolute_difference=max(x['max_absolute_difference'] for x in errors.values()))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['run', 'source', 'baseline', 'a-receipt', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    qualify(parser.parse_args())
