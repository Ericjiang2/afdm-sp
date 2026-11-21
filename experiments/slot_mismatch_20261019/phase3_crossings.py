"""Frozen paired FER=.01 crossings for the complete slot-mismatch archive."""

import numpy as np


SNR_CENTI_DB = np.arange(450, 801, 50)
SNR_DB = SNR_CENTI_DB / 100
TARGET = .01
BAND_DB = .25
CELLS = [(scenario, rho) for scenario in ('U', 'G') for rho in (300, 500)]
CAPS = {'M': (6, 8, 10, 12), 'T6': (8,), 'T10': (8,), 'N': (8, 12)}


def crossing_bounds(counts, n_frames):
    """First <= target crossing on the last array axis, as lower and upper bounds."""
    fer = np.asarray(counts, dtype=np.float64) / n_frames
    below = fer <= TARGET
    first = below.argmax(axis=-1)
    left = below[..., 0]
    right = ~below.any(axis=-1)
    # Use a real bracket for all internal crossings. Dummy interpolation at
    # censored entries is masked out, so it does not set their reported bounds.
    after = np.maximum(first, 1)
    before = after - 1
    valid = ~(left | right)
    above_fer = np.take_along_axis(fer, before[..., None], axis=-1)[..., 0]
    below_fer = np.take_along_axis(fer, after[..., None], axis=-1)[..., 0]
    log_before = np.log(np.where(valid, above_fer, 1.))
    log_after = np.log(np.where(valid, np.where(below_fer == 0, .5 / n_frames, below_fer), .001))
    snr = SNR_DB[before] + (SNR_DB[after] - SNR_DB[before]) * (
        (np.log(TARGET) - log_before) / (log_after - log_before)
    )
    lower = np.where(left, -np.inf, np.where(right, SNR_DB[-1], snr))
    upper = np.where(left, SNR_DB[0], np.where(right, np.inf, snr))
    return np.stack((lower, upper), axis=-1)


def extended_percentile(values, percentile):
    """Linear percentile on the extended real line, retaining infinite endpoints."""
    values = np.sort(values)
    index = (values.size - 1) * percentile / 100
    lower, upper = values[int(np.floor(index))], values[int(np.ceil(index))]
    if lower == upper or not np.isfinite(lower):
        return lower
    if not np.isfinite(upper):
        return upper
    return lower + (index % 1) * (upper - lower)


def bounds_json(bounds):
    return {key: float(value) if np.isfinite(value) else None
            for key, value in zip(('lo', 'hi'), bounds)}


def paired_ci(draws):
    return (extended_percentile(draws[:, 0], 2.5), extended_percentile(draws[:, 1], 97.5))


def contrast_bounds(bounds, positive_indices, negative_indices):
    positive = bounds[..., positive_indices, :].sum(axis=-2)
    negative = bounds[..., negative_indices, :].sum(axis=-2)
    return positive - negative[..., ::-1]


def curve_keys():
    return [(family, scenario, rho, cap)
            for family, caps in CAPS.items()
            for scenario, rho in ([('G', 300)] if family == 'N' else CELLS)
            for cap in (*caps, 'A3')]


def read_crossings(rows, weights):
    """Use shared frame multiplicities ordered by physical frame ID from 10000."""
    n_frames = weights.shape[1]
    keys = curve_keys()
    index = {key: i for i, key in enumerate(keys)}
    # Small integer counts are exactly representable in float32; BLAS avoids
    # integer matrix multiplication and the bootstrap is evaluated in batches.
    failures = np.full((n_frames, len(keys), SNR_DB.size), -1, dtype=np.float32)
    noise_rows = [[] for _ in SNR_DB]
    for row in rows:
        family, scenario, rho = row['family'], row['scenario'], row['rho_permille']
        snr = row['snr_centi_db']
        frame = row['frame'] - 10000
        point = (snr - SNR_CENTI_DB[0]) // 50
        if not (0 <= frame < n_frames and 0 <= point < SNR_DB.size and SNR_CENTI_DB[point] == snr):
            raise ValueError(f'Out-of-grid frame/SNR: {row["frame"]}/{snr}')
        a3 = index[(family, scenario, rho, 'A3')]
        if failures[frame, a3, point] != -1:
            raise ValueError(f'Duplicate receiver key: {family}/{scenario}/{rho}/{frame + 10000}/{snr}')
        failures[frame, a3, point] = row['A3']['info_errors'] > 0
        for cap in CAPS[family]:
            record = row['s'][str(cap)]
            selected = record['arms']['A1c'] if record['triggered'] else record['f0']
            failures[frame, index[(family, scenario, rho, cap)], point] = selected['info_errors'] > 0
        if family == 'N':
            noise_rows[point].append(row['noise'])
    if np.any(failures == -1):
        raise ValueError('The complete per-curve frame/SNR grid is required')

    counts = failures.sum(axis=0, dtype=np.int64)
    observed = crossing_bounds(counts, n_frames)
    boot = np.empty((weights.shape[0], len(keys), 2), dtype=np.float64)
    matrix = failures.reshape(n_frames, -1)
    for start in range(0, weights.shape[0], 512):
        batch = weights[start:start + 512]
        boot_counts = (batch.astype(np.float32, copy=False) @ matrix).reshape(-1, len(keys), SNR_DB.size)
        boot[start:start + len(batch)] = crossing_bounds(boot_counts, n_frames)

    curves = []
    for i, (family, scenario, rho, cap) in enumerate(keys):
        raw = observed[i]
        curves.append(dict(
            family=family, scenario=scenario, rho_permille=rho,
            arm='A3' if cap == 'A3' else 'B', cap=None if cap == 'A3' else cap,
            n_frames=n_frames, snr_centi_db=SNR_CENTI_DB.tolist(), error_counts=counts[i].tolist(),
            fer=(counts[i] / n_frames).tolist(), crossing=bounds_json(raw),
            crossing_ci=bounds_json(paired_ci(boot[:, i])),
            censoring='left' if np.isneginf(raw[0]) else 'right' if np.isposinf(raw[1]) else 'bracketed',
            bootstrap_left=int(np.isneginf(boot[:, i, 0]).sum()),
            bootstrap_right=int(np.isposinf(boot[:, i, 1]).sum()),
        ))

    contrasts = []
    for family, scenario, rho, cap in keys:
        if cap == 'A3' or (family == 'M' and cap == 8):
            continue
        positive = [index[(family, scenario, rho, cap)]]
        negative = [index[('M', scenario, rho, cap if family == 'N' else 8)]]
        if family in ('T6', 'T10'):
            positive.append(index[('M', scenario, rho, 'A3')])
            negative.append(index[(family, scenario, rho, 'A3')])
        raw = contrast_bounds(observed, positive, negative)
        samples = contrast_bounds(boot, positive, negative)
        ci = paired_ci(samples)
        if ci[0] >= -BAND_DB and ci[1] <= BAND_DB:
            label = 'ROBUST'
        elif ci[0] > BAND_DB:
            label = 'DEGRADED'
        else:
            label = 'INCONCLUSIVE'
        contrasts.append(dict(family=family, scenario=scenario, rho_permille=rho, cap=cap,
                              delta=bounds_json(raw), delta_ci=bounds_json(ci), label=label,
                              bootstrap_unbounded_lower=int(np.isneginf(samples[:, 0]).sum()),
                              bootstrap_unbounded_upper=int(np.isposinf(samples[:, 1]).sum())))

    noise = []
    for snr, records in zip(SNR_CENTI_DB, noise_rows):
        ratio = np.array([row['ratio'] for row in records])
        estimates = np.array([row['estimate'] for row in records])
        errors = estimates - estimates / ratio
        noise.append(dict(snr_centi_db=int(snr), n=len(records), ratio_mean=float(ratio.mean()),
                          ratio_sd=float(ratio.std(ddof=1)),
                          ratio_quantiles=np.percentile(ratio, [2.5, 50, 97.5]).tolist(),
                          variance_error_mean=float(errors.mean()),
                          variance_error_sd=float(errors.std(ddof=1)),
                          floor_hits=sum(row['clipped'] for row in records)))

    n8 = next(curve for curve in curves if curve['family'] == 'N' and curve['cap'] == 8)
    n8_delta = next(c for c in contrasts if c['family'] == 'N' and c['cap'] == 8)['delta']
    forecast = None
    if n8['censoring'] != 'bracketed' or n8_delta['lo'] is not None and n8_delta['lo'] > BAND_DB:
        forecast = False
    elif n8_delta['hi'] is not None and n8_delta['hi'] <= BAND_DB:
        forecast = True
    return dict(curves=curves, contrasts=contrasts,
                noise=dict(per_snr=noise, forecast_cap8=dict(
                    crossing=n8['crossing'], censoring=n8['censoring'], delta=n8_delta, met=forecast)))
