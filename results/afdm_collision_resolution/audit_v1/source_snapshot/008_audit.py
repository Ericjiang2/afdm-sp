"""Independent saved-data reconstruction; no experiment statistic is imported."""
import argparse
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from scipy import linalg, special
from scipy.stats import qmc

from experiments.afdm_efficient_information.protocol import ROOT, ARTIFACT, MISSION, dump, run

PROTECTED = MISSION/'protected_baseline.json'
ADMISSION_REJECTION = MISSION/'TRANSFER_ADMISSION_REJECTION.json'
TOLERANCE = dict(atol=1e-7, rtol=2e-6)


def read_json(path):
    return json.loads(Path(path).read_text())


def read_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name:archive[name].copy() for name in archive.files}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT/path


def loaded_project_sources(modules):
    # The actual implementations are torch._ops and torch._classes. Only these
    # exact namespace metadata pairs are synthetic; missing real files must fail.
    virtual = {'torch.ops':'_ops.py', 'torch.classes':'_classes.py'}
    paths = set()
    for name, module in tuple(modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename or (name in virtual and filename == virtual[name]):
            continue
        path = Path(filename).resolve()
        if path.suffix == '.py' and path.is_relative_to(ROOT):
            paths.add(path)
    return sorted(paths)


def audit_admission_rejections(path=ADMISSION_REJECTION):
    record = read_json(path)
    if (record['status'] != 'rejected_before_registration' or record['new_observations'] != 0
            or record['reserved_wall_seconds'] != 0):
        raise ValueError('admission rejection must have zero registered observations/reservation')
    if (ARTIFACT/record['stage_requested']).exists():
        raise ValueError('pre-registration rejection unexpectedly created a stage')
    return [dict(**record, record_sha256=sha(path),
                 cost_scope='no registered stage/observation/wall reservation; unrecorded diagnostic wall is not invented')]


class Checks:
    def __init__(self):
        self.count = 0
        self.maximum_absolute_error = 0.
        self.failures = []

    def close(self, actual, expected, label, **tolerance):
        actual, expected = np.asarray(actual), np.asarray(expected)
        if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.isfinite(expected).all():
            raise ValueError(f'{label}: shape/nonfinite mismatch')
        if actual.dtype == bool or expected.dtype == bool:
            return self.equal(actual, expected, label)
        error = float(np.max(abs(actual-expected))) if actual.size else 0.
        self.maximum_absolute_error = max(self.maximum_absolute_error, error)
        self.count += 1
        if not np.allclose(actual, expected, **(tolerance or TOLERANCE)):
            self.failures.append(dict(label=label, maximum_absolute_error=error))

    def equal(self, actual, expected, label):
        self.count += 1
        if not np.array_equal(actual, expected):
            self.failures.append(dict(label=label, error='exact-value mismatch'))

    def result(self):
        return dict(checks=self.count, maximum_absolute_error=self.maximum_absolute_error,
                    failures=self.failures, passed=not self.failures)


def observed_polynomials(y):
    """Closed products, independently of the sparse monomial catalog."""
    y = np.asarray(y, complex)
    if y.ndim != 2 or y.shape[1] < 4 or not np.isfinite(y).all():
        raise ValueError('finite observations with N>=4 required')
    n = y.shape[1]
    p = y.real*y.real+y.imag*y.imag
    a, b = max(1, n//4), max(max(1, n//4)+1, n//2)
    c = min(n-1, max(b+1, 3*n//4))
    columns = [p.mean(axis=1), (p*p).mean(axis=1), p[:, 0]*(p[:, a]-p[:, b]), p[:, 0]*(p[:, a]-p[:, c])]
    values = {'energy':np.column_stack(columns[:1]), 'old_T':np.column_stack(columns)}
    columns.extend(p[:, j] for j in range(n))
    columns.extend(p[:, i]*p[:, j] for i in range(n) for j in range(i, n))
    values['powers'] = np.column_stack(columns)
    for i in range(n):
        for j in range(i+1, n):
            coherence = y[:, i]*y[:, j].conj()
            for part in (np.real, np.imag):
                columns.extend([part(coherence), part(coherence*coherence)])
                columns.extend(part(coherence)*p[:, k] for k in range(n))
    values['phase'] = np.column_stack(columns)
    pivot = np.argmax(p, axis=1)
    anchor_power = p[np.arange(len(y)), pivot]
    # A selected column of rrH divided by its pivot, rather than multiplying by
    # a phase obtained by the implementation's canonical_phase function.
    column = y*y[np.arange(len(y)), pivot].conj()[:, None]
    z = np.divide(column, np.sqrt(anchor_power)[:, None], out=np.zeros_like(column),
                  where=anchor_power[:, None]>0)
    values['gauge'] = np.concatenate([z.real, z.imag], axis=1)
    return values


def predict(features, state):
    x = np.asarray(features, float)
    active = state['active'].astype(bool)
    standardized = (x[:, active]-state['mean'][active])/state['scale'][active]
    # Einsum is independent of the original chained matmul implementation.
    return np.einsum('ij,jk->ik', standardized, state['coefficients'])*state['score_scale']+state['score_mean']


def nuisance_projection(scores):
    s = np.asarray(scores, float)
    coefficient = linalg.lstsq(s[:, 1:], s[:, 0], cond=1e-5, lapack_driver='gelsd')[0]
    residual = s[:, 0]-s[:, 1:]@coefficient
    return dict(beta=coefficient, raw=float(np.mean(s[:, 0]**2)),
                effective=float(np.mean(residual**2)), residual=residual)


def linear_moment(features, scores):
    """Project scores onto the observed feature span via a data-matrix SVD."""
    f, s = np.asarray(features, float), np.asarray(scores, float)
    centered = f-f.mean(axis=0)
    scale = np.sqrt(np.mean(centered*centered, axis=0))
    active = scale>1e-14*max(float(scale.max()), 1.)
    x = centered[:, active]/scale[active]
    if not x.shape[1]:
        return dict(raw=0., effective=0., rank=0, covariance=np.empty((0, 0)), jacobian=np.empty((0, s.shape[1])))
    u, singular, _ = linalg.svd(x, full_matrices=False, lapack_driver='gesvd')
    keep = singular>1e-5*singular[0]
    projected = u[:, keep].T@s/np.sqrt(len(x))
    beta = linalg.lstsq(projected[:, 1:], projected[:, 0], cond=1e-5, lapack_driver='gelsd')[0]
    residual = projected[:, 0]-projected[:, 1:]@beta
    return dict(raw=float(projected[:, 0]@projected[:, 0]), effective=float(residual@residual),
                rank=int(keep.sum()), covariance=x.T@x/len(x), jacobian=x.T@s/len(x))


def fit_ridge(features, scores, ridge):
    """Independent LAPACK least-squares fit, including augmented ridge rows."""
    f, s = np.asarray(features, float), np.asarray(scores, float)
    mean, scale = f.mean(axis=0), f.std(axis=0)
    active = scale>1e-14*max(float(scale.max()), 1.)
    x = (f[:, active]-mean[active])/scale[active]
    target_mean, target_scale = s.mean(axis=0), s.std(axis=0)
    target_scale[target_scale<=1e-14] = 1.
    target = (s-target_mean)/target_scale
    rank = linalg.lstsq(x, target, cond=1e-10, lapack_driver='gelsd')[2]
    if ridge:
        design = np.vstack([x, np.sqrt(len(x)*ridge)*np.eye(x.shape[1])])
        rhs = np.vstack([target, np.zeros((x.shape[1], s.shape[1]))])
    else:
        design, rhs = x, target
    coefficients = linalg.lstsq(design, rhs, cond=1e-10, lapack_driver='gelsd')[0]
    return dict(mean=mean, scale=scale, active=active, score_mean=target_mean,
                score_scale=target_scale, coefficients=coefficients, rank=rank, ridge=ridge)


def gaussian_teacher(y, words, mass, theta, want_score=True, batch=128):
    """Independent Hermitian spectral density and score over saved finite words."""
    q, mu, tau, noise = np.asarray(theta, float)
    n = y.shape[1]
    omega = 2*np.pi*(np.arange(n)[:, None]-np.arange(n)[None, :])/n
    outer = words[:, :, None]*words[:, None, :].conj()
    phase = np.exp(1j*mu*omega)
    base = outer*phase
    signal = base*np.cos(np.sqrt(q)*omega)
    covariance = tau*signal+noise*np.eye(n)
    eigenvalues, vectors = np.linalg.eigh(covariance)
    if np.any(eigenvalues<=0):
        raise ValueError('saved Gaussian teacher has a nonpositive covariance')
    inverse = (vectors/eigenvalues[:, None, :])@vectors.conj().transpose(0, 2, 1)
    normal = -n*np.log(np.pi)-np.log(eigenvalues).sum(axis=1)+np.log(mass)
    derivatives = np.stack([-.5*tau*base*omega**2*np.sinc(np.sqrt(q)*omega/np.pi),
                            1j*tau*omega*signal, signal, np.broadcast_to(np.eye(n), covariance.shape)], axis=1)
    values, scores = [], []
    for start in range(0, len(y), batch):
        observation = y[start:start+batch]
        solved = np.einsum('kij,bj->bki', inverse, observation)
        log_components = normal[None, :]-np.einsum('bi,bki->bk', observation.conj(), solved).real
        total = special.logsumexp(log_components, axis=1)
        values.append(total)
        if want_score:
            derivative_quadratic = np.einsum('bki,kaij,bkj->bka', solved.conj(), derivatives, solved).real
            trace = np.einsum('kij,kaji->ka', inverse, derivatives).real
            scores.append(np.sum(np.exp(log_components-total[:, None])[:, :, None]*(derivative_quadratic-trace), axis=1))
    return dict(logpdf=np.concatenate(values), score=np.concatenate(scores) if want_score else None)


def component_teacher(y, saved, noise, batch=8):
    """Bessel integration from already-saved means/derivatives, without new nodes."""
    means, weights = saved['means'], saved['logweights']
    values, scores = [], []
    power = np.sum(means.real**2+means.imag**2, axis=1)
    derivative = saved.get('derivatives')
    for start in range(0, len(y), batch):
        observation = y[start:start+batch]
        inner = np.einsum('bi,ki->bk', observation.conj(), means)
        radius = abs(inner)
        kappa = 2*radius/noise
        bessel = special.ive(0, kappa)
        squared_norm = np.sum(abs(observation)**2, axis=1)
        conditional = weights-(squared_norm[:, None]+power)/noise+np.log(bessel)+kappa-y.shape[1]*np.log(np.pi*noise)
        total = special.logsumexp(conditional, axis=1)
        values.append(total)
        if derivative is not None and derivative.size:
            ratio = special.ive(1, kappa)/bessel
            unit = np.divide(inner.conj(), radius, out=np.zeros_like(inner), where=radius>0)
            columns = []
            for dmean in derivative:
                term = -2*np.real(np.sum(means.conj()*dmean, axis=1))/noise
                directional = np.einsum('bi,ki->bk', observation.conj(), dmean)
                columns.append(term+2*ratio*np.real(unit*directional)/noise)
            columns.append(-y.shape[1]+(squared_norm[:, None]+power)/noise-ratio*kappa)
            conditional_score = np.stack(columns, axis=2)
            posterior = np.exp(conditional-total[:, None])
            scores.append(np.sum(posterior[:, :, None]*conditional_score, axis=1))
    return dict(logpdf=np.concatenate(values), score=np.concatenate(scores) if scores else None)


def audit_hashes(stages, protected=PROTECTED):
    counts = dict(protected=0, sources=0, snapshots=0, artifacts=0, committed_blobs=0)
    protected_map = read_json(protected)
    for name, expected in protected_map.items():
        if sha(resolve(name)) != expected:
            raise ValueError(f'protected baseline changed: {name}')
        counts['protected'] += 1
    git_root = Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT,
                                   check=True, capture_output=True, text=True).stdout.strip())
    rows = []
    for folder in stages:
        registration, attempt = read_json(folder/'registration.json'), read_json(folder/'attempt.json')
        fingerprints = registration['source_sha256']
        ordered = sorted((resolve(name).resolve(), expected) for name, expected in fingerprints.items())
        for index, (path, expected) in enumerate(ordered):
            if sha(path) != expected:
                raise ValueError(f'bound source changed: {path}')
            counts['sources'] += 1
            snapshot = folder/'source_snapshot'/f'{index:03d}_{path.name}'
            if snapshot.exists():
                if sha(snapshot) != expected:
                    raise ValueError(f'source snapshot mismatch: {snapshot}')
                counts['snapshots'] += 1
            elif attempt['status'] == 'complete':
                raise ValueError(f'complete stage lacks source snapshot: {snapshot}')
        for name, expected in registration['git']['committed_task_source_sha256'].items():
            git_path = str(resolve(name).relative_to(git_root))
            blob = subprocess.run(['git', 'show', registration['git_head']+':'+git_path], cwd=ROOT,
                                  check=True, capture_output=True).stdout
            if hashlib.sha256(blob).hexdigest() != expected:
                raise ValueError(f'committed source mismatch: {name}')
            counts['committed_blobs'] += 1
        manifest = attempt['artifact_sha256']
        actual_files = {p.resolve() for p in folder.rglob('*') if p.is_file() and p.name != 'attempt.json'}
        if actual_files != {resolve(name).resolve() for name in manifest}:
            raise ValueError(f'raw artifact inventory differs: {folder}')
        for name, expected in manifest.items():
            if sha(resolve(name)) != expected:
                raise ValueError(f'artifact changed: {name}')
            counts['artifacts'] += 1
        for field in ('wall_seconds', 'cpu_seconds', 'peak_rss_bytes', 'reserved_wall_seconds', 'reserved_new_observations'):
            value = attempt.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                raise ValueError(f'invalid/missing attempt cost {folder}: {field}')
        if attempt['reserved_wall_seconds'] != registration['wall_cap_seconds'] or attempt['reserved_new_observations'] != registration['config']['new_observations']:
            raise ValueError(f'reservation changed: {folder}')
        rows.append(dict(stage=folder.name, status=attempt['status'],
                         observations=attempt['reserved_new_observations'], reserved_wall=attempt['reserved_wall_seconds'],
                         wall=attempt['wall_seconds'], cpu=attempt['cpu_seconds'], rss=attempt['peak_rss_bytes']))
    return dict(counts=counts, stages=rows, total_reserved_observations=sum(r['observations'] for r in rows),
                total_reserved_wall=sum(r['reserved_wall'] for r in rows), actual_wall=sum(r['wall'] for r in rows),
                actual_cpu=sum(r['cpu'] for r in rows))


def audit_feature_layer(features, scores, state, raw, row, splits, ridges, bootstrap, seed, checks):
    ntrain, nvalid, ntest = splits
    train, validation, test = features[:ntrain], features[ntrain:ntrain+nvalid], features[-ntest:]
    train_s, validation_s, test_s = scores[:ntrain], scores[ntrain:ntrain+nvalid], scores[-ntest:]
    label = f"point{row['point']}/{row['level']}"
    checks.close(test, raw['features_test'], label+'/features')
    prediction, training_prediction = predict(test, state), predict(train, state)
    checks.close(prediction, raw['predictions'], label+'/predictions')
    fits = []
    for ridge in ridges:
        fit = fit_ridge(train, train_s, ridge)
        loss = float(np.mean(((predict(validation, fit)-validation_s)/fit['score_scale'])**2))
        fits.append((loss, ridge, fit))
    selected = min(fits, key=lambda item:(item[0], item[1]))
    checks.equal(selected[1], row['selected_ridge'], label+'/ridge_selection')
    checks.close(selected[2]['coefficients'], state['coefficients'], label+'/independent_fit')
    checks.equal(selected[2]['rank'], row['training_rank'], label+'/training_rank')
    checks.close([item[0] for item in fits], [item['validation_standardized_mse'] for item in row['validation_candidates']], label+'/validation_losses')
    beta = nuisance_projection(train_s)['beta']
    checks.close(beta, row['frozen_beta'], label+'/frozen_beta')
    checks.close(beta, state['efficient_beta'], label+'/saved_beta')
    error = (prediction-test_s)**2
    checks.close(error.mean(axis=0), row['score_mse'], label+'/score_mse')
    batches = np.array_split(error, min(16, len(error)))
    se = np.std([batch.mean(axis=0) for batch in batches], axis=0, ddof=1)/np.sqrt(len(batches))
    checks.close(se, row['score_mse_batch_se'], label+'/score_mse_se')
    checks.close(np.mean((training_prediction-train_s)**2, axis=0), row['training_score_mse'], label+'/training_mse')
    target = test_s[:, 0]-test_s[:, 1:]@beta
    projected = prediction[:, 0]-prediction[:, 1:]@beta
    checks.close(np.mean((target-projected)**2), row['effective_target_mse'], label+'/effective_mse')
    checks.close(test_s[:, 1:].T@target/len(test_s), row['heldout_nuisance_residual'], label+'/nuisance_residual')
    full = nuisance_projection(test_s)
    checks.close(full['raw'], row['teacher_raw'], label+'/teacher_raw')
    checks.close(full['effective'], row['teacher_effective_plugin'], label+'/teacher_effective')
    info = linear_moment(test, test_s)
    checks.close(info['effective'], row['feature_linear_information_plugin'], label+'/linear_information')
    checks.close(info['raw'], row['feature_raw_linear_plugin'], label+'/linear_raw')
    checks.equal(info['rank'], row['feature_rank'], label+'/feature_rank')
    checks.close(info['covariance'], raw['heldout_feature_covariance'], label+'/covariance')
    checks.close(info['jacobian'], raw['heldout_jacobian'], label+'/jacobian')
    checks.close(linear_moment(prediction, test_s)['effective'], row['compressed_prediction_linear_plugin'], label+'/compressed_linear')
    checks.close(linear_moment(train, train_s)['effective'], row['training_feature_linear_plugin'], label+'/training_linear')
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(bootstrap):
        indices = rng.integers(len(test), size=len(test))
        values.append(linear_moment(test[indices], test_s[indices])['effective'])
    checks.close(values, raw['bootstrap_linear_information'], label+'/bootstrap')
    checks.close(np.quantile(values, [.025, .975]), row['feature_linear_bootstrap_percentile_95'], label+'/bootstrap_interval')
    cost = row['inference_cost']
    checks.equal(cost['test_predictions'], ntest, label+'/prediction_count')
    checks.equal(cost['regression_multiply_adds'], ntest*int(state['active'].sum())*scores.shape[1], label+'/regression_operations')


def audit_features(folder, checks):
    config = read_json(folder/'registration.json')['config']
    rows = read_json(folder/'feature_cases.json')
    control = 'public_points' in config
    observations = 0
    for point in range(len(config['public_points']) if control else 1):
        data = read_npz(folder/(f'observations_{point}.npz' if control else 'observations.npz'))
        y = data['y']
        observations += len(y)
        features = observed_polynomials(y)
        if control:
            teacher = gaussian_teacher(y, data['teacher_time_words'], data['teacher_weights'], data['public_theta'])
            checks.close(teacher['logpdf'], data['logpdf'], f'{folder.name}/{point}/logpdf')
            checks.close(teacher['score'], data['score'], f'{folder.name}/{point}/score')
            score = data['score']
            indices = np.concatenate([data[k] for k in ('train_indices', 'validation_indices', 'test_indices')])
            checks.equal(indices, np.arange(len(y)), f'{folder.name}/{point}/split_partition')
            theta = data['public_theta']
            response = np.exp(2j*np.pi*np.outer(theta[1]+np.array([-np.sqrt(theta[0]), np.sqrt(theta[0])]), np.arange(y.shape[1]))/y.shape[1])
            replay = (data['gain_truth']@response)*data['teacher_time_words'][data['word_indices']]+np.sqrt(theta[3])*data['unit_noise']
            checks.close(replay, y, f'{folder.name}/{point}/raw_generation_replay')
        else:
            score = read_npz(folder/f"teacher_order{config['primary_order']}.npz")['score']
            teacher_arrays = {}
            for order in config['orders']:
                component = read_npz(folder/f'components_order{order}.npz')
                teacher = component_teacher(y, component, np.exp(data['public_theta'][3]))
                saved = read_npz(folder/f'teacher_order{order}.npz')
                teacher_arrays[order] = saved
                checks.close(teacher['logpdf'], saved['logpdf'], f'{folder.name}/order{order}/logpdf')
                checks.close(teacher['score'], saved['score'], f'{folder.name}/order{order}/score')
            refined_component = read_npz(folder/'components_refined_step.npz')
            step_teacher = component_teacher(y, refined_component, np.exp(data['public_theta'][3]))
            refinement = read_npz(folder/'teacher_refinement.npz')
            checks.close(step_teacher['score'], refinement['refined_step_scores'], folder.name+'/all_refined_step_scores')
            primary, fine = teacher_arrays[config['primary_order']], teacher_arrays[max(config['orders'])]
            density_error = abs(primary['logpdf']-fine['logpdf'])
            score_error = np.max(abs(primary['score']-fine['score']), axis=1)
            step_error = np.max(abs(primary['score']-step_teacher['score']), axis=1)
            for name, value in [('logpdf_error', density_error), ('score_error', score_error), ('step_error', step_error)]:
                checks.close(value, refinement[name], folder.name+'/'+name)
            qualified = (density_error<=config['logpdf_tolerance'])&(score_error<=config['score_tolerance'])&(step_error<=config['step_tolerance'])
            checks.equal(qualified, refinement['qualified'], folder.name+'/all_teacher_qualification')
            result = read_json(folder/'results.json')
            checks.equal(int(qualified.sum()), result['teacher_qualified'], folder.name+'/qualified_denominator')
            checks.equal(int((~qualified).sum()), result['teacher_unqualified'], folder.name+'/unqualified_denominator')
            start = sum(config['split_sizes'][:2])
            mismatch = read_json(folder/'mismatch.json')
            source_model = read_npz(resolve(config['control_model']))
            theta = data['public_theta']
            multiplier = np.array([2*theta[0], 1., np.exp(theta[2]), np.exp(theta[3])])
            proxy = predict(features['phase'][start:], source_model)*multiplier
            mismatch_raw = read_npz(folder/'Gaussian_proxy_mismatch.npz')
            checks.close(proxy, mismatch_raw['predicted_native_coordinates'], folder.name+'/all_Gaussian_proxy_predictions')
            checks.close(np.mean((proxy-score[start:])**2, axis=0), mismatch['mse'], folder.name+'/proxy_mse')
        for index, level in enumerate(config['levels']):
            row = next(r for r in rows if r['point'] == point and r['level'] == level)
            state = read_npz(folder/f'model_{point}_{level}.npz')
            raw = read_npz(folder/f'evaluation_{point}_{level}.npz')
            seed = [*config['seed'], 100, point, index] if control else [*config['seed'], 200, index]
            audit_feature_layer(features[level], score, state, raw, row, config['split_sizes'],
                                config['ridges'], config['bootstrap_replicates'], seed, checks)
    checks.equal(observations, config['new_observations'], folder.name+'/observations')
    return dict(stage=folder.name, observations=observations, full_feature_rows=observations, layers=len(rows))


def expected_polynomials(covariance, mass):
    """Independent Isserlis contractions, matching the observed map's order."""
    k = np.asarray(covariance)
    n = k.shape[1]
    p = np.diagonal(k, axis1=1, axis2=2).real
    cross = p[:, :, None]*p[:, None, :]+abs(k)**2
    a, b = max(1, n//4), max(max(1, n//4)+1, n//2)
    c = min(n-1, max(b+1, 3*n//4))
    columns = [p.mean(axis=1), (2*p*p).mean(axis=1), cross[:, 0, a]-cross[:, 0, b], cross[:, 0, a]-cross[:, 0, c]]
    result = {'energy':mass@np.column_stack(columns[:1]), 'old_T':mass@np.column_stack(columns)}
    columns.extend(p[:, j] for j in range(n))
    columns.extend(cross[:, i, j] for i in range(n) for j in range(i, n))
    result['powers'] = mass@np.column_stack(columns)
    for i in range(n):
        for j in range(i+1, n):
            for part in (np.real, np.imag):
                columns.extend([part(k[:, i, j]), part(2*k[:, i, j]**2)])
                columns.extend(part(k[:, i, j]*p[:, a]+k[:, i, a]*k[:, a, j]) for a in range(n))
    result['phase'] = mass@np.column_stack(columns)
    return result


def reconstruct_bank(training, centered_means, candidate_means):
    residual = training-centered_means
    scale = np.sqrt(np.mean(residual**2, axis=0))
    active = scale>1e-14*max(float(scale.max()), 1.)
    x = residual[:, active]/scale[active]
    covariance = x.T@x/len(x)
    inverse = linalg.pinvh(covariance, rtol=1e-10) if len(covariance) else covariance
    eigenvalues = linalg.eigvalsh(covariance) if len(covariance) else np.array([])
    rank = int(np.count_nonzero(eigenvalues>1e-10*max(float(eigenvalues[-1]), 1e-30))) if len(eigenvalues) else 0
    return dict(scale=scale, active=active, inverse=inverse, means=candidate_means[:, active]/scale[active], rank=rank)


def bank_objectives(group_mean, bank, repeats):
    delta = group_mean[:, None, bank['active'].astype(bool)]/bank['scale'][bank['active'].astype(bool)]-bank['means'][None, :, :]
    return repeats*np.einsum('bki,ij,bkj->bk', delta, bank['inverse'], delta)


def group_prefix(values, groups, maximum, repeats, mean):
    if len(values) != groups*maximum:
        raise ValueError('saved group rows disagree with the registered denominator')
    indices = np.arange(groups)[:, None]*maximum+np.arange(repeats)[None, :]
    summed = values[indices].sum(axis=1)
    return summed/repeats if mean else summed


def wilson_counts(k, n):
    if n <= 0 or not 0 <= k <= n:
        raise ValueError('invalid Bernoulli denominator')
    z = special.ndtri(.975)
    center = (k+z*z/2)/(n+z*z)
    half = z*np.sqrt(k*(1-k/n)+z*z/4)/(n+z*z)
    return [float(center-half), float(center+half)]


def calibrate_grid(objectives, candidates, null, alpha):
    rows, thresholds, confidence = [], [], []
    for condition, objective in enumerate(objectives):
        best = objective.min(axis=1)
        rank = math.ceil((len(objective)+1)*(1-alpha))
        if rank > len(objective):
            raise ValueError('calibration sample cannot support the declared alpha')
        cutoff = float(sorted(objective[:, condition]-best)[rank-1])
        confidence.append(cutoff)
        detection = None
        if candidates[condition, 0] == null:
            detection = float(sorted(objective[:, candidates[:, 0] == null].min(axis=1)-best)[rank-1])
            thresholds.append(detection)
        rows.append(dict(condition=condition, groups=len(objective), rank=rank,
                         confidence_cutoff=cutoff, null_cutoff=detection))
    return dict(detection_cutoff=max(thresholds), confidence_cutoff=max(confidence), conditions=rows)


def audit_grid_case(objective, candidates, condition, null, calibration, interest, row, raw, checks, randomized=None):
    label = f"{row['method']}/R{row['repeats']}/condition{condition}"
    index = objective.argmin(axis=1)
    best = objective[np.arange(len(objective)), index]
    detection = objective[:, candidates[:, 0] == null].min(axis=1)-best
    confidence = objective-best[:, None] <= calibration['confidence_cutoff']
    rejected = detection>calibration['detection_cutoff'] if randomized is None else randomized
    estimate = candidates[index]
    checks.equal(index, raw['indices'], label+'/selected')
    checks.close(estimate, raw['estimates'], label+'/estimates')
    checks.close(detection, raw['detection_statistic'], label+'/detection')
    checks.equal(rejected, raw['rejected'], label+'/rejected')
    checks.equal(confidence, raw['grid_confidence_set'], label+'/grid_sets')
    n = len(objective)
    checks.equal(row['groups'], n, label+'/groups')
    checks.equal(row['rejections'], int(rejected.sum()), label+'/rejection_count')
    checks.close(row['rejection_rate'], rejected.mean(), label+'/rejection_rate')
    checks.close(row['rejection_wilson95'], wilson_counts(int(rejected.sum()), n), label+'/rejection_interval')
    truth = candidates[condition]
    errors = estimate-truth
    boundary = np.array([[(value == candidates[:, j].min() or value == candidates[:, j].max())
                         for j, value in enumerate(selected)] for selected in estimate])
    checks.equal(boundary, raw['boundary'], label+'/boundary')
    checks.close(row['boundary_rates'], boundary.mean(axis=0), label+'/boundary_rates')
    unidentified = row['unidentifiable_coordinates']
    for j in range(candidates.shape[1]):
        if j in unidentified:
            checks.equal(row['parameter_rmse'][j], None, label+f'/unidentified{j}')
        else:
            checks.close(row['parameter_rmse'][j], np.sqrt(np.mean(errors[:, j]**2)), label+f'/rmse{j}')
            checks.close(row['parameter_bias'][j], errors[:, j].mean(), label+f'/bias{j}')
    target = np.sqrt(estimate[:, 0]) if interest == 'q' else estimate[:, 0]
    truth_target = np.sqrt(truth[0]) if interest == 'q' else truth[0]
    squared = (target-truth_target)**2
    if 0 not in unidentified:
        checks.close(row['half_gap_rmse'], np.sqrt(squared.mean()), label+'/delta_rmse')
        checks.close(row['half_gap_mse_standard_error'], squared.std(ddof=1)/np.sqrt(n), label+'/delta_mse_se')
    checks.close(row['joint_grid_coverage'], confidence[:, condition].mean(), label+'/joint_coverage')
    checks.close(row['joint_grid_coverage_wilson95'], wilson_counts(int(confidence[:, condition].sum()), n), label+'/coverage_interval')
    interest_covered = [np.any(candidates[mask, 0] == truth[0]) for mask in confidence]
    widths = []
    for mask in confidence:
        points = candidates[mask, 0]
        if not len(points):
            raise ValueError('empty saved calibrated grid set')
        widths.append(np.ptp(np.sqrt(points) if interest == 'q' else points))
    checks.close(row['interest_grid_coverage'], np.mean(interest_covered), label+'/interest_coverage')
    checks.close(row['mean_grid_set_size'], confidence.sum(axis=1).mean(), label+'/grid_size')
    checks.close(row['mean_half_gap_grid_hull_width'], np.mean(widths), label+'/grid_width')
    checks.equal(row['empty_grid_sets'], 0, label+'/empty_sets')
    checks.equal(row['fit_failures'], 0, label+'/fit_failures')


def audit_inference(folder, checks):
    config = read_json(folder/'registration.json')['config']
    control = 'q' in config
    data = read_npz(folder/('inference_observations.npz' if control else 'observations.npz'))
    y, candidates = data['y'], data['candidates']
    raw_likelihoods = read_npz(folder/'likelihoods.npz')
    rows = read_json(folder/'cases.json')
    calibration = read_json(folder/'calibration.json')
    values = observed_polynomials(y)
    if control:
        score_state = read_npz(resolve(config['score_model']))
        values['score4'] = predict(values['phase'], score_state)
        train_raw = read_npz(folder/'training.npz')
        train_values = observed_polynomials(train_raw['y'])
        train_values['score4'] = predict(train_values['phase'], score_state)
        source = score_state
        words, mass = source['teacher_time_words'], source['teacher_weights']
        independent_logpdf = np.column_stack([gaussian_teacher(y, words, mass, theta, want_score=False)['logpdf'] for theta in candidates])
        checks.close(independent_logpdf, raw_likelihoods['exact_logpdf'], folder.name+'/all_exact_logpdf')
        variance = candidates[:, 2]+candidates[:, 3]
        second = -y.shape[1]*np.log(np.pi*variance)[None, :]-np.sum(abs(y)**2, axis=1)[:, None]/variance
        checks.close(second, raw_likelihoods['second_gaussian_logpdf'], folder.name+'/second_gaussian')
        matrices = {'exact':raw_likelihoods['exact_logpdf'], 'second_gaussian':second}
        offset, null, interest = 0, 0., 'q'
        training_count = len(train_raw['y'])
    else:
        for name, key in [('actual_score4', 'actual_score_model'), ('Gaussian_transfer_score4', 'control_score_model')]:
            values[name] = predict(values['phase'], read_npz(resolve(config[key])))
        offset = int(data['calibration_slices'][0, 0])
        observed = y[offset:]
        matrices = {'actual_reference':raw_likelihoods['primary'], 'actual_reference_refined':raw_likelihoods['refined'],
                    'second_gaussian':raw_likelihoods['second_gaussian']}
        replay_ids = np.concatenate([np.arange(a, min(a+8, b)) for split in ('calibration', 'evaluation')
                                     for a, b in data[split+'_slices']])-offset
        for order, key in [(config['primary_order'], 'primary'), (config['refined_order'], 'refined')]:
            for condition, theta in enumerate(candidates):
                components = read_npz(folder/f'components_order{order}_c{condition:02d}.npz')
                value = component_teacher(observed[replay_ids], components, np.exp(theta[3]))['logpdf']
                checks.close(value, raw_likelihoods[key][replay_ids, condition], folder.name+f'/order{order}/candidate{condition}')
        for column, condition in enumerate(raw_likelihoods['audit_candidate_indices']):
            components = read_npz(folder/f"components_order{config['audit_order']}_c{condition:02d}.npz")
            value = component_teacher(observed[raw_likelihoods['audit_row_indices']], components,
                                      np.exp(candidates[condition, 3]))['logpdf']
            checks.close(value, raw_likelihoods['audit_logpdf'][:, column], folder.name+f'/saved_audit/candidate{condition}')
        variance = raw_likelihoods['variance']
        second = -np.log(np.pi*variance).sum(axis=1)[None, :]-(abs(observed)**2)@(1/variance).T
        checks.close(second, raw_likelihoods['second_gaussian'], folder.name+'/second_gaussian')
        absolute = abs(raw_likelihoods['primary']-raw_likelihoods['refined'])
        checks.close(absolute, raw_likelihoods['absolute_error'], folder.name+'/reference_error')
        qualified = absolute<=config['logpdf_tolerance']
        checks.equal(qualified, raw_likelihoods['qualified'], folder.name+'/qualified')
        audit_error = abs(raw_likelihoods['audit_logpdf']-raw_likelihoods['refined'][np.ix_(
            raw_likelihoods['audit_row_indices'], raw_likelihoods['audit_candidate_indices'])])
        checks.close(audit_error, raw_likelihoods['audit_error'], folder.name+'/order48_audit_error')
        qualification = read_json(folder/'reference_qualification.json')
        derived = dict(candidate_observation_pairs=int(absolute.size), unqualified_pairs=int((~qualified).sum()),
            maximum_logpdf_error=float(absolute.max()), audit_pairs=int(audit_error.size),
            audit_unqualified_pairs=int((audit_error>config['logpdf_tolerance']).sum()),
            maximum_audit_logpdf_error=float(audit_error.max()),
            full_reference_qualified=bool(qualified.all() and (audit_error<=config['logpdf_tolerance']).all()))
        for key, value in derived.items():
            checks.close(value, qualification[key], folder.name+'/qualification/'+key)
        mean_rows = read_json(folder/'mean_validation.json')
        for row in mean_rows:
            condition, method = row['condition'], row['method']
            a, b = data['training_slices'][condition]
            c, d = data['mean_validation_slices'][condition]
            train, valid = values[method][a:b], values[method][c:d]
            difference = valid.mean(axis=0)-train.mean(axis=0)
            se = np.sqrt(train.var(axis=0, ddof=1)/len(train)+valid.var(axis=0, ddof=1)/len(valid))
            if np.any((se == 0)&(difference != 0)):
                raise ValueError('different deterministic means with zero standard error')
            normalized = np.divide(abs(difference), se, out=np.zeros_like(se), where=se>0)
            for key, value in [('difference', difference), ('standard_error', se),
                               ('absolute_se_ratio', normalized), ('maximum_absolute_se_ratio', normalized.max())]:
                checks.close(value, row[key], f'{method}/c{condition}/mean_validation/'+key)
        null, interest, training_count = config['delta'][0], 'delta', 0
    banks = {}
    for path in sorted(folder.glob('bank_*.npz')):
        method = path.stem[5:]
        saved = read_npz(path)
        if control:
            candidate_means = []
            omega = 2*np.pi*(np.arange(y.shape[1])[:, None]-np.arange(y.shape[1])[None, :])/y.shape[1]
            base = words[:, :, None]*words[:, None, :].conj()
            for q, mu, tau, noise in candidates:
                covariance = tau*base*np.exp(1j*mu*omega)*np.cos(np.sqrt(q)*omega)+noise*np.eye(y.shape[1])
                means = expected_polynomials(covariance, mass)
                candidate_means.append(predict(means['phase'][None], score_state)[0] if method == 'score4' else means[method])
            candidate_means = np.asarray(candidate_means)
            train = train_values[method]
            centered_means = candidate_means[train_raw['condition_indices']]
        else:
            blocks = [values[method][a:b] for a, b in data['training_slices']]
            candidate_means = np.array([block.mean(axis=0) for block in blocks])
            train = np.concatenate(blocks)
            centered_means = np.concatenate([np.broadcast_to(mean, block.shape) for mean, block in zip(candidate_means, blocks)])
        checks.close(candidate_means, saved['candidate_means'], path.stem+'/means')
        reconstructed = reconstruct_bank(train, centered_means, candidate_means)
        for key in ('scale', 'active', 'inverse', 'means', 'rank'):
            checks.close(reconstructed[key], saved[key], path.stem+'/'+key)
        banks[method] = saved
    maximum = max(config['repeats'])
    for method in sorted({row['method'] for row in rows}):
        for repeat in config['repeats']:
            calibration_raw = read_npz(folder/f'calibration_{method}_R{repeat}.npz')['objectives']
            for split, groups in [('calibration', config['calibration_groups']), ('evaluation', config['evaluation_groups'])]:
                for condition, (a, b) in enumerate(data[split+'_slices']):
                    if method in banks:
                        grouped = group_prefix(values[method][a:b], groups, maximum, repeat, True)
                        objective = bank_objectives(grouped, banks[method], repeat)
                    else:
                        objective = -2*group_prefix(matrices[method][a-offset:b-offset], groups, maximum, repeat, False)
                    saved = (calibration_raw[condition] if split == 'calibration' else
                             read_npz(folder/f'evaluation_{method}_R{repeat}_c{condition:02d}.npz')['objective'])
                    checks.close(objective, saved, f'{method}/R{repeat}/{split}/c{condition}/objective')
            recomputed = calibrate_grid(calibration_raw, candidates, null, config['alpha'])
            declared = calibration[f'{method}_R{repeat}']
            for key in ('detection_cutoff', 'confidence_cutoff'):
                checks.close(recomputed[key], declared[key], f'{method}/R{repeat}/'+key)
            checks.equal(recomputed['conditions'], declared['conditions'], f'{method}/R{repeat}/calibration_conditions')
            for condition in range(len(candidates)):
                row = next(r for r in rows if r['method'] == method and r['repeats'] == repeat and r['condition'] == condition)
                raw = read_npz(folder/f'evaluation_{method}_R{repeat}_c{condition:02d}.npz')
                randomized = None
                if control and method == 'second_gaussian':
                    randomized = np.random.default_rng([*config['seed'], 3, repeat, condition]).random(len(raw['objective']))<config['alpha']
                audit_grid_case(raw['objective'], candidates, condition, null, declared, interest, row, raw, checks, randomized)
                if not control:
                    a, b = data['evaluation_slices'][condition]
                    group_qualified = group_prefix(qualified[a-offset:b-offset].all(axis=1),
                        config['evaluation_groups'], maximum, repeat, False) == repeat
                    checks.equal(group_qualified, raw['numerical_reference_qualified'], f'{method}/R{repeat}/c{condition}/reference_qualified')
                    checks.equal(int((~group_qualified).sum()), row['numerical_reference_unqualified_groups'],
                                 f'{method}/R{repeat}/c{condition}/reference_denominator')
    if not control:
        for row in read_json(folder/'reference_sensitivity.json'):
            condition, repeat = row['condition'], row['repeats']
            primary = read_npz(folder/f'evaluation_actual_reference_R{repeat}_c{condition:02d}.npz')['objective']
            refined = read_npz(folder/f'evaluation_actual_reference_refined_R{repeat}_c{condition:02d}.npz')['objective']
            checks.close(np.max(abs(primary-refined)), row['maximum_candidate_objective_difference'], f'R{repeat}/c{condition}/reference_sensitivity')
            checks.equal(int(np.count_nonzero(primary.argmin(axis=1)!=refined.argmin(axis=1))),
                         row['selected_candidate_disagreements'], f'R{repeat}/c{condition}/selection_sensitivity')
    checks.equal(len(y)+training_count, config['new_observations'], folder.name+'/observations')
    return dict(stage=folder.name, observations=len(y)+training_count, evaluation_cases=len(rows),
                all_candidate_objectives_rebuilt=True, likelihood_replay_rows=len(y) if control else len(replay_ids),
                likelihood_replay_candidates=len(candidates), all_saved_order48_subset_replayed=not control)


def _pdp_law(n, theta, mode):
    if not (isinstance(mode, str) and mode == 'marginal'):
        pdp = np.ones((1, 2)) if isinstance(mode, str) and mode == 'equal' else np.asarray(mode)[None, :]
        return pdp, np.ones(1)
    ts, resolution = 1/8000., 1/(n*15.)
    indices = np.arange(1, int(np.ceil(resolution/ts))+3)
    maximum = indices[np.round((indices-1)*ts/resolution).astype(int) == 0][-1]
    limits = np.floor(maximum*(1+np.array([theta[1]-theta[0], theta[1]+theta[0]])*8000/(12000*n))).astype(int)
    survival, decay = np.exp(-ts/.0008), np.log(10)*20/10/.01*ts
    pdp, weights = [], []
    for assignment in (0, 1):
        l1, l2 = limits if assignment == 0 else limits[::-1]
        for j2 in range(1, l2):
            maximum_j1 = min(l1, l2-j2)
            if maximum_j1 > 0:
                pair = [1., np.exp(-decay*j2)]
                pdp.append(pair if assignment == 0 else pair[::-1])
                weights.append(.5*(1-survival)*survival**(j2-1)*(1-survival**maximum_j1))
    return np.asarray(pdp), np.asarray(weights)/sum(weights)


def _prior_components(case, rule, theta, n, step):
    """Reconstruct only the original registered rule, with independent derivatives.

    Frozen physical geometry is reused. No ActualPrior, density, score, or
    pushforward differentiation function is called by this audit path.
    """
    from experiments.afdm_higher_order_information.prior import geometry, small_system
    system = small_system(n)
    system.k_max_cap = min(2, (n-1)//2)
    geo = geometry(system, theta[1], theta[0])
    if rule['rule'] == 'product':
        t, mass = special.roots_legendre(rule['order'])
        t, mass = (t+1)/2, mass/2
        t = np.repeat(t, rule['phases'])
        phi = np.tile(2*np.pi*(np.arange(rule['phases'])+.5)/rule['phases'], rule['order'])
        mass = np.repeat(mass/rule['phases'], rule['phases'])
    elif rule['rule'] == 'sobol':
        count = rule['order']*rule['phases']
        points = qmc.Sobol(2, scramble=True, seed=rule['seed']).random_base2(count.bit_length()-1)
        t, phi, mass = points[:, 0], 2*np.pi*points[:, 1], np.full(count, 1/count)
    else:
        raise ValueError('unknown registered prior rule')
    nodes = np.column_stack([np.sqrt(t), np.sqrt(1-t)*np.exp(1j*phi)])
    pdp, weights = _pdp_law(n, theta, case['pdp'])
    angular = np.sum(weights[None, :]*(pdp[:, 0]*pdp[:, 1])[None, :]
                     /(t[:, None]*pdp[:, 1]+(1-t[:, None])*pdp[:, 0])**2, axis=1)
    mass = mass*angular
    mass_error = abs(float(mass.sum())-1)
    mass /= mass.sum()
    active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
    platform = case['model'] == 'g0' and len(active) == 1 and np.all(geo['weights'][active[0]] != 0)
    if platform:
        atom = active[0] % (2*system.k_max_cap+1)-system.k_max_cap
        response = np.exp(2j*np.pi*atom*np.arange(n)/n)[None, :]
        mass, mass_error = np.ones(1), 0.
        differentiated = np.zeros((2, 1, n), complex)
    else:
        energy = np.real(np.sum(nodes.conj()*(nodes@geo['gram'].T), axis=1))
        gains = nodes/np.sqrt(energy[:, None])
        response = gains@geo[case['model']].T
        differentiated = []
        for axis in (0, 1):
            plus, minus = theta.copy(), theta.copy()
            plus[axis] += step
            minus[axis] -= step
            gp, gm = geometry(system, plus[1], plus[0]), geometry(system, minus[1], minus[0])
            dr = (gp['gram']-gm['gram'])/(2*step)
            db = (gp[case['model']]-gm[case['model']])/(2*step)
            derivative_energy = np.real(np.sum(nodes.conj()*(nodes@dr.T), axis=1))
            derivative_gain = -.5*gains*(derivative_energy/energy)[:, None]
            differentiated.append(derivative_gain@geo[case['model']].T+gains@db.T)
    labels = np.column_stack([np.zeros(4**(n-1), int), np.array(list(product(range(4), repeat=n-1)))])
    words = np.exp(1j*(np.pi/4+np.pi/2*labels))
    k = np.arange(n)
    matrix = np.exp(2j*np.pi*.1/n**2*k*k)[:, None]*np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)*np.exp(2j*np.pi*2.5/n*k*k)[None, :]
    time_words = words@matrix.conj()
    means = (np.exp(theta[2]/2)*response[:, None, :]*time_words).reshape(-1, n)
    derivative = np.stack([(np.exp(theta[2]/2)*d[:, None, :]*time_words).reshape(-1, n) for d in differentiated]+[means/2])
    return dict(means=means, logweights=np.log(np.repeat(mass/len(words), len(words))),
                derivatives=derivative, quadrature_mass_error=mass_error, platform=platform)


def audit_prior_information(folder, checks, replay_rows=8):
    config = read_json(folder/'registration.json')['config']
    records = read_json(folder/'information.json')
    for record in records:
        case = record['case']
        raw = read_npz(folder/(case['name']+'.npz'))
        theta = raw['theta']
        split = config['independent_projection_train']
        effective, masses = {}, {}
        for rule in config['rules']:
            name = rule['name']
            score = raw[name+'_score']
            train = score[:split]
            beta, _, rank, singular = linalg.lstsq(train[:, 1:], train[:, 0], cond=config['nuisance_rcond'], lapack_driver='gelsd')
            for section, sample in [('train', train), ('validation', score[split:])]:
                residual = sample[:, 0]-sample[:, 1:]@beta
                stored = record['information'][name][section]
                checks.close(stored['coefficient'], beta, case['name']+'/'+name+'/'+section+'/beta')
                checks.close(stored['raw'], np.mean(sample[:, 0]**2), case['name']+'/'+name+'/'+section+'/raw')
                checks.close(stored['effective'], np.mean(residual**2), case['name']+'/'+name+'/'+section+'/effective')
                chunks = np.array_split(residual**2, min(8, len(sample)))
                standard_error = np.std([chunk.mean() for chunk in chunks], ddof=1)/np.sqrt(len(chunks))
                checks.close(stored['effective_batch_se'], standard_error, case['name']+'/'+name+'/'+section+'/se')
                checks.equal(stored['nuisance_rank'], rank, case['name']+'/'+name+'/'+section+'/rank')
                checks.close(stored['score_mean'], sample.mean(axis=0), case['name']+'/'+name+'/'+section+'/score_mean')
                if section == 'validation':
                    checks.close(residual, raw[name+'_effective_validation'], case['name']+'/'+name+'/residual')
                    effective[name] = np.mean(residual**2)
            reconstructed = _prior_components(case, rule, theta, config['n'], config['derivative_steps'][0])
            independent = component_teacher(raw['y'][:replay_rows], reconstructed, np.exp(theta[3]))
            checks.close(independent['logpdf'], raw[name+'_logpdf'][:replay_rows], case['name']+'/'+name+'/reconstructed_logpdf')
            checks.close(independent['score'], score[:replay_rows], case['name']+'/'+name+'/reconstructed_score')
            checks.close(reconstructed['quadrature_mass_error'], record['quadrature_mass_errors'][name], case['name']+'/'+name+'/mass')
            masses[name] = reconstructed['quadrature_mass_error']
        comparisons = []
        for first, second in [('coarse', 'fine'), ('fine', 'independent')]:
            difference = raw[first+'_score']-raw[second+'_score']
            relative = np.sqrt(np.mean(difference**2, axis=0))/np.maximum(np.sqrt(np.mean(raw[second+'_score']**2, axis=0)), .01)
            comparisons.append(dict(logpdf_max=float(np.max(abs(raw[first+'_logpdf']-raw[second+'_logpdf']))), score_relative_rms=relative))
        for index, comparison in enumerate(comparisons):
            for key in comparison:
                checks.close(comparison[key], record['comparisons'][index][key], case['name']+f'/comparison{index}/'+key)
        finite = raw['finite_difference_score']
        fd_relative = np.sqrt(np.mean((finite-raw['fine_score'][:len(finite)])**2, axis=0))/np.maximum(np.sqrt(np.mean(finite**2, axis=0)), .01)
        checks.close(fd_relative, record['finite_difference_relative_rms'], case['name']+'/fd_residual')
        relative_effective = abs(effective['fine']-effective['independent'])/max(effective['independent'], .001)
        checks.close(relative_effective, record['effective_rule_relative_error'], case['name']+'/information_refinement')
        fine_rule = next(rule for rule in config['rules'] if rule['name'] == 'fine')
        derivative_ok = True
        for index, step in enumerate(config['derivative_steps'][1:]):
            small = raw[f'score_step_{step}']
            component = _prior_components(case, fine_rule, theta, config['n'], step)
            teacher = component_teacher(raw['y'][:len(small)], component, np.exp(theta[3]))
            checks.close(teacher['score'], small, case['name']+f'/step{step}/reconstructed')
            relative = np.sqrt(np.mean((raw['fine_score'][:len(small)]-small)**2, axis=0))/np.maximum(np.sqrt(np.mean(small**2, axis=0)), .01)
            maximum = np.max(abs(raw['fine_logpdf'][:len(small)]-teacher['logpdf']))
            checks.close(relative, record['derivative_steps'][index]['comparison']['score_relative_rms'], case['name']+f'/step{step}/relative')
            checks.close(maximum, record['derivative_steps'][index]['comparison']['logpdf_max'], case['name']+f'/step{step}/logpdf')
            checks.equal(step, record['derivative_steps'][index]['step'], case['name']+f'/step{step}/declared')
            derivative_ok = derivative_ok and maximum<=config['logpdf_max_tolerance'] and max(relative)<=config['derivative_relative_tolerance']
        step = config['derivative_steps'][-1]
        for axis in range(4):
            densities = []
            for sign in (1, -1):
                shifted = theta.copy()
                shifted[axis] += sign*step
                component = _prior_components(case, fine_rule, shifted, config['n'], step)
                component.pop('derivatives')
                densities.append(component_teacher(raw['y'][:len(finite)], component, np.exp(shifted[3]))['logpdf'])
            checks.close((densities[0]-densities[1])/(2*step), finite[:, axis], case['name']+f'/FD{axis}/reconstructed')
        gates = dict(node_rules=bool(all(c['logpdf_max']<=config['logpdf_max_tolerance'] and
                         max(c['score_relative_rms'])<=config['score_relative_rms_tolerance'] for c in comparisons)),
            derivative_steps=bool(derivative_ok), direct_finite_difference=bool(max(fd_relative)<=config['derivative_relative_tolerance']),
            quadrature_mass=bool(max(masses.values())<=config['mass_tolerance']),
            effective_information=bool(relative_effective<=config['effective_relative_tolerance']))
        checks.equal(gates, record['refinement_checks'], case['name']+'/all_gates')
        checks.equal(all(gates.values()), record['refined'], case['name']+'/refined_decision')
        classification = ('exact_zero' if case['name'] == 'platform_g0_actual_marginal' else
            'numerically_positive_not_certified' if record['refined'] and effective['fine']>
                config['positive_evidence_standard_errors']*record['information']['fine']['validation']['effective_batch_se']
            else 'unresolved_numerical_information')
        checks.equal(classification, record['classification'], case['name']+'/classification')
    return dict(stage=folder.name, all_score_statistic_rows=len(records)*config['observations_per_case'],
                reconstructed_existing_rule_rows_per_case=replay_rows, rules_per_case=len(config['rules']),
                saved_component_replay=False, existing_rule_reconstruction=True, new_scientific_rules=0)


def audit_prior_refinement(folder, checks):
    config = read_json(folder/'registration.json')['config']
    raw, record = read_npz(folder/'scores.npz'), read_json(folder/'refinement.json')
    y, theta = raw['y'], raw['theta']
    effective, masses, node_count = {}, {}, 0
    for rule in config['rules']:
        name = rule['name']
        nodes = read_npz(folder/(name+'_nodes.npz'))
        exponent = config['endpoint_power']
        complement = (1-nodes['chart_s'])**exponent
        sphere = np.column_stack([np.sqrt(1-complement), np.sqrt(complement)*np.exp(1j*nodes['chart_phi'])])
        checks.close(sphere@nodes['unitary'].T, nodes['nodes'], name+'/chart_nodes')
        checks.close(exponent*(1-nodes['chart_s'])**(exponent-1), nodes['jacobian'], name+'/Jacobian')
        checks.close(nodes['base_weights']*nodes['jacobian'], nodes['weights'], name+'/positive_weights')
        checks.close(nodes['unitary'].conj().T@nodes['unitary'], np.eye(2), name+'/unitary')
        node_count += len(nodes['nodes'])
        component = read_npz(folder/(name+'__base_components.npz'))
        replay = component_teacher(y[:8], component, np.exp(theta[3]))
        checks.close(replay['logpdf'], raw[name+'_logpdf'][:8], name+'/component_logpdf')
        checks.close(replay['score'], raw[name+'_score'][:8], name+'/component_score')
        score = raw[name+'_score']
        split = config['independent_projection_train']
        beta, _, rank, _ = linalg.lstsq(score[:split, 1:], score[:split, 0], cond=config['nuisance_rcond'], lapack_driver='gelsd')
        for part, values in [('train', score[:split]), ('validation', score[split:])]:
            residual = values[:, 0]-values[:, 1:]@beta
            saved = record['information'][name][part]
            checks.close(residual, raw[name+'_effective_'+part], name+'/'+part+'/all_residuals')
            checks.close(beta, saved['coefficient'], name+'/'+part+'/beta')
            checks.close(np.mean(residual**2), saved['effective'], name+'/'+part+'/information')
            checks.close(np.mean(values[:, 0]**2), saved['raw'], name+'/'+part+'/raw_information')
            chunks = np.array_split(residual**2, min(8, len(values)))
            se = np.std([x.mean() for x in chunks], ddof=1)/np.sqrt(len(chunks))
            checks.close(se, saved['effective_batch_se'], name+'/'+part+'/se')
            checks.equal(rank, saved['nuisance_rank'], name+'/'+part+'/rank')
        effective[name] = np.mean(residual**2)
        pdp, pdp_weights = _pdp_law(config['n'], theta, config['pdp'])
        t = abs(nodes['nodes'][:, 0])**2
        angular = np.sum(pdp_weights[None, :]*(pdp[:, 0]*pdp[:, 1])[None, :]
            /(t[:, None]*pdp[:, 1]+(1-t[:, None])*pdp[:, 0])**2, axis=1)
        masses[name] = abs(float(nodes['weights']@angular)-1)
        checks.close(masses[name], record['quadrature_mass_errors'][name], name+'/mass_error')
    for index, step in enumerate(config['derivative_steps'][1:], start=1):
        component = read_npz(folder/f'fine__step_{index}_components.npz')
        replay = component_teacher(y[:8], component, np.exp(theta[3]))
        checks.close(replay['score'], raw[f'score_step_{index}'], f'refined_step{index}')
    for axis in range(4):
        for sign in ('plus', 'minus'):
            component = read_npz(folder/f'fine__fd_{axis}_{sign}_components.npz')
            replay = component_teacher(y[:8], component, np.exp(component['theta'][3]))
            checks.close(replay['logpdf'], raw[f'fd_{sign}_logpdf'][:, axis], f'FD/{axis}/{sign}')
    finite = (raw['fd_plus_logpdf']-raw['fd_minus_logpdf'])/(2*raw['finite_difference_step'])
    checks.close(finite, raw['finite_difference_score'], 'FD/direct_difference')
    checks.equal(node_count, config['new_quadrature_nodes'], 'refinement/active_node_count')
    checks.equal(record['new_observations'], 0, 'refinement/no_new_observations')
    checks.equal(record['reused_observations'], len(y), 'refinement/reused_observations')
    # Every convergence decision is independently derived from all saved scores.
    comparisons = []
    for index, (first, second) in enumerate(config['comparisons']):
        relative = np.sqrt(np.mean((raw[first+'_score']-raw[second+'_score'])**2, axis=0))/np.maximum(np.sqrt(np.mean(raw[second+'_score']**2, axis=0)), .01)
        maximum = np.max(abs(raw[first+'_logpdf']-raw[second+'_logpdf']))
        checks.close(relative, record['comparisons'][index]['score_relative_rms'], f'comparison{index}/score')
        checks.close(maximum, record['comparisons'][index]['logpdf_max'], f'comparison{index}/logpdf')
        comparisons.append(maximum<=config['logpdf_max_tolerance'] and max(relative)<=config['score_relative_rms_tolerance'])
    derivative_ok = True
    for index, step in enumerate(config['derivative_steps'][1:], start=1):
        refined = raw[f'score_step_{index}']
        relative = np.sqrt(np.mean((raw['fine_score'][:8]-refined)**2, axis=0))/np.maximum(np.sqrt(np.mean(refined**2, axis=0)), .01)
        checks.close(relative, record['derivative_steps'][index-1]['comparison']['score_relative_rms'], f'step{index}/relative')
        checks.close(0., record['derivative_steps'][index-1]['comparison']['logpdf_max'], f'step{index}/unchanged_logpdf')
        derivative_ok = derivative_ok and max(relative)<=config['derivative_relative_tolerance']
    fd_relative = np.sqrt(np.mean((finite-raw['fine_score'][:8])**2, axis=0))/np.maximum(np.sqrt(np.mean(finite**2, axis=0)), .01)
    effective_error = abs(effective['fine']-effective['independent'])/max(effective['independent'], .001)
    checks.close(fd_relative, record['finite_difference_relative_rms'], 'refinement/FD_relative')
    checks.close(effective_error, record['effective_rule_relative_error'], 'refinement/information_relative')
    gates = dict(node_rules=bool(all(comparisons)), derivative_steps=bool(derivative_ok),
                 direct_finite_difference=bool(max(fd_relative)<=config['derivative_relative_tolerance']),
                 quadrature_mass=bool(max(masses.values())<=config['mass_tolerance']),
                 effective_information=bool(effective_error<=config['effective_relative_tolerance']))
    checks.equal(gates, record['refinement_checks'], 'refinement/all_gates')
    checks.equal(all(gates.values()), record['refined'], 'refinement/decision')
    expected = 'numerically_positive_not_certified' if all(gates.values()) and effective['fine']>config['positive_evidence_standard_errors']*record['information']['fine']['validation']['effective_batch_se'] else 'unresolved_numerical_information'
    checks.equal(expected, record['classification'], 'refinement/classification')
    return dict(stage=folder.name, all_score_rows=len(y)*len(config['rules']), reused_observations=len(y),
                source_active_nodes=node_count, source_unused_initialization_nodes=config['unused_base_initialization_nodes'],
                audit_new_nodes=0, component_replay_rows_per_rule=8)


def audit_geometry(folder, checks):
    from experiments.afdm_higher_order_information.prior import small_system, geometry
    rows = read_json(folder/'geometry.json')
    for index, row in enumerate(rows):
        n = row['n']
        system = small_system(n)
        system.k_max_cap = min(2, (n-1)//2)
        geo = geometry(system, row['mu'], row['delta'])
        weights = geo['weights']
        active = np.flatnonzero(np.any(weights != 0, axis=1))
        width = 2*system.k_max_cap+1
        matrices = [system.gen_h_daft(weights[active, j], active//width, active%width-system.k_max_cap) for j in range(2)]
        gram = np.array([[np.vdot(a, b)/n for b in matrices] for a in matrices])
        eigenvalues, vectors = linalg.eigh(gram)
        checks.close(eigenvalues, row['eigenvalues'], f'geometry{index}/eigenvalues')
        checks.equal(active.tolist(), row['active_atoms'], f'geometry{index}/atoms')
        checks.equal(geo['physical_clip_mask'], row['physical_clipped'], f'geometry{index}/clip')
        for name in ('g0', 'g1'):
            rank = int(np.count_nonzero(eigenvalues>1e-12))
            leak = linalg.norm(geo[name]@vectors[:, eigenvalues<=1e-12])
            bounded = rank == 2 or leak<=1e-12
            stored = row[name+'_moments']
            checks.equal(rank, stored['rank'], f'geometry{index}/{name}/rank')
            checks.equal('undefined' if rank == 0 else 'finite' if bounded or rank>1 else 'infinite', stored['second'], f'geometry{index}/{name}/second')
            checks.equal('undefined' if rank == 0 else 'finite' if bounded or rank>2 else 'infinite', stored['fourth'], f'geometry{index}/{name}/fourth')
    for row in read_json(folder/'thresholds.json'):
        n = row['n']
        threshold = n/np.pi*np.arctan(.1*np.sin(np.pi/n)/(1+.1*np.cos(np.pi/n)))
        checks.close(threshold, row['delta_star'], f'N{n}/threshold')
    config = read_json(folder/'registration.json')['config']
    collisions = read_json(folder/'collision_covariance.json')
    for index, record in enumerate(collisions):
        for point in record['points']:
            q = point['delta']**2
            checks.close(np.array(point['even_change'])/(q*np.log(1/q)), point['even_over_qlogq'], f'collision{index}/ratio')
            checks.equal(point['same_as_collision'], point['discrete_branch'] == record['collision_discrete_branch'], f'collision{index}/branch')
        tail = record['points'][-config['coefficient_fit_last']:]
        qualified = all(point['same_as_collision'] for point in tail)
        checks.equal(qualified, record['branch_qualified'], f'collision{index}/fit_qualification')
        if qualified:
            x = np.array([np.log(1/point['delta']**2) for point in tail])
            values = np.array([np.array(point['even_change'])/point['delta']**2 for point in tail])
            coefficient = linalg.lstsq(np.column_stack([x, np.ones(len(x))]), values)[0][0]
            checks.close(coefficient, record['log_slope_coefficient'], f'collision{index}/coefficient_fit')
            predicted = np.array(record['predicted_qlogq_coefficient'])
            error = linalg.norm(coefficient-predicted)/max(linalg.norm(predicted), 1e-12)
            checks.close(error, record['log_slope_relative_error'], f'collision{index}/fit_error')
            checks.equal(error<config['qlogq_signal_tolerance'], record['log_slope_refined'], f'collision{index}/decision')
    return dict(stage=folder.name, dense_geometry_cases=len(rows), collision_tail_fits=len(collisions),
                covariance_scope='saved analytic covariance changes and asymptotic fits; no new covariance quadrature')


def physical_daft_matrix(n):
    k = np.arange(n)
    return (np.exp(2j*np.pi*.1/n**2*k*k)[:, None]*np.exp(-2j*np.pi*np.outer(k, k)/n)
            *np.exp(2j*np.pi*2.5/n*k*k)[None, :]/np.sqrt(n))


def audit_transfer(folder, checks):
    config = read_json(folder/'registration.json')['config']
    model = read_npz(resolve(config['model_path']))
    beta = model['efficient_beta']
    metadata, thresholds = read_json(folder/'observations.json'), read_json(folder/'thresholds.json')
    populations, count, seeds = {}, 0, []
    for row in metadata:
        raw = read_npz(folder/(row['key']+'.npz'))
        y, theta = raw['y_time'], raw['theta']
        n = y.shape[1]
        count += len(y)
        seeds.append(tuple(row['seed']))
        matrix = physical_daft_matrix(n)
        recovered = raw['y_daft']@matrix.conj()
        checks.close(recovered, y, row['key']+'/dense_inverse_daft')
        features = observed_polynomials(recovered[:, np.arange(4)*n//4])['phase']
        checks.close(features, raw['observed_features'], row['key']+'/features')
        prediction = predict(features, model)
        statistic = prediction[:, 0]-prediction[:, 1:]@beta
        checks.close(prediction, raw['predicted_scores'], row['key']+'/prediction')
        checks.close(statistic, raw['statistic'], row['key']+'/statistic')
        if row['gain_prior'] == 'gaussian':
            gain = raw['gain_gaussian_base']/np.sqrt(2)
        else:
            base = raw['gain_gaussian_base']*np.sqrt(raw['latent_pdp'])
            power = np.real(np.sum(base.conj()*(base@raw['gram'].T), axis=1))
            gain = base/np.sqrt(power[:, None])
        checks.close(gain, raw['gain'], row['key']+'/gain_pushforward')
        time_input = raw['symbols']@matrix.conj()
        replay = np.exp(theta[2]/2)*(gain@raw['response_atoms'].T)*time_input+np.exp(theta[3]/2)*raw['noise_base']
        checks.close(replay, y, row['key']+'/generation_replay')
        checks.equal(len(y), row['observations'], row['key']+'/denominator')
        populations[row['key']] = raw['statistic']
    checks.equal(len(set(seeds)), len(seeds), folder.name+'/independent_seed_partition')
    checks.equal(count, config['new_observations'], folder.name+'/all_observations')
    for n in config['dimensions']:
        values = populations[f'calibration_N{n}']
        rank = math.ceil((len(values)+1)*(1-config['alpha']))
        threshold = sorted(values)[rank-1]
        checks.close(threshold, thresholds['per_dimension'][str(n)], f'calibration_N{n}/threshold')
    for row in read_json(folder/'performance.json'):
        expected_threshold = thresholds['fixed_n4_threshold'] if row['calibration'] == 'frozen_N4_threshold' else thresholds['per_dimension'][str(row['n'])]
        checks.close(expected_threshold, row['threshold'], 'transfer/'+row['scenario']+'/fixed_threshold')
        for hypothesis, metric in [(0, 'false_alarm'), (1, 'power')]:
            values = populations[f"N{row['n']}_{row['scenario']}_H{hypothesis}"]
            successes = int(np.count_nonzero(values>expected_threshold))
            checks.equal(successes, row[metric]['successes'], row['scenario']+'/'+metric+'/count')
            checks.equal(len(values), row[metric]['count'], row['scenario']+'/'+metric+'/denominator')
            checks.close(successes/len(values), row[metric]['fraction'], row['scenario']+'/'+metric+'/fraction')
            checks.close(wilson_counts(successes, len(values)), row[metric]['wilson95'], row['scenario']+'/'+metric+'/interval')
    references = read_json(folder/'references.json')
    for scenario in config['scenarios']:
        reference = read_npz(folder/(scenario['name']+'_references.npz'))
        row = next(r for r in references if r['scenario'] == scenario['name'])
        words, word_mass = reference['input_words'], reference['input_mass']
        time_words = words@physical_daft_matrix(4).conj()
        centered = time_words-word_mass@time_words
        covariance = np.einsum('bi,bj,b->ij', centered, centered.conj(), word_mass)
        pseudo = np.einsum('bi,bj,b->ij', centered, centered, word_mass)
        eigenvalues = linalg.eigvalsh(covariance)
        checks.close(covariance, reference['input_time_covariance'], scenario['name']+'/input_covariance')
        checks.close(pseudo, reference['input_time_pseudocovariance'], scenario['name']+'/input_pseudocovariance')
        checks.close(eigenvalues, row['input_centered_covariance_eigenvalues'], scenario['name']+'/input_spectrum')
        checks.equal(int((eigenvalues>1e-10).sum()), row['input_centered_covariance_rank'], scenario['name']+'/input_rank')
        checks.close(linalg.norm(pseudo), row['input_pseudocovariance_norm'], scenario['name']+'/input_pseudocovariance_norm')
        for hypothesis in (0, 1):
            population = read_npz(folder/f'N4_{scenario["name"]}_H{hypothesis}.npz')
            theta = population['theta']
            if scenario['gain_prior'] == 'gaussian':
                for kind in ('original', 'canonical'):
                    y = reference['y'] if kind == 'original' else reference['canonical']
                    logpdf = gaussian_teacher(y, time_words, word_mass,
                        [theta[0]**2, theta[1], np.exp(theta[2]), np.exp(theta[3])], want_score=False)['logpdf']
                    checks.close(logpdf, reference[f'logpdf_{hypothesis}_{kind}'], scenario['name']+f'/exact/{hypothesis}/{kind}')
                continue
            pdp, pdp_mass = _pdp_law(4, theta, scenario['gain_prior'])
            for rule_index in range(len(config['reference_rules'])):
                nodes, mass = reference[f'nodes_rule{rule_index}'], reference[f'weights_rule{rule_index}']
                t = abs(nodes[:, 0])**2
                angular = np.sum(pdp_mass[None, :]*(pdp[:, 0]*pdp[:, 1])[None, :]
                    /(t[:, None]*pdp[:, 1]+(1-t[:, None])*pdp[:, 0])**2, axis=1)
                mass = mass*angular
                mass /= mass.sum()
                energy = np.real(np.sum(nodes.conj()*(nodes@population['gram'].T), axis=1))
                response = (nodes/np.sqrt(energy[:, None]))@population['response_atoms'].T
                means = (np.exp(theta[2]/2)*response[:, None, :]*time_words).reshape(-1, 4)
                component = dict(means=means, logweights=np.log(np.outer(mass, word_mass).ravel()))
                logpdf = component_teacher(reference['y'], component, np.exp(theta[3]))['logpdf']
                checks.close(logpdf, reference[f'logpdf_rule{rule_index}'][:, hypothesis], scenario['name']+f'/rule{rule_index}/H{hypothesis}')
                if rule_index == 1:
                    canonical = component_teacher(reference['canonical'], component, np.exp(theta[3]))['logpdf']
                    checks.close(canonical, reference[f'canonical_logpdf_{hypothesis}'], scenario['name']+f'/canonical/H{hypothesis}')
        if scenario['gain_prior'] != 'gaussian':
            errors = [reference[f'logpdf_rule{j}']-reference['logpdf_rule1'] for j in (0, 2)]
            maximum = max(np.max(abs(value)) for value in errors)
            rmse = max(np.sqrt(np.mean(value**2)) for value in errors)
            checks.close(maximum, row['max_logpdf_refinement_error'], scenario['name']+'/maximum_refinement')
            checks.close(rmse, row['logpdf_refinement_rmse'], scenario['name']+'/rmse_refinement')
            checks.equal(maximum<=config['reference_logpdf_max_error'] and rmse<=config['reference_logpdf_rmse'], row['refined'], scenario['name']+'/refined')
            identity = max(np.max(abs(reference[f'canonical_logpdf_{j}']-reference['logpdf_rule1'][:, j])) for j in (0, 1))
        else:
            identity = max(np.max(abs(reference[f'logpdf_{j}_original']-reference[f'logpdf_{j}_canonical'])) for j in (0, 1))
        checks.close(identity, row['canonical_logpdf_error'], scenario['name']+'/identity_error')
        checks.equal(identity<=config['identity_tolerance'], row['numerical_identity_pass'], scenario['name']+'/identity_pass')
    for row in read_json(folder/'representations.json'):
        n, size = row['n'], row['observations']
        checks.equal(row['dense_outer_bytes'], size*n*n*16, f'N{n}/dense_bytes')
        checks.equal(row['full_canonical_bytes'], size*n*16+size*8, f'N{n}/canonical_bytes')
        y = np.concatenate([read_npz(folder/f'N{n}_{row["scenario"]}_H{h}.npz')['y_time'] for h in (0, 1)])
        pivot = abs(y).argmax(axis=1)
        column = y*y[np.arange(size), pivot].conj()[:, None]
        z = column/abs(y[np.arange(size), pivot])[:, None]
        dense = y[:, :, None]*y[:, None, :].conj()
        error = np.max(abs(dense-z[:, :, None]*z[:, None, :].conj()))
        checks.close(error, row['max_dense_reconstruction_error'], f'N{n}/{row["scenario"]}/dense_identity')
        checks.equal(size*n, row['canonical_complex_scalings'], f'N{n}/canonical_scalings')
        checks.equal(size*n*n, row['dense_complex_products'], f'N{n}/outer_products')
    from experiments.afdm_higher_order_information.prior import small_system, geometry
    geometry_rows = read_json(folder/'geometry.json')
    for index, row in enumerate(geometry_rows):
        n = row['n']
        system = small_system(n)
        system.k_max_cap = min(2, (n-1)//2)
        geo = geometry(system, row['center'], row['delta'])
        active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
        width = 2*system.k_max_cap+1
        operators = [system.gen_h_daft(geo['weights'][active, j], active//width, active%width-system.k_max_cap) for j in range(2)]
        gram = np.array([[np.vdot(a, b)/n for b in operators] for a in operators])
        eigenvalues, vectors = linalg.eigh(gram)
        error = np.max(abs(gram-geo['gram']))
        checks.close(eigenvalues, row['gram_eigenvalues'], f'transfer_geometry{index}/eigenvalues')
        checks.close(error, row['dense_gram_error'], f'transfer_geometry{index}/dense_error')
        checks.equal(error<=config['identity_tolerance'], row['identity_pass'], f'transfer_geometry{index}/identity')
        checks.equal(active, row['active_atoms'], f'transfer_geometry{index}/active')
        rank = int((eigenvalues>1e-12).sum())
        bounded = rank>0 and (rank == 2 or linalg.norm(geo[row['generator']]@vectors[:, eigenvalues<=1e-12])<=1e-12)
        checks.equal(rank, row['moments']['rank'], f'transfer_geometry{index}/rank')
        for power, key in [(1, 'second'), (2, 'fourth')]:
            status = 'undefined' if rank == 0 else 'finite' if bounded or rank>power else 'infinite'
            checks.equal(status, row['moments'][key], f'transfer_geometry{index}/'+key)
    return dict(stage=folder.name, raw_observations=count, all_predictions_reconstructed=True,
                small_n_reference_cases=len(references), saved_quadrature_nodes_reused=True,
                dense_geometry_rows=len(geometry_rows))


def audit_cost_records(folder, checks):
    config = read_json(folder/'registration.json')['config']
    rows = read_json(folder/'stage_inventory.json')
    if folder.name in config['input_stages']:
        raise ValueError('cost stage recursively included its own incomplete attempt')
    checks.equal([row['stage'] for row in rows], sorted(config['input_stages']), 'cost/input_stages')
    for row in rows:
        registration = read_json(ARTIFACT/row['stage']/'registration.json')
        attempt = read_json(ARTIFACT/row['stage']/'attempt.json')
        checks.equal(row['status'], attempt['status'], row['stage']+'/cost_status')
        checks.equal(row['reserved_wall_seconds'], registration['wall_cap_seconds'], row['stage']+'/cost_reservation')
        checks.equal(row['reserved_observations'], registration['config']['new_observations'], row['stage']+'/cost_observations')
        checks.close(row['actual_wall_seconds'], attempt['wall_seconds'], row['stage']+'/cost_wall')
        checks.close(row['actual_cpu_seconds'], attempt['cpu_seconds'], row['stage']+'/cost_cpu')
        checks.equal(row['peak_rss_bytes'], attempt['peak_rss_bytes'], row['stage']+'/cost_peak_rss')
    documents = read_json(folder/'source_cost_documents.json')
    for name, value in documents.items():
        checks.equal(value, read_json(resolve(name)), name+'/copied_cost_source')
    corrections = []
    for name in config['input_stages']:
        stage = ARTIFACT/name
        registration = read_json(stage/'registration.json')['config']
        if (stage/'feature_cases.json').exists() and 'public_points' in registration:
            costs = read_json(stage/'costs.json')
            for row in costs:
                words = len(read_npz(stage/f"observations_{row['point']}.npz")['teacher_weights'])
                checks.equal(words, row['teacher_covariance_factorizations'], name+'/reported_cholesky_count')
                checks.equal(words*row['new_observations'], row['teacher_component_observation_pairs'], name+'/teacher_pairs')
                corrections.append(dict(stage=name, point=row['point'], cholesky_matrices=words, general_solve_matrices=words,
                    reported_field='teacher_covariance_factorizations counts Cholesky matrices only; general solve additionally factors each covariance'))
        elif (stage/'cases.json').exists() and 'q' in registration:
            costs = read_json(stage/'costs.json')
            words = len(read_npz(resolve(registration['score_model']))['teacher_weights'])
            data = read_npz(stage/'inference_observations.npz')
            matrices = len(data['candidates'])*words
            checks.equal(matrices, costs['reference']['covariance_factorizations'], name+'/reported_cholesky_count')
            checks.equal(matrices*len(data['y']), costs['reference']['component_observation_pairs'], name+'/teacher_pairs')
            corrections.append(dict(stage=name, cholesky_matrices=matrices, general_solve_matrices=matrices,
                reported_field='covariance_factorizations counts Cholesky matrices only; general solves are additional'))
    return dict(stage=folder.name, input_stages=len(rows), source_derived_operation_corrections=corrections,
                timing_scope='all original whole-stage wall/CPU already includes both operations; do not alter measured time')


def audit_stage(folder, checks):
    attempt = read_json(folder/'attempt.json')
    if attempt['status'] != 'complete':
        return dict(stage=folder.name, status=attempt['status'], scientific_replay='not claimed for failed partial output', retained=True)
    if (folder/'feature_cases.json').exists():
        return audit_features(folder, checks)
    if (folder/'information.json').exists():
        return audit_prior_information(folder, checks)
    if (folder/'refinement.json').exists() and (folder/'scores.npz').exists():
        return audit_prior_refinement(folder, checks)
    if (folder/'cases.json').exists() and (folder/'calibration.json').exists():
        return audit_inference(folder, checks)
    if (folder/'performance.json').exists():
        return audit_transfer(folder, checks)
    if (folder/'stage_inventory.json').exists():
        return audit_cost_records(folder, checks)
    if (folder/'collision_covariance.json').exists():
        return audit_geometry(folder, checks)
    raise ValueError(f'unrecognized completed scientific stage schema: {folder}')


def calculate(output, input_stages):
    stages = [ARTIFACT/name for name in input_stages]
    before = audit_hashes(stages)
    rejections = audit_admission_rejections()
    checks, reports = Checks(), []
    try:
        for stage in stages:
            report = audit_stage(stage, checks)
            reports.append(report)
            dump(output/(stage.name+'_audit.json'), dict(report=report, cumulative_checks=checks.result()))
        after = audit_hashes(stages)
        checks.equal(before, after, 'all_input_hashes_and_costs_unchanged')
        contract = read_json(MISSION/'run_contract.json')
        if before['total_reserved_observations']>contract['max_new_development_observations'] or before['total_reserved_wall']>contract['max_total_reserved_wall_seconds']:
            raise ValueError('recorded task allocation exceeds the immutable contract')
        checks.equal(before['counts']['protected'], 4307, 'protected_baseline_file_count')
        dump(output/'hash_audit.json', before)
        summary = dict(**checks.result(), stages=reports, input_hash_counts=before['counts'],
                       new_observations=0, new_scientific_nodes=0, new_scientific_rules=0,
                       reused_existing_nodes=True, input_costs=before,
                       pre_registration_rejections=rejections,
                       own_attempt_cost_separate=True,
                       scope='all feature/prediction/statistic rows; independent density integration scope declared per adapter')
        dump(output/'audit_summary.json', summary)
        if checks.failures:
            raise AssertionError(f'{len(checks.failures)} independent reconstruction checks failed')
        return summary
    finally:
        dump(output/'checks.json', checks.result())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    from experiments.afdm_higher_order_information.prior import frozen_components
    frozen_components()
    stages = sorted(path.parent.name for path in ARTIFACT.glob('*/registration.json'))
    if args.stage in stages:
        raise FileExistsError(ARTIFACT/args.stage)
    sources = [Path(__file__), Path(__file__).with_name('test_audit.py'),
               Path(__file__).with_name('AUDIT.md'), PROTECTED, ADMISSION_REJECTION]
    for name in stages:
        folder = ARTIFACT/name
        # The attempts bind every raw hash. Large NPZs are verified, not copied
        # into this audit's source snapshot a second time.
        sources.extend([folder/'registration.json', folder/'attempt.json'])
    import sys
    sources.extend(loaded_project_sources(sys.modules))
    config = dict(seed=[20261005, 104835, 50], new_observations=0, new_scientific_nodes=0,
                  input_stages=stages, protected_files=4307, tolerances=TOLERANCE,
                  prior_rows_per_case_rule=8, actual_inference_rows_per_condition_split=8,
                  actual_feature_teacher_all_rows=True, control_teacher_all_rows=True,
                  receiver_calls=0, decoder_calls=0, own_attempt_cost_separate=True)
    def callback(output):
        return calculate(output, stages)
    run(args.stage, config, sources, callback, wall_seconds=900)


if __name__ == '__main__':
    main()
