"""Untruncated CPP propagation for the separately registered G1 development unit."""
from __future__ import annotations

import time
import hashlib
from pathlib import Path

import numpy as np

from .budgeted_support_diagnostics import array_hash
from .supplement_pilots import propagate_cpp, transform, waveform_metrics

GENERATOR = 'physical_cpp_untruncated'
GAIN_RULE = 'reuse_g0_physical_gains_without_rescaling'
NUMERICAL_RTOL = 1e-10


def physical_channel_matrix(n, c1, c2, delays, dopplers, gains, *, prefix_length):
    """Full DAFT matrix of the existing CPP operator; no gain normalization.

    A path contributes a circular Dirichlet kernel, evaluated with one FFT.
    Unlike the G0 virtual-atom generator, every output bin is retained.
    """
    delays, dopplers, gains = map(np.asarray, (delays, dopplers, gains))
    if (type(n) is not int or n < 2 or type(prefix_length) is not int or
            not 0 <= prefix_length < n or not np.isfinite([c1, c2]).all() or
            delays.ndim != 1 or not len(delays) or
            delays.shape != dopplers.shape or delays.shape != gains.shape or
            any(not np.isfinite(x).all() for x in (delays, dopplers, gains)) or
            np.iscomplexobj(delays) or np.iscomplexobj(dopplers) or
            np.any(delays != np.floor(delays)) or np.any(delays < 0) or
            np.any(delays > prefix_length)):
        raise ValueError('finite matched physical paths and supported integer delays required')
    index = np.arange(n)
    difference = (index[:, None] - index[None, :]) % n
    chirp = np.exp(2j * np.pi * c2 * index**2)
    h = np.zeros((n, n), complex)
    for delay, nu, gain in zip(delays, dopplers, gains):
        kernel = np.fft.fft(np.exp(2j * np.pi * (nu + 2 * n * c1 * delay) * index / n)) / n
        phase = np.exp(-2j * np.pi * (c1 * delay**2 + delay * index / n))
        h += gain * kernel[difference] * phase[None, :]
    return chirp[:, None] * h * chirp.conj()[None, :]


def _projection_error(h, delays, dopplers, gains, l_max, k_max):
    """Exact Frobenius projection onto the public finite integer-atom dictionary.

    Integer time shifts are orthogonal; each shift's Doppler coefficients are
    the DFT of its physical modulation. This is a truth-side diagnostic, not an
    estimator fit or a claim that the G0 weights are that projection.
    """
    n = len(h)
    if not 0 <= l_max < n or not 0 <= k_max < n / 2:
        raise ValueError('invalid finite dictionary domain')
    kept_energy = 0.
    indices = np.arange(-k_max, k_max + 1) % n
    samples = np.arange(n)
    for delay in np.unique(delays):
        if delay > l_max:
            continue
        mask = delays == delay
        modulation = np.sum(gains[mask, None] * np.exp(
            2j * np.pi * dopplers[mask, None] * samples / n), axis=0)
        coefficients = np.fft.fft(modulation) / n
        kept_energy += n * float(np.vdot(coefficients[indices], coefficients[indices]).real)
    total = float(np.vdot(h, h).real)
    if total <= 0 or kept_energy > total * (1 + 1e-12):
        raise ValueError('invalid physical/projection energy')
    return max(0., (total - kept_energy) / total)


def physical_observation(raw, system, *, prefix_length):
    """Replace only the generator-side channel/observation; retain the G0 reference."""
    started = time.perf_counter()
    params = raw['params']
    delays = np.asarray(params['l_i'])
    nu = np.asarray(params['k_real'])
    gains = np.asarray(params['g_i'])
    h = physical_channel_matrix(int(system.N_total), system.c1, system.c2,
                                delays, nu, gains, prefix_length=prefix_length)
    pilot, data, noise = (np.asarray(raw[k]) for k in ('pilot', 'data', 'noise'))
    sigma2 = float(raw['sigma2'])
    waveform = transform(pilot + data, system.c1, system.c2, inverse=True)
    physical_y = transform(propagate_cpp(waveform, system.c1, delays, nu, gains,
                                        prefix_length=prefix_length), system.c1, system.c2)
    matrix_y = h @ (pilot + data)
    error = float(np.linalg.norm(physical_y - matrix_y) / max(1., np.linalg.norm(physical_y)))
    if not np.isfinite(error) or error > NUMERICAL_RTOL:
        raise ValueError('G1 matrix and direct CPP propagation disagree')
    power = float(np.vdot(h, h).real / len(h))
    if power <= 0 or not np.isfinite(power):
        raise ValueError('zero or nonfinite G1 channel energy')
    _, _, transmit = waveform_metrics(pilot / np.sqrt(system.rho), data,
        rho=system.rho, c1=system.c1, c2=system.c2, prefix_length=prefix_length,
        papr_limit_db=12., peak_power_limit=16.)
    hp, hx = h @ pilot, h @ data
    diag = dict(generator=GENERATOR, gain_normalization=GAIN_RULE,
        g0_fro_scale=float(params['fro_scale']), physical_doppler_cap_preserved=True,
        prefix_length=prefix_length, physical_paths=len(gains),
        channel_energy_per_dimension=power,
        g0_reference_operator_nmse=float(np.linalg.norm(h - raw['H'])**2 / (len(h) * power)),
        finite_dictionary_projection_nmse=_projection_error(
            h, delays, nu, gains, int(system.l_max_cap), int(system.k_max_cap)),
        model_error_scope='G0 operator mismatch includes truncation, weight convention and scaling; '
                          'finite-dictionary projection is reported separately',
        nominal_data_snr_db=float(10 * np.log10((1 - system.rho) / sigma2)),
        channel_average_data_snr_db=float(10 * np.log10((1 - system.rho) * power / sigma2)),
        realized_data_power=float(np.vdot(hx, hx).real / len(h)),
        realized_pilot_power=float(np.vdot(hp, hp).real / len(h)),
        realized_cross_power=float(2 * np.vdot(hp, hx).real / len(h)),
        noise_variance=sigma2, matrix_cpp_relative_error=error,
        numerical_relative_tolerance=NUMERICAL_RTOL,
        g0_reference_H_sha256=array_hash(raw['H']),
        physical_gains_sha256=array_hash(gains), transmit_normalization='none',
        waveform=transmit)
    # G0 virtual atoms must not masquerade as the complete physical truth.
    physical_params = {key: value for key, value in params.items()
                       if key not in ('P_actual', 'chan_coef_exp', 'l_exp', 'k_exp',
                                      'k_max_int', 'k_leak')}
    physical_params.update(representation=GENERATOR, physical_paths=len(gains),
                           gain_normalization=GAIN_RULE)
    out = dict(raw, H=h, y=physical_y + np.sqrt(sigma2) * noise, noiseless=physical_y,
               params=physical_params, g0_reference=dict(H=raw['H'], params=params))
    diag['physical_generation_and_diagnostics_seconds'] = time.perf_counter() - started
    return out, diag


def reuse_at_snr(raw, diagnostics, snr):
    """Reuse one exogenous block exactly; only thermal noise scale changes."""
    sigma2 = 10**(-snr / 10)
    power = diagnostics['channel_energy_per_dimension']
    data_power = float(np.vdot(raw['data'], raw['data']).real / len(raw['data']))
    return dict(raw, sigma2=sigma2, y=raw['noiseless'] + np.sqrt(sigma2) * raw['noise']), dict(
        diagnostics, noise_variance=sigma2,
        nominal_data_snr_db=float(10 * np.log10(data_power / sigma2)),
        channel_average_data_snr_db=float(10 * np.log10(data_power * power / sigma2)),
        g0_reference_generation_seconds=0., physical_generation_and_diagnostics_seconds=0.,
        shared_exogenous_reuse=True)


def evidence_arrays(frame, result):
    """Producer-time arrays for regenerating observations and checking every FER."""
    arrays = {key: np.asarray(frame.observed[key]) for key in ('y', 'pilot', 'sigma2')}
    arrays.update({key: np.asarray(frame._truth[key])
                   for key in ('H', 'info', 'coded', 'data', 'noise')})
    arrays.update({key: np.asarray(result[key])
                   for key in ('llr', 'decoded', 'info_hat', 'x_hard', 'x_soft', 'support',
                               'gains', 'mu', 'var')})
    arrays['Hhat'] = np.asarray(result['H'])
    arrays['H_g0_reference'] = np.asarray(frame._truth['g0_reference']['H'])
    for key in ('l_i', 'k_real', 'g_i', 'g_i_raw', 'fro_scale'):
        arrays[key] = np.asarray(frame._truth['params'][key])
    if any(a.dtype.hasobject or not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError('G1 evidence must contain finite, non-object arrays')
    return arrays


def audit_frame_evidence(row, batch):
    """Read-only audit; hashes, actual saved bits and physical observation closure."""
    from .supplement_profile import score_errors
    receipt = row['raw_evidence']
    path = Path(batch) / Path(receipt['path']).name
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
        raise ValueError('G1 raw evidence SHA-256 mismatch')
    with np.load(path, allow_pickle=False) as snapshot:
        arrays = dict(snapshot)
    if any(not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError('G1 nonfinite raw evidence')
    for key, expected in row['input_hashes'].items():
        if array_hash(arrays[key]) != expected:
            raise ValueError('G1 raw input hash mismatch: ' + key)
    diag = row['physical_model']
    if (diag['generator'] != GENERATOR or diag['gain_normalization'] != GAIN_RULE or
            array_hash(arrays['H_g0_reference']) != diag['g0_reference_H_sha256'] or
            array_hash(arrays['g_i']) != diag['physical_gains_sha256']):
        raise ValueError('G1 physical model provenance mismatch')
    scores = score_errors(arrays, arrays)
    if any(row[key] != value for key, value in scores.items()):
        raise ValueError('G1 saved bits disagree with reported error counts')
    calculated = arrays['H'] @ (arrays['pilot'] + arrays['data']) + np.sqrt(arrays['sigma2']) * arrays['noise']
    relative = np.linalg.norm(arrays['y'] - calculated) / max(1., np.linalg.norm(arrays['y']))
    if relative > NUMERICAL_RTOL:
        raise ValueError('G1 saved observation does not close')
    if not np.allclose(arrays['g_i'], arrays['g_i_raw'] * arrays['fro_scale'], rtol=1e-13, atol=1e-14):
        raise ValueError('G1 physical gain scale changed')


def summarize_physical_records(rows, blocks, snrs):
    """Development summaries with a strict three-SNR, one-exogenous-block contract."""
    table = {(row['block_id'], row['SNR']): row for row in rows}
    if len(table) != len(rows) or set(table) != {(b, s) for b in blocks for s in snrs}:
        raise ValueError('G1 physical records do not cover the exact registered grid')
    for block in blocks:
        reference = table[(block, snrs[0])]['input_hashes']
        for snr in snrs:
            row = table[(block, snr)]
            if any(reference[k] != row['input_hashes'][k]
                   for k in ('H', 'noise', 'info', 'coded', 'pilot', 'data')):
                raise ValueError('G1 exogenous pairing changed across SNR')
    by_snr = {}
    for snr in snrs:
        selected = [table[(b, snr)] for b in blocks]
        metrics = {}
        for key in ('g0_reference_operator_nmse', 'finite_dictionary_projection_nmse',
                    'channel_energy_per_dimension', 'nominal_data_snr_db',
                    'channel_average_data_snr_db', 'matrix_cpp_relative_error'):
            values = [r['physical_model'][key] for r in selected]
            metrics[key] = dict(mean=float(np.mean(values)), minimum=float(min(values)),
                                maximum=float(max(values)))
        times = [r['receiver_seconds'] for r in selected]
        by_snr[snr] = dict(n=len(blocks), errors=sum(r['FER'] for r in selected), metrics=metrics,
            receiver_seconds=dict(mean=float(np.mean(times)), p95=float(np.quantile(times, .95))),
            power_gate_failures=sum(not r['physical_model']['waveform']['passes_declared_simulation_power_gate']
                                    for r in selected))
    return dict(n_exogenous_blocks=len(blocks), snr_records=len(rows), by_snr=by_snr,
        pairing='one immutable exogenous block reused at three noise scales',
        inference='single-arm development only; no robustness or equivalence confirmation',
        timing_scope='instrumented development only; not formal COST-02',
        raw_inputs_and_terminal_bits_verified=len(rows))
