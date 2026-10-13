"""Independent saved-phase audit; no optimizer, observation inputs, FFT or RNG."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

REFERENCE_SHA256 = '9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03'
TRACE_SHAPES = dict(phases=(201, 64), gradients=(201, 64),
                    losses=(201,), mus=(201,), Qs=(201,))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_npz(path):
    with np.load(path, allow_pickle=False) as source:
        return {key: source[key] for key in source.files}


def close(actual, expected, label, atol=2e-11, rtol=1e-10):
    require(np.isfinite(actual).all() and np.isfinite(expected).all(), f'{label}: nonfinite')
    require(np.allclose(actual, expected, atol=atol, rtol=rtol), f'{label}: mismatch')
    return float(np.max(abs(np.asarray(actual)-expected)))


def direct_values(phase):
    """Explicit character and derivative sums, including the unlocked derivative 0."""
    phase = np.asarray(phase)
    require(phase.ndim == 1 and len(phase) >= 8 and len(phase) % 4 == 0,
            'phase shape: N>=8 divisible by four required')
    require(np.issubdtype(phase.dtype, np.floating) and np.isfinite(phase).all(),
            'finite real floating phases required')
    n = len(phase)
    j, k, d = np.arange(n), np.arange(1, n), np.arange(n//4)
    angle = (phase[None, :]-phase[(j[None, :]-k[:, None]) % n])[:, None, :]
    terms = np.exp(1j*(angle+8*np.pi*d[None, :, None]*j[None, None, :]/n))
    ambiguity = terms.sum(axis=2)/n
    squared = abs(ambiguity)**2
    total = float(np.sum(squared**8))
    require(math.isfinite(total) and total > 0, 'invalid high-order potential')
    gradient = np.empty(n)
    for coordinate in range(n):
        derivative = 1j*(terms[:, :, coordinate]-
                         terms[np.arange(n-1), :, (coordinate+k) % n])/n
        gradient[coordinate] = 2*total**(-7/8)*np.sum(
            squared**7*np.real(ambiguity.conj()*derivative))
    Q = float(squared[np.array([n//4, n//2, 3*n//4])-1, 0].sum())
    return dict(loss=total**(1/8), mu=float(abs(ambiguity).max()), Q=Q,
                gradient=gradient, energy=float(squared.sum()), potential=total)


def check_energy(values, n):
    """Restricted energy, exceptional shifts and high-order power-mean bounds."""
    q, energy, mu2 = values['Q'], values['energy'], values['mu']**2
    m = n//4
    error = close(energy, m-1+m*q, 'restricted energy identity')
    require(mu2+2e-11 >= (1+q)/(n+3), 'nonexceptional coherence lower bound')
    require(mu2+2e-11 >= q/3, 'exceptional coherence lower bound')
    require(mu2 <= values['loss']+2e-11, 'potential lower norm bound')
    require(values['loss'] <= ((n-1)*m)**(1/8)*mu2+2e-11, 'potential upper norm bound')
    lower = (m-1)*(1+q)**8/(n+3)**7+q**8/3**7
    require(values['potential']+2e-13 >= lower, 'high-order energy lower bound')
    close(float(values['gradient'].sum()), 0., 'global phase derivative', atol=2e-11)
    return error


def check_adam_updates(phases, gradients):
    """Replay only saved transitions, without evaluating or appending a candidate."""
    require(phases.shape == gradients.shape and phases.ndim == 2 and
            2 <= len(phases) <= 201 and phases.shape[1] > 0, 'Adam trace shape')
    require(np.isfinite(phases).all() and np.isfinite(gradients).all(), 'nonfinite Adam trace')
    require(np.all(phases[:, 0] == phases[0, 0]), 'changed locked phase coordinate')
    first, second = np.zeros(phases.shape[1]), np.zeros(phases.shape[1])
    max_error = 0.
    for step in range(1, len(phases)):
        gradient = gradients[step-1].copy()
        gradient[0] = 0.
        first = .9*first+.1*gradient
        second = .999*second+.001*gradient**2
        rate = .001+.049*(1+math.cos(math.pi*(step-1)/199))/2
        increment = rate*(first/(1-.9**step))/(np.sqrt(second/(1-.999**step))+1e-8)
        max_error = max(max_error, close(phases[step], phases[step-1]-increment,
                                        f'Adam step {step}', atol=2e-12, rtol=1e-12))
    return max_error


def check_checkpoint(phases, mus, code, selected):
    require(type(selected) is int and selected == int(np.argmin(mus)),
            'checkpoint must be earliest minimum mu')
    expected = np.exp(.25j*np.angle(np.exp(1j*phases[selected])))
    require(code.shape == expected.shape and np.isfinite(code).all(), 'selected code shape/finite')
    root_error = close(code, expected, 'principal fourth root', atol=1e-12, rtol=0.)
    close(code**4, np.exp(1j*phases[selected]), 'fourth power identity', atol=1e-12, rtol=0.)
    unit_error = float(np.max(abs(abs(code)-1)))
    qualified = bool(mus[selected] <= .9*mus[0] and unit_error <= 1e-12)
    return dict(design_qualified=qualified, max_unit_modulus_error=unit_error,
                max_principal_root_error=root_error)


def check_saved_hash(folder, name, attempt):
    matches = [digest for path, digest in attempt['artifact_sha256'].items()
               if Path(path).name == name and Path(path).parent.name == folder.name]
    require(len(matches) == 1 and matches[0] == file_hash(folder/name), f'artifact hash: {name}')


def calculate_audit(output, input_root):
    output, root = Path(output), Path(input_root)
    reference, design = root/'design_reference', root/'execution'/'D'
    historical_attempt = read_json(reference/'attempt.json')
    attempt = read_json(design/'attempt.json')
    require(historical_attempt['status'] == attempt['status'] == 'complete', 'incomplete source stage')
    require(attempt['exit_code'] == 0, 'D exit code')
    require(0 < attempt['wall_seconds'] <= 120 and
            0 < attempt['peak_rss_bytes'] <= 536870912, 'D resource contract')
    require(not (design/'partial_trace.npz').exists() and
            not (design/'partial_work_counts.json').exists(), 'partial design artifact')
    bound_names = ('design_trace.npz', 'code.npz', 'results.json',
                   'committed_project_sources.json', 'registration.json', 'environment.json')
    for name in bound_names:
        check_saved_hash(design, name, attempt)
    identity = read_json(design/'committed_project_sources.json')
    package = Path(__file__).resolve().parent
    for path in package.glob('*.py'):
        relative = str(path.relative_to(package.parents[1]))
        require(identity['project_python_sha256'][relative] == file_hash(path),
                f'D/current package source binding: {relative}')

    historical = read_json(reference/'results.json')
    historical_design = read_json(reference/'design.json')
    require(file_hash(reference/'codes.npz') == REFERENCE_SHA256 ==
            historical['code_file_sha256'] == historical_design['code_file_sha256'], 'old code hash binding')
    require(historical['design_phase_draws'] == 96 and historical['geometry_probes'] == 163280 and
            historical['new_observations'] == 0, 'historical counts')
    initial_code = read_npz(reference/'codes.npz')['n64_random']
    require(initial_code.shape == (64,), 'initial code shape')
    close(abs(initial_code), 1., 'initial unit modulus', atol=1e-12, rtol=0.)

    saved = read_json(design/'results.json')
    require(saved['reference_code_sha256'] == REFERENCE_SHA256, 'D reference binding')
    require(saved['code_sha256'] == file_hash(design/'code.npz') and
            saved['trace_sha256'] == file_hash(design/'design_trace.npz'), 'D output binding')
    trace = read_npz(design/'design_trace.npz')
    require(set(trace) == set(TRACE_SHAPES), 'trace keys')
    for key, shape in TRACE_SHAPES.items():
        require(trace[key].shape == shape and np.issubdtype(trace[key].dtype, np.floating) and
                np.isfinite(trace[key]).all(), f'trace {key}: shape/dtype/finite')
    close(trace['phases'][0], np.angle(initial_code**4), 'initial phase', atol=1e-14, rtol=0.)
    errors = dict(max_loss_error=0., max_mu_error=0., max_Q_error=0.,
                  max_gradient_error=0., max_energy_identity_error=0.)
    reconstructed_mus = []
    for index, phase in enumerate(trace['phases']):
        value = direct_values(phase)
        reconstructed_mus.append(value['mu'])
        for field, key in (('loss', 'losses'), ('mu', 'mus'), ('Q', 'Qs'), ('gradient', 'gradients')):
            error = close(trace[key][index], value[field], f'state {index}/{field}')
            errors[f'max_{field}_error'] = max(errors[f'max_{field}_error'], error)
        errors['max_energy_identity_error'] = max(errors['max_energy_identity_error'],
                                                  check_energy(value, 64))
    errors['max_Adam_phase_error'] = check_adam_updates(trace['phases'], trace['gradients'])
    codes = read_npz(design/'code.npz')
    require(set(codes) == {'v'}, 'selected code keys')
    selected = saved['selected_index']
    checkpoint = check_checkpoint(trace['phases'], trace['mus'], codes['v'], selected)
    require(selected == int(np.argmin(reconstructed_mus)), 'direct-sum minimum mu checkpoint')
    for field, value in (('initial_mu', trace['mus'][0]), ('selected_mu', trace['mus'][selected]),
                         ('selected_loss', trace['losses'][selected]), ('selected_Q', trace['Qs'][selected]),
                         ('max_unit_modulus_error', checkpoint['max_unit_modulus_error'])):
        close(saved[field], value, field, atol=1e-14, rtol=0.)
    require(type(saved['design_qualified']) is bool and
            saved['design_qualified'] == checkpoint['design_qualified'], 'design qualification')
    counts = dict(new_observations=0, geometry_probes=202608, objective_evaluations=201,
                  completed_objective_evaluations=201, acquisition_calls=0, receiver_calls=0,
                  decoder_calls=0, design_random_draws=0)
    for field, expected in counts.items():
        require(type(saved[field]) is int and saved[field] == expected, f'D count {field}')
    result = dict(new_observations=0, geometry_probes=0, acquisition_calls=0, receiver_calls=0,
                  decoder_calls=0, design_random_draws=0, audit_pass=True,
                  audited_states=201, audited_unlocked_derivatives=12864, audited_Adam_updates=200,
                  audited_saved_ambiguity_values=202608, source_counts=counts,
                  selected_index=selected, initial_mu=float(trace['mus'][0]),
                  selected_mu=float(trace['mus'][selected]), **checkpoint, checks=errors,
                  source_head=identity['head'],
                  design_reference=dict(code_sha256=REFERENCE_SHA256, reused=True,
                                        original_design_phase_draws=96, original_geometry_probes=163280,
                                        new_design_phase_draws=0, new_geometry_probes=0),
                  source_sha256={str(path.relative_to(root)): file_hash(path) for path in
                                 [reference/name for name in ('codes.npz', 'results.json', 'design.json', 'attempt.json')]+
                                 [design/name for name in (*bound_names, 'attempt.json')]},
                  scope='Saved deterministic design reconstruction only; zero new candidates, observations, acquisition calls or RNG. Audit consistency and mathematical qualification do not imply acquisition accuracy or global optimality.')
    with (output/'audit.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result
