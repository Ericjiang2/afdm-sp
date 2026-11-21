"""Validate the completed replay archive and apply the frozen readout."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import spearmanr

from run_main import CAP, CELLS, CORE_HOUR_CAP, FIRST, SHARD_FRAMES, SNRS, STOP, TARGET_COUNT

BOOTSTRAPS, SEED = 20_000, 20261019
ARMS = ('A2', 'A1c')
CHECKS = ('E_positive', 'u_positive', 'lambda_positive', 'K_A2_positive', 'K_A1c_positive',
          'legal_P', 'legal_N', 'one_surviving_anchor', 'D_ge_090', 'kappa_minus_D_le_005',
          'P_other_coherence_le_015', 'N_entering_coherence_le_015')


def read_archive(run):
    config = json.loads((run / 'RUN_CONFIG.json').read_text())['_config']
    receipt = json.loads((run / 'main_receipt.json').read_text())
    status = (run / 'STATUS').read_text().split()
    shards = (STOP - FIRST) // SHARD_FRAMES
    if (receipt['_config'] != config or status[:2] != ['DONE', str(shards)] or len(status) != 3
            or receipt['reason'] is not None or receipt['errors']
            or receipt['completed_shards'] != shards or receipt['keys'] != TARGET_COUNT
            or not 0 < receipt['core_hours'] < CORE_HOUR_CAP
            or abs(float(status[2]) - receipt['core_hours']) > 0.0000005
            or config['family'] != 'M' or config['cap'] != CAP or config['expected_keys'] != TARGET_COUNT
            or config['frame_range'] != [FIRST, STOP - 1] or config['snr_centi_db'] != list(SNRS)
            or config['cells'] != [list(cell) for cell in CELLS]):
        raise ValueError('Main replay completion or scope differs from the frozen protocol')
    raw_manifest = (run / 'REMOTE_ROWS_MD5.txt').read_bytes()
    manifest = [line.split() for line in raw_manifest.decode().splitlines()]
    if [name for _, name in manifest] != [f'rows_shard{i:03d}.jsonl.gz' for i in range(shards)]:
        raise ValueError('Unexpected replay shard inventory')

    keys, admitted, pairs, funnel = set(), [], [], []
    survivors = np.zeros(len(CHECKS), dtype=int)
    independent_failures = np.zeros(len(CHECKS), dtype=int)
    for shard, (digest, name) in enumerate(manifest):
        path = run / name
        if hashlib.md5(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Archive MD5 differs at {name}')
        lo = FIRST + SHARD_FRAMES * shard
        count = 0
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                frame, scenario, rho, snr = (row[key] for key in ('frame', 'scenario', 'rho', 'snr_centi_db'))
                key = frame, scenario, rho, snr
                if (key in keys or not lo <= frame < lo + SHARD_FRAMES or (scenario, rho) not in CELLS
                        or snr not in SNRS or row['family'] != 'M' or row['cap'] != CAP
                        or set(row['arms']) != set(ARMS) or set(row['subset_checks']) != set(CHECKS)):
                    raise ValueError(f'Unexpected replay key or schema {key}')
                keys.add(key)
                count += 1
                checks = [row['subset_checks'][name] for name in CHECKS]
                if all(checks) != row['subset_pass']:
                    raise ValueError(f'Inconsistent subset checks at {key}')
                survivors += np.logical_and.accumulate(checks)
                independent_failures += np.logical_not(checks)
                if not row['subset_pass']:
                    continue
                a2, a1c = (row['arms'][name] for name in ARMS)
                observed = a2['actual_class']
                if observed not in ('P', 'N', 'O', 'none') or a1c['actual_class'] not in ('P', 'N', 'O', 'none'):
                    raise ValueError(f'Inconsistent observed class at {key}')
                predicted = a2['predicted_class']
                correct = (predicted == ('O' if observed == 'none' else observed)
                           and (predicted != 'N' or a2['predicted_N_is_true']))
                inside = row['truth']['inside_W']
                admitted.append((frame, observed, a2['m_A2'], inside, bool(correct), a1c['actual_class'] == 'P'))
                # Q2 admits the A2 pair attaining P_A2. Read that same pair in both arms.
                pair = a2['maxima']['P']
                for i, arm in enumerate((a2, a1c)):
                    phantom, = (p for p in arm['slots'][pair['slot']]['P']
                                if (p['delay'], p['doppler']) == (pair['delay'], pair['doppler']))
                    D, kappa = complex(*phantom['D']), complex(*phantom['kappa'])
                    pairs.append((i, abs(D), abs(kappa - D), phantom['modeled_gain'], phantom['measured_gain']))
        if count != config['shard_expected_keys'][shard]:
            raise ValueError(f'Wrong replay count at shard {shard}')
    if len(keys) != TARGET_COUNT:
        raise ValueError(f'Expected {TARGET_COUNT} unique target keys, got {len(keys)}')
    prior = len(keys)
    for step, remaining, failed in zip(CHECKS, map(int, survivors), map(int, independent_failures)):
        funnel.append(dict(step=step, removed=prior-remaining, remaining=remaining, failed_independently=failed))
        prior = remaining
    return config, receipt, admitted, pairs, funnel, hashlib.md5(raw_manifest).hexdigest()


def auc_batch(weights, frame, positive, left, right):
    """Rows must already be sorted by score, with [left,right) bounds for ties."""
    key_weights = weights[:, frame]
    negative_weights = key_weights * ~positive
    all_neg = np.column_stack([np.zeros(len(weights)), negative_weights.cumsum(axis=1)])
    contributions = all_neg[:, left] + .5 * (all_neg[:, right] - all_neg[:, left])
    pos_weights = key_weights * positive
    numerator = (pos_weights * contributions).sum(axis=1)
    denominator = pos_weights.sum(axis=1) * all_neg[:, -1]
    return divide(numerator, denominator)


def divide(net, count):
    return np.divide(net, count, out=np.full(net.shape, np.nan), where=count != 0)


def describe(draws):
    point, draws = draws[0], draws[1:]
    valid = draws[np.isfinite(draws)]
    ci = np.percentile(valid, [2.5, 97.5]).tolist() if len(valid) else None
    return dict(point=float(point), ci95=ci, undefined_draws=len(draws)-len(valid))


def verdict(estimate, threshold):
    if estimate['ci95'] is None:
        return 'INCONCLUSIVE'
    lo, hi = estimate['ci95']
    return 'SUPPORTED' if lo > threshold else 'REFUTED' if hi <= threshold else 'INCONCLUSIVE'


def bootstrap(admitted, n_frames, first_frame):
    frame = np.array([r[0]-first_frame for r in admitted])
    a2_phantom = np.array([r[1] == 'P' for r in admitted])
    a1c_phantom = np.array([r[5] for r in admitted])
    correct = np.array([r[4] for r in admitted])
    inside = np.array([r[3] is True for r in admitted])
    outside = np.array([r[3] is False for r in admitted])
    counts = [np.ones(len(admitted)), correct, a2_phantom, inside, outside, a2_phantom & inside,
              a2_phantom & outside, a1c_phantom & inside]
    by_frame = np.stack([np.bincount(frame, weights=mask, minlength=n_frames) for mask in counts], axis=1)
    binary = sorted((r for r in admitted if r[1] in ('P', 'N')), key=lambda r: r[2])
    scores = np.array([r[2] for r in binary])
    if not np.isfinite(scores).all():
        raise ValueError('Nonfinite AUC margin for admitted P/N observation')
    auc_frames = np.array([r[0]-first_frame for r in binary])
    positive = np.array([r[1] == 'P' for r in binary])
    left = np.searchsorted(scores, scores, side='left')
    right = np.searchsorted(scores, scores, side='right')
    rng = np.random.default_rng(SEED)
    auc_draws, rates = [], []
    for start in range(0, BOOTSTRAPS+1, 256):
        weights = np.empty((min(256, BOOTSTRAPS+1-start), n_frames))
        for i, draw in enumerate(weights, start):
            draw[:] = 1 if i == 0 else np.bincount(rng.integers(n_frames, size=n_frames), minlength=n_frames)
        auc_draws.extend(auc_batch(weights, auc_frames, positive, left, right))
        rates.extend(weights @ by_frame)
    total, hits, base, in_n, out_n, a2in, a2out, a1cin = np.asarray(rates).T
    m1 = describe(np.asarray(auc_draws))
    m2 = describe(divide(a2in, in_n) - divide(a2out, out_n))
    m1['verdict'], m2['verdict'] = verdict(m1, .50), verdict(m2, 0.)
    gap = describe(divide(a2in-a1cin, in_n))
    gap['separation_refuted'] = gap['ci95'] is not None and gap['ci95'][1] <= 0.
    return dict(M1=m1, M2=m2, accuracy=describe(divide(hits, total)),
                always_phantom=describe(divide(base, total)), accuracy_gain=describe(divide(hits-base, total)),
                A2_inside_W=describe(divide(a2in, in_n)), A2_outside_W=describe(divide(a2out, out_n)),
                A1c_inside_W=describe(divide(a1cin, in_n)), inside_arm_gap=gap)


def calibration_paired(pairs):
    data = np.asarray(pairs)
    arm, D, delta, modeled, measured = data.T

    def calibrate(mask):
        x, y = modeled[mask], measured[mask]
        positive = y > 0
        rho = float(spearmanr(x, y).statistic) if len(set(x)) > 1 and len(set(y)) > 1 else None
        median = float(np.median(abs(x[positive] - y[positive])/y[positive])) if positive.any() else None
        return dict(n=len(x), spearman=rho, median_relative_error=median,
                    nonpositive_measured=int((~positive).sum()))

    result = {}
    for name, selected in [('pooled', np.ones(len(arm), bool)), *((a, arm == i) for i, a in enumerate(ARMS))]:
        result[name] = dict(all=calibrate(selected),
                            abs_D={'[.90,.95)': calibrate(selected & (D < .95)),
                                   '[.95,1]': calibrate(selected & (D >= .95))},
                            abs_kappa_minus_D={'[0,.025)': calibrate(selected & (delta < .025)),
                                               '[.025,.05]': calibrate(selected & (delta >= .025))})
    return result


def score(admitted, pairs, funnel, target_count, n_frames, first_frame):
    coverage = len(admitted) / target_count
    classes = Counter(row[1] for row in admitted)
    window = Counter(row[3] for row in admitted)
    findings = dict(target_keys=target_count, admitted=len(admitted), coverage=coverage,
                    funnel=funnel, admitted_class_counts=dict(classes),
                    admitted_window_counts=dict(inside=window[True], outside=window[False], undefined=window[None]))
    failures = []
    if coverage < .05:
        failures.append('coverage < 5%')
    if not classes['P'] or not classes['N']:
        failures.append('AUC has an empty outcome class')
    if not window[True] or not window[False]:
        failures.append('W has an empty stratum')
    if failures:
        return dict(status='UNSCORABLE', reasons=failures, **findings)
    return dict(status='SCORED', **findings, **bootstrap(admitted,n_frames,first_frame),
                calibration=calibration_paired(pairs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    config, receipt, admitted, pairs, funnel, manifest_md5 = read_archive(args.run)
    result = score(admitted, pairs, funnel, TARGET_COUNT, STOP-FIRST, FIRST)
    payload = dict(_argv=sys.argv, _config=dict(run_commit=config['commit'], bootstrap_draws=BOOTSTRAPS,
                    seed=SEED, cluster='physical_frame', bootstrap_frame_count=STOP-FIRST,
                    sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    m2_scope='admitted units with W defined', no_edit_accuracy_class='other',
                    calibration_pair='A2 winning phantom pair shared across arms',
                    calibration_forecast_scope='pooled', calibration_abs_D_split=.95,
                    calibration_abs_kappa_minus_D_split=.025),
                   manifest_md5=manifest_md5, core_hours=receipt['core_hours'],
                   started_utc=receipt['started_utc'], ended_utc=receipt['ended_utc'], **result)
    out = args.run / 'results.json'
    pending = out.with_suffix('.json.pending')
    with pending.open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')
    pending.rename(out)
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
