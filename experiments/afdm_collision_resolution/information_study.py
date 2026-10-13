"""Four frozen actual collision base points; independent fit/evaluation splits."""
import argparse
import json
import sys
from pathlib import Path
import time

import numpy as np

from experiments.afdm_collision_resolution.collision_teacher import (
    CollisionTeacher, SCORE_COLUMNS, STEPS, exact_moment_system, power_features,
)
from experiments.afdm_higher_order_information.prior import frozen_components

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT/'results/afdm_collision_resolution/INFORMATION_CONFIG.json'


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k:plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def batch_summary(values, batches=8):
    values = np.asarray(values, float)
    if len(values) < batches or len(values) % batches or not np.isfinite(values).all():
        raise ValueError('finite rows divisible by the registered batch count required')
    means = np.asarray([part.mean(axis=0) for part in np.split(values, batches)])
    return dict(mean=values.mean(axis=0), batch_se=means.std(axis=0, ddof=1)/np.sqrt(batches),
                batches=batches, batch_means=means)


def fitted_information(scores, coefficient=None, rcond=1e-10):
    scores = np.asarray(scores, float)
    if scores.ndim != 2 or scores.shape[1] != 4 or not np.isfinite(scores).all():
        raise ValueError('four finite score columns required')
    design = scores[:, 1:]
    if coefficient is None:
        coefficient, _, rank, singular = np.linalg.lstsq(design, scores[:, 0], rcond=rcond)
    else:
        coefficient = np.asarray(coefficient, float)
        singular = np.linalg.svd(design, compute_uv=False)
        rank = int(np.sum(singular > rcond*singular[0])) if len(singular) else 0
    residual = scores[:, 0]-design@coefficient
    return dict(coefficient=coefficient, nuisance_rank=int(rank), nuisance_singular_values=singular,
                raw=batch_summary(scores[:, 0]**2), effective=batch_summary(residual**2),
                score_mean=batch_summary(scores), efficient_mean=batch_summary(residual),
                residual=residual, gram=scores.T@scores/len(scores))


def moment_projection(system, count, rcond=1e-10):
    """Optimal linear-moment tangent geometry; positive float is not a certificate."""
    covariance = system['covariance'][:count, :count]
    derivatives = system['derivatives'][:count]
    values, vectors = np.linalg.eigh(covariance)
    if values[-1] <= 0 or values[0] < -rcond*values[-1]:
        raise ValueError('invalid analytic moment covariance')
    keep = values > rcond*values[-1]
    # Declared PSD support, with no jitter and full discarded eigenvalues saved.
    inverse = (vectors[:, keep]/values[keep])@vectors[:, keep].T
    gram = derivatives.T@inverse@derivatives
    beta, _, rank, singular = np.linalg.lstsq(gram[1:, 1:], gram[1:, 0], rcond=rcond)
    witness = inverse@(derivatives[:, 0]-derivatives[:, 1:]@beta)
    target = float(witness@derivatives[:, 0])
    nuisance = witness@derivatives[:, 1:]
    variance = float(witness@covariance@witness)
    return dict(covariance_eigenvalues=values, covariance_rank=int(keep.sum()),
                covariance_condition=float(values[-1]/values[keep][0]), gram=gram,
                coefficient=beta, nuisance_gram_rank=int(rank), nuisance_gram_singular_values=singular,
                raw=float(gram[0, 0]), effective=float(gram[0, 0]-gram[0, 1:]@beta),
                witness=witness, witness_target=target, witness_nuisance=nuisance,
                witness_variance=variance, witness_ratio=target**2/variance if variance > 0 else None,
                linear_score_coefficients=inverse@derivatives,
                scope='finite-sum floating evaluation of analytic moment identities; no interval positivity certificate')


def nuisance_fd(teacher, y):
    point = np.array([teacher.mu, np.log(teacher.tau), np.log(teacher.sigma2)])
    all_scores = []
    for step in STEPS:
        columns = []
        for axis in range(3):
            plus, minus = point.copy(), point.copy()
            plus[axis] += step; minus[axis] -= step
            a = CollisionTeacher(plus[0], np.exp(plus[1]), np.exp(plus[2]))
            b = CollisionTeacher(minus[0], np.exp(minus[1]), np.exp(minus[2]))
            columns.append((a.logpdf(y)-b.logpdf(y))/(2*step))
        all_scores.append(np.column_stack(columns))
    return np.asarray(all_scores)


def calculate(output):
    from experiments.afdm_collision_resolution.protocol import dump
    config = json.loads(CONFIG_PATH.read_text())
    rows, costs = [], []
    start = time.perf_counter()
    for index, point in enumerate(config['points']):
        case_start = time.perf_counter()
        name = f'point_{index:02d}'
        teacher = CollisionTeacher(point['mu'], point['tau'], point['sigma2'])
        sample_start = time.perf_counter()
        raw = teacher.sample(config['observations_per_point'], [*config['seed'], index])
        sampling_seconds = time.perf_counter()-sample_start
        y = raw['y']
        np.savez_compressed(output/f'{name}_observations.npz', **raw,
                            public_point=np.array([point['mu'], point['tau'], point['sigma2']]))
        np.savez_compressed(output/f'{name}_components.npz', **teacher.component_state())
        teacher_start = time.perf_counter()
        evaluated = teacher.evaluate(y)
        fd = nuisance_fd(teacher, y)
        errors = abs(fd-evaluated['score'][None, :, 1:])
        qualified = np.all(errors <= config['nuisance_fd_abs_tolerance'], axis=(0, 2))
        np.savez_compressed(output/f'{name}_teacher.npz', **evaluated, nuisance_fd=fd,
                            nuisance_fd_error=errors, formula_qualified=qualified, steps=np.asarray(STEPS))
        teacher_seconds = time.perf_counter()-teacher_start
        train_size = config['train_size']
        train, heldout = evaluated['score'][:train_size], evaluated['score'][train_size:]
        fitted = fitted_information(train, rcond=config['rcond'])
        tested = fitted_information(heldout, fitted['coefficient'], config['rcond'])
        np.savez_compressed(output/f'{name}_full_projection.npz', coefficient=fitted['coefficient'],
                            train_residual=fitted['residual'], heldout_residual=tested['residual'])
        moment_start = time.perf_counter()
        system = exact_moment_system(teacher)
        np.savez_compressed(output/f'{name}_moments.npz', **{k:v for k, v in system.items() if isinstance(v, np.ndarray)})
        features = power_features(y, system['exponents'])
        feature_rows = []
        for level, count in (('powers_degree1', 4), ('powers_degree1_and2', 14)):
            analytic = moment_projection(system, count, config['rcond'])
            centered = features[:, :count]-system['mean'][:count]
            linear_score = centered@analytic['linear_score_coefficients']
            linear_residual = centered@analytic['witness']
            scale = np.sqrt(np.diag(system['covariance'])[:count])
            standardized = centered/scale
            regression, _, rank, singular = np.linalg.lstsq(standardized[:train_size], train, rcond=config['rcond'])
            prediction = standardized@regression
            pred_fit = fitted_information(prediction[:train_size], rcond=config['rcond'])
            pred_test = fitted_information(prediction[train_size:], pred_fit['coefficient'], config['rcond'])
            score_feature_cross = centered[train_size:].T@heldout/len(heldout)
            identity_error = score_feature_cross-system['derivatives'][:count]
            np.savez_compressed(output/f'{name}_{level}.npz', features=features[:, :count],
                                standardized=standardized, regression=regression, prediction=prediction,
                                regression_nuisance_coefficient=pred_fit['coefficient'], linear_score=linear_score,
                                linear_efficient_score=linear_residual, analytic_witness=analytic['witness'],
                                analytic_linear_coefficients=analytic['linear_score_coefficients'],
                                analytic_nuisance_coefficient=analytic['coefficient'],
                                train_regression_residual=pred_fit['residual'], heldout_regression_residual=pred_test['residual'])
            feature_rows.append(dict(level=level, dimension=count, analytic=analytic,
                regression_rank=int(rank), regression_singular_values=singular,
                regression_train={k:v for k,v in pred_fit.items() if k != 'residual'},
                regression_heldout={k:v for k,v in pred_test.items() if k != 'residual'},
                heldout_mse=batch_summary((prediction[train_size:]-heldout)**2),
                linear_heldout_raw=batch_summary(linear_score[train_size:, 0]**2),
                linear_heldout_effective=batch_summary(linear_residual[train_size:]**2),
                score_feature_cross_heldout=score_feature_cross,
                score_feature_identity_error=identity_error,
                identity_cross_batch_se=batch_summary(centered[train_size:, :, None]*heldout[:, None, :])['batch_se']))
        moment_seconds = time.perf_counter()-moment_start
        score_means = tested['score_mean']
        zmean = np.divide(abs(score_means['mean']), score_means['batch_se'],
                          out=np.full(4, np.inf), where=score_means['batch_se'] > 0)
        if not np.isfinite(zmean).all():
            raise ValueError('undefined score-mean diagnostic; do not silently serialize infinity')
        row = dict(point_id=name, public_point=point, new_observations=len(y), train=train_size,
            heldout=len(y)-train_size, kappa=teacher.kappa, geometry_fd=teacher.geo['finite_difference'],
            geometry_signature=teacher.geo['signature'], pdp_components=len(teacher.geo['pdp']['weights']),
            formula_qualified=int(qualified.sum()), formula_unqualified=int((~qualified).sum()),
            fd_absolute_max_by_step=errors.max(axis=(1, 2)),
            train_information={k:v for k,v in fitted.items() if k != 'residual'},
            heldout_information={k:v for k,v in tested.items() if k != 'residual'},
            heldout_score_mean_z=zmean, score_mean_within_four_se=(zmean <= 4).tolist(),
            positivity_diagnostic=bool(tested['effective']['mean'] > 4*tested['effective']['batch_se']),
            feature_rows=feature_rows, exact_moments_evaluated=system['distinct_moments'],
            scope='conditional actual G0 P2/common-zero-delay collision point; MC second moments are not certified Fisher information')
        rows.append(row)
        costs.append(dict(point_id=name, sample_seconds=sampling_seconds, teacher_and_fd_seconds=teacher_seconds,
                          moments_and_projections_seconds=moment_seconds, complete_case_seconds=time.perf_counter()-case_start,
                          finite_qpsk_orbits=len(teacher.m0), phase_quadrature_nodes=0, new_observations=len(y)))
        dump(output/f'{name}_summary.json', plain(row))
    dump(output/'information_cases.json', plain(rows))
    dump(output/'costs.json', plain(costs))
    return plain(dict(new_observations=sum(r['new_observations'] for r in rows), cases=len(rows), rows=rows,
        score_columns=SCORE_COLUMNS, observations_per_point=config['observations_per_point'],
        formula_unqualified=sum(r['formula_unqualified'] for r in rows), costs=costs,
        complete_seconds_before_summary=time.perf_counter()-start,
        failure_rule='all registered cases and unqualified rows retained; no score-mean/positivity exclusion',
        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False))


def main():
    from experiments.afdm_collision_resolution.protocol import run, PACKAGE
    from experiments.afdm_efficient_information.audit import loaded_project_sources
    frozen_components()
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text())
    sources = [*loaded_project_sources(sys.modules), CONFIG_PATH,
               PACKAGE/'test_collision_teacher.py', PACKAGE/'test_information_study.py',
               PACKAGE/'TEACHER.md', PACKAGE/'INFORMATION.md', PACKAGE/'DENSITY_THEORY.md', PACKAGE/'NUISANCE_THEORY.md']
    run(args.stage, config, sources, calculate, wall_seconds=config['wall_seconds'])


if __name__ == '__main__':
    main()
