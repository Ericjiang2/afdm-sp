"""Read-only measurements of the archived first exchange and round-1 APP."""

from unittest.mock import patch

import numpy as np


def check_exact(actual, expected, label):
    if actual != expected:
        fields = [field for field in set(actual) | set(expected)
                  if actual.get(field) != expected.get(field)]
        raise ValueError(f'{label} mismatch: {sorted(fields)}')


def exchange_readout(replay, study, obs, arrays, truth, archived):
    """Observe the frozen score grid and pass the unaltered summary through."""
    traces, gains = [], []
    first_exchange, measured_gains = replay.first_exchange, replay.measured_gains

    def capture_exchange(*args, **kwargs):
        result, trace = first_exchange(*args, **kwargs)
        traces.append(trace)
        return result, trace

    def capture_gains(*args):
        gain = measured_gains(*args)
        gains.append(gain)
        return gain

    with patch.object(replay, 'first_exchange', capture_exchange), \
            patch.object(replay, 'measured_gains', capture_gains):
        observed = replay.first_exchange_from_f0(study, obs, arrays, truth)
    check_exact(observed, {field: archived[field] for field in observed}, 'Admission archive')
    return {
        name: reward_maxima(observed['arms'][name], trace, gain, truth['l_i'])
        for name, trace, gain in zip(('A1c', 'A2'), traces, gains, strict=True)
    }


def reward_maxima(arm, trace, gain, true_delays):
    entering = np.array([path['delay'] for path in trace['entering_paths']])
    delays = trace['candidate_delays']
    occupied = np.isin(delays, entering)
    true_delay = np.isin(delays, true_delays)
    valid = trace['valid']
    phantom = np.array([np.isin(delays, np.delete(entering, slot))
                        for slot in range(len(entering))])
    best_p = max((p for slot in arm['slots'] for p in slot['P']),
                 key=lambda p: p['measured_gain'])
    if best_p['measured_gain'] != gain[valid & phantom].max():
        raise ValueError('Gross phantom maximum differs from the archived candidates')
    anchor = trace['entering_gains'][best_p['anchor']]

    def best(eligible):
        candidates = gain[valid & eligible]
        return float(candidates.max()) if candidates.size else None

    return dict(G_P=best_p['measured_gain'], G_T=best(~occupied & true_delay),
                G_F=best(~occupied & ~true_delay), anchor_power=float(abs(anchor) ** 2),
                ridge=arm['lambda'])


def app_readout(study, obs, arrays, archived):
    from messages import moments
    from physical import dkernel

    system, kernel = study[1].system, study[3]
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - system.rho)
    x = obs['pilot'] + mu
    E, u = float(np.vdot(x, x).real), float(v.sum())
    for name, expected in archived['arms'].items():
        check_exact(dict(E=E, u=u), {k: expected[k] for k in ('E', 'u')}, name)
    if u <= 0 or system.l_max_cap != 102 or len(v) != 1024:
        raise ValueError('Unexpected APP variance scale or domain')
    vf = np.fft.fft(v)
    spectrum = abs(vf[1:103]) / u
    delays, dopplers = arrays['r1_delays'], arrays['r1_dopplers']
    atoms = [kernel.Path(int(delay), float(nu))
             for delay, nu in zip(delays, dopplers, strict=True)]
    # This is the frozen gamma_full operation on the retained support.
    gamma = kernel._gamma_cross(atoms, atoms, vf, system.c1)
    i, j = np.nonzero(np.triu(delays[:, None] != delays[None, :], k=1))
    if not len(i):
        raise ValueError('Sampled F0 support has no cross-delay pair')
    d, delta_nu = delays[j] - delays[i], dopplers[j] - dopplers[i]
    variance_factor = abs(vf[d % len(v)]) / u
    realized = abs(gamma[i, j]) / u
    shift = delta_nu + 2 * len(v) * system.c1 * d
    wrapped = (shift + len(v) / 2) % len(v) - len(v) / 2
    # Magnitude of the closed form, independently of the frozen complex kernel.
    expected = abs(np.sinc(wrapped) / np.sinc(wrapped / len(v))) * variance_factor
    error = abs(realized - expected)
    if np.any(error > 1e-10 * expected):
        raise ValueError('Closed-form Gamma parity exceeds relative tolerance')
    relative = np.divide(error, expected, out=np.zeros_like(error), where=expected != 0)
    ofdm = abs(dkernel(delta_nu, len(v))) * variance_factor
    afdm_max, ofdm_max = float(realized.max()), float(ofdm.max())
    if ofdm_max <= 0:
        raise ValueError('OFDM ratio denominator is zero')
    return dict(d1=float(spectrum[0]), d2=float(spectrum[1]), d3=float(spectrum[2]),
                max_d=float(spectrum.max()), afdm_max=afdm_max, ofdm_max=ofdm_max,
                afdm_over_ofdm=afdm_max / ofdm_max, pairs=len(i),
                gamma_max_rel_error=float(relative.max()), c1=float(system.c1))
