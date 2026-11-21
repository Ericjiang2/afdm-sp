"""Primary paired rescue contrasts for PROTOCOL §7."""

from itertools import product
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import interval  # noqa: E402

SCENARIOS = ('U', 'G')
PRIMARY_SNRS = {150: (600, 650, 700, 800), 300: (450, 500)}
N_BOOT = 20_000
SEED = 20261125
FAILURE_LIMIT = .01
MINIMUM_GAIN = .03
MINIMUM_DISCORDANT_FRAMES = 5


def classify(low_rho_gain, matched_gain, interaction):
    """Apply the direction, practical-size and matched-equivalence rules independently."""
    direction = practical = matched = 'unresolved'
    if low_rho_gain['evaluable']:
        lo, hi = low_rho_gain['ci_lo'], low_rho_gain['ci_hi']
        if interaction['evaluable']:
            direction = 'supported' if lo > 0 and interaction['ci_lo'] > 0 else 'not_supported'
        if lo >= MINIMUM_GAIN:
            practical = 'meaningful'
        elif hi < MINIMUM_GAIN:
            practical = 'not_meaningful'
        else:
            practical = 'uncertain'
    if matched_gain['evaluable']:
        matched = ('unchanged' if -MINIMUM_GAIN <= matched_gain['ci_lo']
                   <= matched_gain['ci_hi'] <= MINIMUM_GAIN else 'not_established')
    return dict(direction=direction, practical_size=practical, matched_30=matched)


def _paired_counts(rows, frames):
    if not frames or len(set(frames)) != len(frames):
        raise ValueError('Expected distinct registered physical frame IDs')
    remaining = {(scenario, rho, snr, frame)
                 for rho, snrs in PRIMARY_SNRS.items()
                 for scenario, snr, frame in product(SCENARIOS, snrs, frames)}
    frame_index = {frame: i for i, frame in enumerate(frames)}
    rho_index = {rho: i for i, rho in enumerate(PRIMARY_SNRS)}
    # The final axes encode whether CD2 and CD4, respectively, rescued the key.
    counts = np.zeros((len(frames), len(PRIMARY_SNRS), 2, 2), dtype=np.int64)
    for row in rows:
        rho, snr = row['rho_permille'], row['snr_centi_db']
        if snr not in PRIMARY_SNRS.get(rho, ()):
            continue
        frame = row['frame']
        key = row['scenario'], rho, snr, frame
        if key not in remaining:
            raise ValueError(f'Duplicate or unexpected primary row: {key}')
        remaining.remove(key)
        triggered, syndrome = row['triggered'], row['syndrome']
        if type(triggered) is not bool or type(syndrome) is not int or syndrome < 0 or triggered != bool(syndrome):
            raise ValueError(f'Invalid trigger or syndrome at {key}')
        errors2, errors4 = (row['arms'][arm]['errors'] for arm in ('CD2', 'CD4'))
        if any(type(errors) is not int or errors < 0 for errors in (errors2, errors4)):
            raise ValueError(f'Invalid decoder error count at {key}')
        if triggered:
            counts[frame_index[frame], rho_index[rho], int(errors2 == 0), int(errors4 == 0)] += 1
    if remaining:
        raise ValueError(f'Missing {len(remaining)} primary rows; first missing key: {min(remaining)}')
    return counts


def _gain(counts):
    triggered = counts.sum(axis=(-1, -2))
    rescued_by_cd4_only = counts[..., 0, 1]
    rescued_by_cd2_only = counts[..., 1, 0]
    return np.divide(
        rescued_by_cd4_only - rescued_by_cd2_only, triggered,
        out=np.full(triggered.shape, np.nan), where=triggered > 0,
    )


def _summary(point, draws, enough_discordance):
    valid = np.isfinite(draws)
    invalid_fraction = float((~valid).mean())
    evaluable = bool(enough_discordance and np.isfinite(point) and invalid_fraction <= FAILURE_LIMIT)
    bounds = interval(draws[valid]) if evaluable else dict(
        ci_lo=None, ci_hi=None, ci_width=None, contains_0=None,
    )
    return dict(point=float(point) if np.isfinite(point) else None, **bounds,
                undefined_draws=int((~valid).sum()), undefined_fraction=invalid_fraction, evaluable=evaluable)


def readout(rows, frames):
    """Require the complete primary panel, and resample every registered frame jointly."""
    frames = tuple(sorted(frames))
    counts = _paired_counts(rows, frames)
    full_counts = counts.sum(axis=0)
    points = _gain(full_counts)
    draws = np.empty((N_BOOT, len(PRIMARY_SNRS)))
    n = len(frames)
    probabilities = np.full(n, 1 / n)
    frame_totals = counts.reshape(n, -1)
    rng = np.random.default_rng(SEED)
    for start in range(0, N_BOOT, 256):
        batch = min(N_BOOT - start, 256)
        weights = rng.multinomial(n, probabilities, size=batch)
        resampled = (weights @ frame_totals).reshape(batch, *full_counts.shape)
        draws[start:start + batch] = _gain(resampled)

    triggered_frames = np.count_nonzero(counts.sum(axis=(-1, -2)), axis=0)
    discordant_frames = np.count_nonzero(counts[..., 0, 1] + counts[..., 1, 0], axis=0)
    enough = discordant_frames >= MINIMUM_DISCORDANT_FRAMES
    gains = {rho: _summary(points[i], draws[:, i], enough[i])
             for i, rho in enumerate(PRIMARY_SNRS)}
    did = _summary(points[0] - points[1], draws[:, 0] - draws[:, 1], enough.all())
    census = {}
    for i, (rho, snrs) in enumerate(PRIMARY_SNRS.items()):
        pair = full_counts[i]
        census[rho] = dict(
            snrs_centi_db=snrs, keys=n * len(SCENARIOS) * len(snrs), triggered=int(pair.sum()),
            triggered_frames=int(triggered_frames[i]), discordant_frames=int(discordant_frames[i]),
            rescued_cd2=int(pair[1, :].sum()), rescued_cd4=int(pair[:, 1].sum()),
            new_harms=int(pair[1, 0]), new_rescues=int(pair[0, 1]),
        )
    return dict(n_frame_clusters=n, bootstrap=dict(
        draws=N_BOOT, seed=SEED, confidence_level=.95, undefined_draw_failure_limit=FAILURE_LIMIT,
        minimum_discordant_frames=MINIMUM_DISCORDANT_FRAMES,
    ), counts=census, gain=gains, did=did, **classify(gains[150], gains[300], did))
