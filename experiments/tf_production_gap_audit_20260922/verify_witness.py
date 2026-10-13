"""Independently recount saved C scores in AF coordinates; no receiver/search."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

import audit_io


def verify(run, source, baseline, output, destination):
    if destination.exists():
        raise FileExistsError(destination)
    evidence = audit_io.attach(source, baseline)
    from physical import Channel

    manifest = json.loads((run / 'manifest.json').read_text())
    audit_io.verify_sources(manifest, source, baseline, evidence)
    receipt = json.loads((output / 'receipt.json').read_text())
    for name, digest in receipt['files'].items():
        if audit_io.sha256(output / name) != digest:
            raise ValueError(f'C hash differs: {name}')
    header = json.loads((run / 'context_header.json').read_text())['system']
    _, original = audit_io.read_records(run)
    original = {f"s{x['snr_centi_db']}_f{x['frame']:04d}": x for x in original}
    rows = list(csv.DictReader((output / 'witness_metrics.csv').open()))
    max_difference, count = 0., 0
    max_condition, max_coefficient_relative_difference, max_prediction_relative_difference = 0., 0., 0.
    ill_conditioned_cases = 0

    def check(actual, expected, label):
        nonlocal max_difference
        a, b = np.asarray(actual), np.asarray(expected)
        if not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError(f'nonfinite score: {label}')
        np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-8, err_msg=label)
        max_difference = max(max_difference, float(np.max(np.abs(a - b))))

    for row in rows:
        fid = row['observation_id']
        record = original[fid]
        obs = audit_io.load_bound(evidence, run / 'frames' / f'{fid}_input.npz', record['input_sha256'])
        truth = audit_io.load_bound(evidence, run / 'frames' / f'{fid}_truth.npz', record['frame_sha256'])
        cp = record['checkpoints'][-1]
        final = audit_io.load_bound(evidence, run / cp['path'], cp['artifact_sha256'])['snapshot']
        raw = audit_io.load_bound(evidence, output / 'raw' / f'{fid}.npz', receipt['files'][f'raw/{fid}.npz'])
        n, sigma2 = header['n_total'], float(obs['sigma2'])
        y, pilot = np.asarray(obs['y']), np.asarray(obs['pilot'])
        cases = [
            ('working', final['delays'], final['dopplers'], final['gains'], raw['working_scores']),
            ('true_geometry', truth['l_i'], truth['k_real'], raw['true_geometry_pilot_gains'], raw['true_geometry_scores']),
            ('broad_plugin', final['delays'], raw['broad_search']['baseline']['profile']['dopplers'], final['gains'], raw['broad_conditional']),
        ]
        for name in ('baseline', 'truth'):
            bits = np.asarray(raw['candidate_bits' if name == 'baseline' else 'truth_bits'], dtype=float)
            data = np.sqrt((1 - header['rho']) / 2) * ((1 - 2 * bits[:n]) + 1j * (1 - 2 * bits[n:]))
            candidate_cases = list(cases)
            for objective in ('profile', 'marginal'):
                fit = raw['broad_search'][name][objective]
                candidate_cases.append((f'broad_{objective}', fit['delays'], fit['dopplers'], None, {name: fit['scores']}))
            for prefix, delays, dopplers, gains, scores in candidate_cases:
                channel = Channel(n, header['c1'], header['c2'], delays, dopplers, np.ones(len(delays)))
                # Independent physical regressors in AF coordinates, not TimePathOps.
                B = channel.regressors(pilot + data)
                expected = scores[name]
                hp, _, rank, _ = np.linalg.lstsq(B, y, rcond=None)
                residual = y - B @ hp
                profile = float(np.vdot(residual, residual).real / sigma2)
                check(profile, expected['profile_score'], fid + prefix + name + 'profile')
                saved_hp = np.asarray(expected['profile_gains'])
                condition = float(np.linalg.cond(B))
                coefficient_difference = float(np.linalg.norm(hp - saved_hp) / max(np.linalg.norm(hp), 1.))
                prediction_difference = float(np.linalg.norm(B @ (hp - saved_hp)) / np.linalg.norm(y))
                max_condition = max(max_condition, condition)
                max_coefficient_relative_difference = max(max_coefficient_relative_difference, coefficient_difference)
                max_prediction_relative_difference = max(max_prediction_relative_difference, prediction_difference)
                # Nearly coincident true paths amplify tiny AF/time rounding
                # differences in unregularized coefficients. Verify their
                # identifiable fitted signal and optimality, not unstable digits.
                check(prediction_difference, 0., fid + prefix + name + 'fitted signal')
                gradient = np.linalg.norm(B.conj().T @ (y - B @ saved_hp))
                check(gradient / (np.linalg.norm(B, 2) * np.linalg.norm(y)), 0., fid + 'LS optimality')
                if condition < 1e4:
                    check(hp, saved_hp, fid + prefix + name + 'gains')
                else:
                    ill_conditioned_cases += 1
                if rank != expected['profile_rank']:
                    raise ValueError('profile rank differs')
                p = B.shape[1]
                gram = B.conj().T @ B
                q = B.conj().T @ y
                ridge = np.linalg.solve(gram + sigma2 * p * np.eye(p), q)
                # Woodbury / determinant lemma, independent of the SVD score path.
                sign, logdet = np.linalg.slogdet(np.eye(p) + gram / (sigma2 * p))
                check(sign, 1., fid + 'determinant')
                marginal = float((np.vdot(y, y).real - np.vdot(q, ridge).real) / sigma2 + logdet)
                check(marginal, expected['marginal_score'], fid + prefix + name + 'marginal')
                check(np.linalg.eigvalsh(gram), expected['response_gram_eigenvalues'], fid + 'Gram')
                if gains is not None:
                    residual = y - B @ gains
                    conditional = float(np.vdot(residual, residual).real / sigma2)
                    check(conditional, expected['conditional_score'], fid + prefix + name + 'conditional')
                    for metric, actual in [('conditional', conditional), ('profile', profile), ('marginal', marginal)]:
                        check(actual, float(row[f'{prefix}_{metric}_score_{name}']), fid + 'CSV')
                else:
                    check(profile if prefix == 'broad_profile' else marginal, float(row[f'{prefix}_{name}']), fid + 'broad CSV')
                count += 1
    if len(rows) != 32 or count != 320:
        raise ValueError('witness allocation differs')
    result = dict(status='pass', witnesses=len(rows), candidate_geometry_scores=count,
                  verified_artifact_hashes=len(receipt['files']), max_absolute_numerical_difference=max_difference,
                  max_response_condition=max_condition, ill_conditioned_coefficient_cases=ill_conditioned_cases,
                  max_coefficient_relative_difference=max_coefficient_relative_difference,
                  max_fitted_signal_relative_difference=max_prediction_relative_difference,
                  receiver_calls=0, search_calls=0, source_sha256=audit_io.sha256(Path(__file__)),
                  method='AF physical regressors + numpy lstsq + normal-equation Woodbury and determinant lemma',
                  scope='scores, fitted signals, LS optimality, ranks, spectra; coefficients compared directly only for condition<1e4; no global optimum claim',
                  c_receipt_sha256=audit_io.sha256(output / 'receipt.json'))
    audit_io.write_json(destination, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('run', 'source', 'baseline', 'c-output', 'out'):
        parser.add_argument('--' + argument, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.run, args.source, args.baseline, args.c_output, args.out)))
