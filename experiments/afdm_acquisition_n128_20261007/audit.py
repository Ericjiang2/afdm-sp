"""Independent SCREEN512 saved-output audit; no random draws or estimator calls."""
import json
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np

from .design_check import (array_hash, close, file_hash, load_verified_design,
                           read_json, read_npz, require, verify_stage_completion)

ARMS = ('quadratic', 'random')
METHODS = ('SCREEN512', 'FULL')
KEYS = tuple(f'{arm}_{method}' for arm in ARMS for method in METHODS)
ARRAYS = ('hypotheses', 'profile_scores', 'best_gain_indices', 'fourth_scores')


def check_source_identity(output, root, *, project_root=Path(__file__).resolve().parents[2]):
    """The recorder already checks HEAD; require the same source bytes in D/P/A."""
    folders = (Path(root)/'execution'/'D', Path(root)/'execution'/'P', Path(output))
    identities = [read_json(folder/'committed_project_sources.json') for folder in folders]
    require(identities[0] == identities[1] == identities[2], 'D/P/A committed source identity mismatch')
    identity = identities[0]
    require(set(identity) == {'head', 'project_python_sha256'} and
            isinstance(identity['head'], str) and len(identity['head']) == 40 and
            all(c in '0123456789abcdef' for c in identity['head']), 'source commit identity')
    hashes = identity['project_python_sha256']
    require(isinstance(hashes, dict) and len(hashes) > 0, 'empty Python source inventory')
    project_root = Path(project_root).resolve()
    for name, digest in hashes.items():
        path = (project_root/name).resolve()
        require(not Path(name).is_absolute() and path.is_relative_to(project_root) and path.suffix == '.py',
                'invalid Python source path')
        require(file_hash(path) == digest, f'current Python source mismatch: {name}')
    return identity


def direct_transforms(n):
    j = np.arange(n)
    f = np.exp(-2j*np.pi*j[:, None]*j[None, :]/n)/np.sqrt(n)
    r = np.exp(-5j*np.pi*j*j/n)
    shifts = (j[None, :]-j[:, None]) % n
    delay_match = np.exp(8j*np.pi*j[:, None]*np.arange(n//4)[None, :]/n)
    return f, r, shifts, delay_match


def direct_mixture(x, v, sigma2, hypothesis):
    """96 saved-grid profiles from four explicit Gaussian components."""
    x, v = np.asarray(x), np.asarray(v)
    require(v.ndim == 1 and len(v) >= 4 and len(v) % 4 == 0, 'mixture code shape')
    n = len(v)
    require(x.ndim == 2 and x.shape[0] > 0 and x.shape[1] == n, 'mixture observation shape')
    require(np.isfinite(x).all() and np.isfinite(v).all(), 'mixture nonfinite')
    require(np.isscalar(sigma2) and np.isfinite(sigma2) and sigma2 > 0, 'mixture noise variance')
    require(isinstance(hypothesis, (int, np.integer)) and 0 <= hypothesis < n*(n//4),
            'mixture hypothesis')
    a, delay = divmod(int(hypothesis), n//4)
    shifted = (np.arange(n)-a) % n
    z = (x*np.conj(v[shifted])*np.exp(2j*np.pi*delay*shifted/n)).ravel()
    symbols = np.array([1+1j, 1-1j, -1+1j, -1-1j])/np.sqrt(2)
    gains = (np.array([.75, 1., 1.25])[:, None]*np.exp(1j*np.arange(32)*np.pi/64)).ravel()
    logterms = -np.abs(z[None, :, None]-gains[:, None, None]*symbols)**2/sigma2
    peak = logterms.max(axis=2)
    # Restore only the common energy constant omitted in saved profile scores.
    return (peak+np.log(np.exp(logterms-peak[:, :, None]).sum(axis=2))-np.log(4)).sum(axis=1)+np.sum(abs(z)**2)/sigma2


def check_selection(answer, arrays, key, n):
    """Select from saved grids independently, including exact deterministic ties."""
    method = key.split('_')[1]
    values = {name: arrays[f'{key}_{name}'] for name in ARRAYS}
    hypotheses, scores, gains, fourth = (values[name] for name in ARRAYS)
    for name, value in values.items():
        require(np.isfinite(value).all(), f'{key}/{name}: nonfinite')
    require(np.issubdtype(hypotheses.dtype, np.integer), 'hypothesis indices')
    require(not np.iscomplexobj(scores) and not np.iscomplexobj(fourth), 'real score arrays')
    size = n*(n//4)
    require(method in METHODS, 'unknown audited method')
    if method == 'FULL':
        require(fourth.shape == (0,), 'FULL fourth scores must be empty')
        expected = np.arange(size)
    else:
        require(fourth.shape == (n, n//4), 'screen fourth shape')
        expected = np.sort(np.argsort(-fourth.ravel(), kind='stable')[:512])
    require(np.array_equal(hypotheses, expected), f'{key}: hypothesis order/shortlist')
    require(scores.shape == gains.shape == hypotheses.shape, 'profile shape')
    require(np.issubdtype(gains.dtype, np.integer) and np.all((gains >= 0) & (gains < 96)), 'gain indices')
    winner = int(np.argmax(scores))
    selected, objective = int(hypotheses[winner]), float(scores[winner])
    ties = int(np.count_nonzero(scores == objective))
    gi = int(gains[winner])
    require(answer['gain_index'] == gi, 'selected gain index')
    magnitude = (.75, 1., 1.25)[gi//32]
    physical = magnitude*np.exp(1j*((gi % 32)*np.pi/64+5*np.pi*(selected % (n//4))**2/n))
    close(answer['physical_gain_mod_C4'], [physical.real, physical.imag], 'physical gain', 1e-12)
    count = len(hypotheses)
    a, delay = divmod(selected, n//4)
    require((answer['a'], answer['delay'], answer['cfo']) == (a, delay, (a-5*delay) % n), 'selected parameters')
    require(answer['objective'] == objective and answer['exact_ties'] == ties, 'selected objective/ties')
    require(answer['likelihood_hypotheses'] == count and answer['gain_grid_evaluations'] == 96*count, 'likelihood work counts')
    require(math.isfinite(answer['elapsed_seconds']) and answer['elapsed_seconds'] > 0, 'elapsed time')


def cp_upper(x, n=256):
    """Invert the binomial lower tail directly, independently of beta.ppf."""
    require(type(x) is int and type(n) is int and n > 0 and 0 <= x <= n, 'invalid binomial count')
    if x == n:
        return 1.
    logcomb = [math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1) for k in range(x+1)]
    low, high = 0., 1.
    for _ in range(64):
        p = (low+high)/2
        logs = [c+k*math.log(p)+(n-k)*math.log1p(-p) for k, c in enumerate(logcomb)]
        peak = max(logs)
        tail = math.exp(peak)*math.fsum(math.exp(t-peak) for t in logs)
        if tail > .05:
            low = p
        else:
            high = p
    return (low+high)/2


def independent_summary(records):
    require(len(records) == 256 and all((r['N'], r['T'], r['snr_db']) == (128, 2, 5)
                                        for r in records), 'incomplete or foreign SCREEN512 cell')
    for row in records:
        require(set(row['estimates']) == set(KEYS) and set(row['dominance']) == set(ARMS),
                'summary method inventory')
        require(all(type(v) is bool for v in row['dominance'].values()), 'summary dominance type')
        for answer in row['estimates'].values():
            require(type(answer['error']) is bool, 'summary error type')
            require(math.isfinite(answer['elapsed_seconds']) and answer['elapsed_seconds'] > 0,
                    'summary elapsed time')
    errors = {key: sum(r['estimates'][key]['error'] for r in records) for key in KEYS}
    totals = {key: sum(r['estimates'][key]['elapsed_seconds'] for r in records) for key in KEYS}
    differences = [int(r['estimates']['quadratic_SCREEN512']['error'])-
                   int(r['estimates']['random_SCREEN512']['error']) for r in records]
    mean = sum(differences)/256
    variance = sum((d-mean)**2 for d in differences)/255
    se = math.sqrt(variance/256)
    radius = NormalDist().inv_cdf(.975)*se
    interval = [mean-radius, mean+radius]
    bad = sum(r['estimates']['random_SCREEN512']['error'] and
              not r['estimates']['random_FULL']['error'] for r in records)
    reverse = sum(r['estimates']['random_FULL']['error'] and
                  not r['estimates']['random_SCREEN512']['error'] for r in records)
    upper = cp_upper(bad)
    require((upper <= .02) == (bad <= 1), 'CP upper and frozen integer gate disagree')
    ratio = totals['random_FULL']/totals['random_SCREEN512']
    cell = dict(N=128, snr_db=5, groups=256, error_counts=errors,
                elapsed_seconds=totals, random_speed_ratio=ratio)
    gates = dict(dominance=all(all(r['dominance'].values()) for r in records),
                 complete_time_ratio=ratio >= 3, noninferiority=upper <= .02,
                 code_improvement=mean >= .10 and interval[0] > 0,
                 each_cell_usable=errors['random_SCREEN512'] <= 64)
    return dict(cells=[cell], paired_improvement=dict(mean=mean, standard_error=se, interval=interval),
                total_elapsed_seconds=totals, random_speed_ratio=ratio, mean_cell_speed_ratio=ratio,
                bad_discordance=bad, reverse_discordance=reverse, binomial_reference_cp_upper=upper,
                gates=gates, positive_pilot_signal=all(gates.values()))


def compare_summary(actual, saved):
    """Compare independent numerical fields, leaving metadata labels alone."""
    for key, value in actual.items():
        require(key in saved, f'missing summary field {key}')
        other = saved[key]
        if isinstance(value, dict):
            compare_summary(value, other)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            require(len(value) == len(other), 'summary cell count')
            for a, b in zip(value, other):
                compare_summary(a, b)
        elif isinstance(value, (list, float)):
            close(value, other, f'summary {key}', 1e-12)
        else:
            require(value == other, f'summary {key}')


def calculate_audit(output, input_root):
    output, root = Path(output), Path(input_root)
    design, pilot = root/'execution'/'D', root/'execution'/'P'
    codes, dr = load_verified_design(design)
    verify_stage_completion(pilot, ('records.json', 'results.json', 'registration.json',
                                    'committed_project_sources.json'))
    source_identity = check_source_identity(output, root)
    pr = read_json(pilot/'results.json')
    require(dr['code_file_sha256'] == pr['waveform_design_sha256'], 'pilot design file binding')
    require(dr['design_audit_sha256'] == pr['design_audit_sha256'], 'pilot design audit binding')
    require(not (pilot/'records.json.gz').exists(), 'duplicate record representation')
    require(not (pilot/'partial_work_counts.json').exists(), 'partial pilot artifact')
    records = read_json(pilot/'records.json')
    require(len(records) == 256 and [r['group'] for r in records] == list(range(256)), 'complete unique group sequence')
    require(sorted(p.name for p in (pilot/'groups').iterdir()) == [f'{i:04d}' for i in range(256)], 'group folder inventory')
    transforms = direct_transforms(128)
    max_y = max_fourth = max_spot = 0.
    calls = likelihood = gain_evaluations = spot_checks = 0
    for group, row in enumerate(records):
        n, snr = 128, 5
        require((row['N'], row['T'], row['snr_db'], row['within_cell']) == (n, 2, snr, group), 'frozen group order')
        folder = pilot/'groups'/f'{group:04d}'
        require(read_json(folder/'record.json') == row, 'per-group record mismatch')
        require(set(p.name for p in folder.iterdir()) == {'raw.npz', 'estimates.npz', 'record.json'}, 'partial/unknown group artifact')
        raw_path, estimates_path = folder/'raw.npz', folder/'estimates.npz'
        require(row['raw_path'] == f'groups/{group:04d}/raw.npz' and row['estimates_path'] == f'groups/{group:04d}/estimates.npz', 'group paths')
        require(file_hash(raw_path) == row['raw_sha256'] and file_hash(estimates_path) == row['estimates_sha256'], 'group file hash')
        raw, arrays = read_npz(raw_path), read_npz(estimates_path)
        expected_raw = {'states', 'standard_noise', 'gain', 'delay', 'cfo', 'sigma2'} | {f'Y_{arm}' for arm in ARMS}
        require(set(raw) == set(row['array_sha256']) == expected_raw, 'raw keys')
        require(set(arrays) == {f'{key}_{name}' for key in KEYS for name in ARRAYS}, 'estimate array keys')
        for key, value in raw.items():
            require(array_hash(value) == row['array_sha256'][key], f'raw array hash {key}')
            require(np.isfinite(value).all(), f'raw nonfinite {key}')
        states, noise = raw['states'], raw['standard_noise']
        require(states.shape == noise.shape == (2, n), 'source shape')
        require(np.issubdtype(states.dtype, np.integer) and np.all((states >= 0) & (states < 4)), 'QPSK states')
        for field in ('delay', 'cfo', 'sigma2'):
            require(raw[field].shape == () and raw[field].item() == row[field], f'raw truth {field}')
        require(raw['gain'].shape == (), 'gain scalar')
        gain = complex(raw['gain'])
        close([gain.real, gain.imag], row['gain'], 'record gain', 1e-14)
        require(.75 <= abs(gain) <= 1.25, 'gain range')
        delay, cfo = row['delay'], row['cfo']
        require(isinstance(delay, int) and 0 <= delay < n//4 and isinstance(cfo, int) and 0 <= cfo < n, 'truth range')
        require(row['sigma2'] == 10**(-snr/10), 'noise variance')
        f, r, shifts, delay_match = transforms
        symbols = np.array([1+1j, 1-1j, -1+1j, -1-1j])[states]/np.sqrt(2)
        clock = np.arange(2)[:, None]*(n+n//4)+np.arange(n)[None, :]
        require(set(row['estimates']) == set(KEYS) and set(row['dominance']) == set(ARMS), 'method inventory')
        offset = group % len(KEYS)
        require(row['estimator_order'] == list(KEYS[offset:]+KEYS[:offset]), 'timing rotation')
        for arm in ARMS:
            v = codes[f'n{n}_{arm}']
            signal = ((symbols*v)@f.conj())*r
            expected_y = gain*np.exp(2j*np.pi*cfo*clock/n)*signal[:, (np.arange(n)-delay) % n]+np.sqrt(row['sigma2']/2)*noise
            y = raw[f'Y_{arm}']
            require(y.shape == (2, n), 'Y shape')
            close(y, expected_y, 'raw reconstruction', 1e-10)
            max_y = max(max_y, float(np.max(abs(y-expected_y))))
            x = (y*r.conj())@f
            direct_fourth = abs((np.mean(x**4, axis=0)[None, :]*np.conj(v[shifts]**4))@delay_match)
            for method in METHODS:
                key = f'{arm}_{method}'
                answer = row['estimates'][key]
                check_selection(answer, arrays, key, n)
                require(answer['Y_sha256'] == array_hash(y), 'estimator observation hash')
                require(type(answer['error']) is bool and answer['error'] == (answer['delay'] != delay or answer['cfo'] != cfo), 'truth error scoring')
                calls += 1
                likelihood += answer['likelihood_hypotheses']
                gain_evaluations += answer['gain_grid_evaluations']
                if method != 'FULL':
                    saved = arrays[f'{key}_fourth_scores']
                    close(saved, direct_fourth, 'direct fourth scores', 1e-8)
                    max_fourth = max(max_fourth, float(np.max(abs(saved-direct_fourth))))
            full, screen = (row['estimates'][f'{arm}_{m}'] for m in ('FULL', 'SCREEN512'))
            dominance = full['objective'] >= screen['objective']-1e-8-1e-10*abs(screen['objective'])
            require(row['dominance'][arm] == dominance, 'record dominance')
            h = arrays[f'{arm}_SCREEN512_hypotheses']
            close(arrays[f'{arm}_SCREEN512_profile_scores'], arrays[f'{arm}_FULL_profile_scores'][h], 'shared likelihood scores')
            require(np.array_equal(arrays[f'{arm}_SCREEN512_best_gain_indices'], arrays[f'{arm}_FULL_best_gain_indices'][h]), 'shared likelihood gains')
            if group in (0, 64, 128, 192):
                selected = full['a']*(n//4)+full['delay']
                for candidate in (selected, (selected+1) % (n*n//4)):
                    profile = direct_mixture(x, v, row['sigma2'], candidate)
                    spot_checks += 1
                    stored = arrays[f'{arm}_FULL_profile_scores'][candidate]
                    close(float(profile.max()), stored, 'explicit mixture spot', 1e-7)
                    require(int(np.argmax(profile)) == arrays[f'{arm}_FULL_best_gain_indices'][candidate], 'spot best gain')
                    max_spot = max(max_spot, abs(float(profile.max())-stored))
    expected_counts = dict(paired_groups=256, waveform_datasets=512, new_observations=1024,
                           complex_scalars=131072, acquisition_calls=1024, geometry_probes=0,
                           receiver_calls=0, decoder_calls=0, generation_ifft_vectors=1024,
                           attempted_observation_vectors=1024, completed_acquisition_calls=1024)
    require(calls == 1024 and likelihood == 2359296 and gain_evaluations == 226492416, 'reconstructed estimator work')
    require(spot_checks == 16, 'mixture spot count')
    for key, value in expected_counts.items():
        require(pr[key] == value, f'pilot count {key}')
    summary = independent_summary(records)
    compare_summary(summary, pr)
    result = dict(new_observations=0, geometry_probes=0, design_phase_draws=0, acquisition_calls=0, receiver_calls=0,
                  decoder_calls=0, audit_pass=True, audited_groups=256, audited_acquisition_calls=calls,
                  audited_likelihood_hypotheses=likelihood, audited_gain_grid_evaluations=gain_evaluations,
                  source_counts=expected_counts, summary=summary, committed_source_identity=source_identity,
                  design_reference=dict(code_file_sha256=dr['code_file_sha256'],
                                        design_audit_sha256=dr['design_audit_sha256'],
                                        design_phase_draws=128, design_geometry_probes=1056640,
                                        new_design_phase_draws=0, new_geometry_probes=0),
                  source_sha256={str(p.relative_to(root)): file_hash(p) for p in
                                 (design/'codes.npz', design/'design.json', design/'results.json',
                                  design/'attempt.json', design/'design_audit.json',
                                  design/'committed_project_sources.json', pilot/'committed_project_sources.json',
                                  output/'committed_project_sources.json',
                                  pilot/'records.json', pilot/'results.json', pilot/'attempt.json')},
                  checks=dict(max_Y_abs_error=max_y, max_fourth_score_abs_error=max_fourth,
                              mixture_spot_groups=[0, 64, 128, 192], mixture_spot_candidates=spot_checks,
                              max_mixture_spot_abs_error=max_spot),
                  scope='Independent 256-group N128/T2/SNR5 SCREEN512 cohort; saved outputs only, zero new estimator calls, observations, geometry probes or RNG. D independently checked all 130 objectives before P; A checks its file/array hashes and receipt without repeating geometry. All Y and fourth scores checked; explicit 96-gain mixture check limited to 16 candidates, not full independent likelihood recomputation.')
    with (output/'audit.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result
