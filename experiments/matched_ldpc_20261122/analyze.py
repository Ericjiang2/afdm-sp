"""Paired frame-cluster inference for the registered FER endpoints."""
import numpy as np
from scipy.stats import beta

from c1A_stats import pava


ARMS = ('regular', 'matched', 'awgn')
FRAMES = tuple(range(12000, 12200))
GRID = tuple(range(525, 1051, 25))


def crossing(snrs, rates, target):
    fit = -np.asarray(pava(-np.asarray(rates), np.ones(len(rates))))
    if fit[0] < target:
        return -np.inf, snrs[0]
    if fit[-1] > target:
        return snrs[-1], np.inf
    index = int(np.flatnonzero(fit <= target)[0])
    if fit[index] == target:
        point = snrs[index]
    else:
        point = np.interp(target, fit[index - 1:index + 1][::-1], snrs[index - 1:index + 1][::-1])
    return point, point


def difference(left, right):
    return round(float(left[0] - right[1]), 12), round(float(left[1] - right[0]), 12)


def label(regular, awgn):
    if regular[1] < .3 or awgn[1] <= 0:
        return 'KILL'
    if awgn[0] > 0 and regular[0] >= .8:
        return 'CONTINUE'
    if awgn[0] > 0 and regular[0] >= .3 and regular[1] < .8:
        return 'MIDDLE'
    return 'UNRESOLVED'


def json_bounds(bounds):
    return [float(x) if np.isfinite(x) else None for x in bounds]


def validate_cell(rows, exogenous, key):
    if len(rows) != len(FRAMES) or {row['frame'] for row in rows} != set(FRAMES):
        raise ValueError('cell does not contain the 200 registered unique frames')
    ordered = sorted(rows, key=lambda row: row['frame'])
    for row in ordered:
        frame, load = row['frame'], row['load']
        if (load, row['snr_centi_db']) != key:
            raise ValueError('raw row does not match its cell key')
        shared = row['info_sha256'], row['noise_sha256'], row['pilot_sha256']
        physical = row['channel_seed'], row['gains_sha256']
        if (exogenous.setdefault(frame, shared) != shared or
                exogenous.setdefault((frame, load), physical) != physical):
            raise ValueError('cross-cell exogenous pairing mismatch')
        if set(row['arms']) != set(ARMS):
            raise ValueError('missing paired arm')
    return np.array([[row['arms'][arm]['info_errors'] > 0 for arm in ARMS] for row in ordered])


def summarize(cells):
    """Analyze complete cells only. Null endpoints denote open bounds."""
    exogenous = {}
    errors = {key: validate_cell(rows, exogenous, key) for key, rows in cells.items()}
    counts = {f'L{load}_{snr / 100:.2f}': dict(zip(ARMS, values.sum(axis=0).tolist()))
              for (load, snr), values in sorted(errors.items())}
    main_snrs = sorted(snr for load, snr in errors if load == 28)
    if not main_snrs:
        return dict(frame_errors=counts, frames_per_cell=len(FRAMES), verdict='UNRESOLVED')
    snrs = np.asarray(main_snrs, dtype=float) / 100
    cube = np.stack([errors[(28, snr)] for snr in main_snrs], axis=1)
    rates = cube.mean(axis=0)
    at10 = [crossing(snrs, rates[:, index], .1) for index in range(len(ARMS))]
    gains = [difference(at10[index], at10[1]) for index in (0, 2)]

    # Flatten SNR and arm axes only after sharing the draw across complete frames.
    rng = np.random.default_rng(20261123)
    weights = rng.multinomial(len(FRAMES), np.full(len(FRAMES), 1 / len(FRAMES)), size=4000)
    draws = (weights @ cube.reshape(len(FRAMES), -1)) / len(FRAMES)
    paired = []
    for draw in draws.reshape(-1, len(snrs), len(ARMS)):
        endpoints = [crossing(snrs, draw[:, index], .1) for index in range(len(ARMS))]
        paired.append([difference(endpoints[index], endpoints[1]) for index in (0, 2)])
    paired = np.asarray(paired)
    intervals = zip(np.quantile(paired[:, :, 0], .025, axis=0, method='inverted_cdf'),
                    np.quantile(paired[:, :, 1], .975, axis=0, method='inverted_cdf'))

    # Binomial confidence inversion is simultaneous over the full allowed grid.
    failures = cube.sum(axis=0)
    n = len(FRAMES)
    tail = .05 / (2 * len(GRID) * len(ARMS))
    lowers = np.where(failures == 0, 0, beta.ppf(tail, failures, n - failures + 1))
    uppers = np.where(failures == n, 1, beta.ppf(1 - tail, failures + 1, n - failures))
    at01 = []
    for index in range(len(ARMS)):
        below = snrs[lowers[:, index] > .01]
        above = snrs[uppers[:, index] <= .01]
        low = below[-1] if below.size else -np.inf
        high = above[0] if above.size else np.inf
        at01.append((low, high) if low <= high else (-np.inf, np.inf))
    gain_names = ('regular_minus_matched', 'awgn_minus_matched')
    return dict(frame_errors=counts, frames_per_cell=n, verdict=label(*gains),
                crossover_10_db={arm: json_bounds(bounds) for arm, bounds in zip(ARMS, at10)},
                gains_10_db={name: json_bounds(bounds) for name, bounds in zip(gain_names, gains)},
                paired_bootstrap_10_db={name: json_bounds(bounds) for name, bounds in zip(gain_names, intervals)},
                crossover_01_confidence_db={arm: json_bounds(bounds) for arm, bounds in zip(ARMS, at01)},
                gains_01_confidence_db={name: json_bounds(difference(at01[index], at01[1]))
                                        for name, index in zip(gain_names, (0, 2))})
