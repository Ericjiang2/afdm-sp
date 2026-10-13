"""Independent shortburst saved-output audit; no random draws or estimator calls."""
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np

ARMS = ('current', 'quadratic', 'random')
METHODS = ('FOURTH', 'SCREEN32', 'FULL')
KEYS = tuple(f'{arm}_{method}' for arm in ARMS for method in METHODS)
ARRAYS = ('hypotheses', 'profile_scores', 'best_gain_indices', 'fourth_scores')
DESIGN_SHA256 = '9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_hash(value):
    value = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(value.dtype).encode())
    h.update(json.dumps(list(value.shape)).encode())
    h.update(value.tobytes())
    return h.hexdigest()


def close(actual, expected, label, atol=1e-8):
    require(np.all(np.isfinite(actual)), f'{label}: nonfinite')
    require(np.allclose(actual, expected, atol=atol, rtol=1e-10), f'{label}: mismatch')


def read_json(path):
    return json.loads(Path(path).read_text())


def read_npz(path):
    with np.load(path, allow_pickle=False) as source:
        return {k: source[k] for k in source.files}


def direct_transforms(n):
    j = np.arange(n)
    f = np.exp(-2j*np.pi*j[:, None]*j[None, :]/n)/np.sqrt(n)
    r = np.exp(-5j*np.pi*j*j/n)
    shifts = (j[None, :]-j[:, None]) % n
    delay_match = np.exp(8j*np.pi*j[:, None]*np.arange(n//4)[None, :]/n)
    return f, r, shifts, delay_match


def direct_mixture(x, v, sigma2, hypothesis):
    """48 saved-grid profiles from four explicit Gaussian components."""
    n = len(v)
    a, delay = divmod(int(hypothesis), n//4)
    shifted = (np.arange(n)-a) % n
    z = (x*np.conj(v[shifted])*np.exp(2j*np.pi*delay*shifted/n)).ravel()
    symbols = np.array([1+1j, 1-1j, -1+1j, -1-1j])/np.sqrt(2)
    gains = (np.array([.75, 1., 1.25])[:, None]*np.exp(1j*np.arange(16)*np.pi/32)).ravel()
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
    size = n*(n//4)
    if method == 'FOURTH':
        require(all(v.size == 0 for v in (hypotheses, scores, gains)), 'FOURTH likelihood arrays not empty')
        require(fourth.shape == (n, n//4), 'fourth shape')
        selected = int(np.argmax(fourth))
        objective = float(fourth.ravel()[selected])
        ties = int(np.count_nonzero(fourth == objective))
        require(answer['gain_index'] is None and answer['physical_gain_mod_C4'] is None, 'FOURTH gain must be unavailable')
        count = 0
    else:
        if method == 'FULL':
            require(fourth.size == 0, 'FULL fourth scores must be empty')
            expected = np.arange(size)
        else:
            require(fourth.shape == (n, n//4), 'screen fourth shape')
            expected = np.sort(np.argsort(-fourth.ravel(), kind='stable')[:32])
        require(np.array_equal(hypotheses, expected), f'{key}: hypothesis order/shortlist')
        require(scores.shape == gains.shape == hypotheses.shape, 'profile shape')
        require(np.issubdtype(gains.dtype, np.integer) and np.all((gains >= 0) & (gains < 48)), 'gain indices')
        winner = int(np.argmax(scores))
        selected, objective = int(hypotheses[winner]), float(scores[winner])
        ties = int(np.count_nonzero(scores == objective))
        gi = int(gains[winner])
        require(answer['gain_index'] == gi, 'selected gain index')
        magnitude = (.75, 1., 1.25)[gi//16]
        physical = magnitude*np.exp(1j*((gi % 16)*np.pi/32+5*np.pi*(selected % (n//4))**2/n))
        close(answer['physical_gain_mod_C4'], [physical.real, physical.imag], 'physical gain', 1e-12)
        count = len(hypotheses)
    a, delay = divmod(selected, n//4)
    require((answer['a'], answer['delay'], answer['cfo']) == (a, delay, (a-5*delay) % n), 'selected parameters')
    require(answer['objective'] == objective and answer['exact_ties'] == ties, 'selected objective/ties')
    require(answer['likelihood_hypotheses'] == count and answer['gain_grid_evaluations'] == 48*count, 'likelihood work counts')
    require(math.isfinite(answer['elapsed_seconds']) and answer['elapsed_seconds'] > 0, 'elapsed time')


def independent_summary(records):
    require(len(records) == 256 and all((r['N'], r['T'], r['snr_db']) == (64, 2, 5)
                                       for r in records), 'incomplete or foreign shortburst cell')
    errors = {key: sum(r['estimates'][key]['error'] for r in records) for key in KEYS}
    totals = {key: sum(r['estimates'][key]['elapsed_seconds'] for r in records) for key in KEYS}
    differences = [int(r['estimates']['quadratic_SCREEN32']['error'])-
                   int(r['estimates']['random_SCREEN32']['error']) for r in records]
    mean = sum(differences)/256
    variance = sum((d-mean)**2 for d in differences)/255
    se = math.sqrt(variance/256)
    radius = NormalDist().inv_cdf(.975)*se
    interval = [mean-radius, mean+radius]
    bad = sum(r['estimates']['random_SCREEN32']['error'] and
              not r['estimates']['random_FULL']['error'] for r in records)
    reverse = sum(r['estimates']['random_FULL']['error'] and
                  not r['estimates']['random_SCREEN32']['error'] for r in records)
    ratio = totals['random_FULL']/totals['random_SCREEN32']
    cell = dict(N=64, snr_db=5, groups=256, error_counts=errors,
                elapsed_seconds=totals, random_speed_ratio=ratio)
    gates = dict(dominance=all(all(r['dominance'].values()) for r in records),
                 complete_time_ratio=ratio >= 3, noninferiority=bad <= 1,
                 code_improvement=mean >= .10 and interval[0] > 0,
                 each_cell_usable=errors['random_SCREEN32'] <= 64)
    return dict(cells=[cell], paired_improvement=dict(mean=mean, standard_error=se, interval=interval),
                total_elapsed_seconds=totals, random_speed_ratio=ratio, mean_cell_speed_ratio=ratio,
                bad_discordance=bad, reverse_discordance=reverse, gates=gates,
                positive_pilot_signal=all(gates.values()))


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
    design, pilot = root/'design_reference', root/'execution'/'P'
    for folder in (design, pilot):
        require(read_json(folder/'attempt.json')['status'] == 'complete', f'incomplete source {folder.name}')
    dr, pr = read_json(design/'results.json'), read_json(pilot/'results.json')
    design_record = read_json(design/'design.json')
    code_hash = file_hash(design/'codes.npz')
    require(code_hash == DESIGN_SHA256 == dr['code_file_sha256'] == design_record['code_file_sha256'] == pr['waveform_design_sha256'], 'design file binding')
    codes = read_npz(design/'codes.npz')
    require(set(codes) == set(dr['array_sha256']) == set(design_record['array_sha256']), 'design array inventory')
    require(dr['designs'] == design_record['designs'], 'design record mismatch')
    for key, value in codes.items():
        require(array_hash(value) == dr['array_sha256'][key] == design_record['array_sha256'][key], f'design array hash {key}')
    for n in (32, 64):
        candidates = codes[f'n{n}_candidate_c2']
        objectives = codes[f'n{n}_candidate_objectives']
        expected = np.r_[1/(10*n*n), (np.arange(128)+np.sqrt(2))/(4*129)]
        close(candidates, expected, 'quadratic candidates', 1e-15)
        require(objectives.shape == (129,) and np.isfinite(objectives).all(), 'candidate objectives')
        choice = int(np.argmin(objectives))
        rows = [r for r in dr['designs'] if r['N'] == n]
        require(len(rows) == 1 and rows[0]['quadratic_index'] == choice, 'design selection')
        row = rows[0]
        require(row['quadratic_c2'] == candidates[choice] and row['quadratic_objective'] == objectives[choice], 'selected design score')
        require(row['current_objective'] == objectives[0] and row['random_objective'] == codes[f'n{n}_random_objective'], 'design score fields')
        for arm, idx in (('current', 0), ('quadratic', choice)):
            close(codes[f'n{n}_{arm}'], np.exp(-2j*np.pi*candidates[idx]*np.arange(n)**2), 'quadratic code', 1e-12)
        for arm in ARMS:
            require(codes[f'n{n}_{arm}'].shape == (n,), 'code shape')
            close(abs(codes[f'n{n}_{arm}']), 1., 'unit code', 1e-12)
    require(dr['design_phase_draws'] == 96 and dr['new_observations'] == 0 and dr['geometry_probes'] == 163280, 'design counts')
    require(not (pilot/'records.json.gz').exists(), 'duplicate record representation')
    require(not (pilot/'partial_work_counts.json').exists(), 'partial pilot artifact')
    records = read_json(pilot/'records.json')
    require(len(records) == 256 and [r['group'] for r in records] == list(range(256)), 'complete unique group sequence')
    require(sorted(p.name for p in (pilot/'groups').iterdir()) == [f'{i:04d}' for i in range(256)], 'group folder inventory')
    transforms = direct_transforms(64)
    max_y = max_fourth = max_spot = 0.
    calls = likelihood = gain_evaluations = 0
    for group, row in enumerate(records):
        n, snr = 64, 5
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
        offset = group % 9
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
            full, screen = (row['estimates'][f'{arm}_{m}'] for m in ('FULL', 'SCREEN32'))
            dominance = full['objective'] >= screen['objective']-1e-8-1e-10*abs(screen['objective'])
            require(row['dominance'][arm] == dominance, 'record dominance')
            h = arrays[f'{arm}_SCREEN32_hypotheses']
            close(arrays[f'{arm}_SCREEN32_profile_scores'], arrays[f'{arm}_FULL_profile_scores'][h], 'shared likelihood scores')
            require(np.array_equal(arrays[f'{arm}_SCREEN32_best_gain_indices'], arrays[f'{arm}_FULL_best_gain_indices'][h]), 'shared likelihood gains')
            if group % 64 == 0:
                selected = full['a']*(n//4)+full['delay']
                for candidate in (selected, (selected+1) % (n*n//4)):
                    profile = direct_mixture(x, v, row['sigma2'], candidate)
                    stored = arrays[f'{arm}_FULL_profile_scores'][candidate]
                    close(float(profile.max()), stored, 'explicit mixture spot', 1e-7)
                    require(int(np.argmax(profile)) == arrays[f'{arm}_FULL_best_gain_indices'][candidate], 'spot best gain')
                    max_spot = max(max_spot, abs(float(profile.max())-stored))
    expected_counts = dict(paired_groups=256, waveform_datasets=768, new_observations=1536,
                           complex_scalars=98304, acquisition_calls=2304, geometry_probes=0,
                           receiver_calls=0, decoder_calls=0, generation_ifft_vectors=1536,
                           attempted_observation_vectors=1536, completed_acquisition_calls=2304)
    require(calls == 2304 and likelihood == 811008 and gain_evaluations == 38928384, 'reconstructed estimator work')
    for key, value in expected_counts.items():
        require(pr[key] == value, f'pilot count {key}')
    summary = independent_summary(records)
    compare_summary(summary, pr)
    result = dict(new_observations=0, geometry_probes=0, acquisition_calls=0, receiver_calls=0,
                  decoder_calls=0, audit_pass=True, audited_groups=256, audited_acquisition_calls=calls,
                  audited_likelihood_hypotheses=likelihood, audited_gain_grid_evaluations=gain_evaluations,
                  source_counts=expected_counts, summary=summary,
                  design_reference=dict(code_file_sha256=DESIGN_SHA256, reused=True,
                                        original_design_phase_draws=96, original_geometry_probes=163280,
                                        new_design_phase_draws=0, new_geometry_probes=0),
                  source_sha256={str(p.relative_to(root)): file_hash(p) for p in
                                 (design/'codes.npz', design/'design.json', design/'results.json',
                                  design/'attempt.json', pilot/'records.json', pilot/'results.json', pilot/'attempt.json')},
                  checks=dict(max_Y_abs_error=max_y, max_fourth_score_abs_error=max_fourth,
                              mixture_spot_groups=[0, 64, 128, 192], mixture_spot_candidates=24,
                              max_mixture_spot_abs_error=max_spot),
                  scope='Independent N64/T2/SNR5 shortburst cohort; saved outputs only, zero new estimator calls, observations or RNG. design_reference is the unchanged old D artifact, not a new design stage; its 96 draws and 163280 geometry probes are historical. All Y and fourth scores checked; likelihood mixture spot check limited to 24 candidates.')
    with (output/'audit.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result
