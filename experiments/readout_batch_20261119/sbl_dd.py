"""Summarize saved SBL residual-gap and decision-directed noise rows."""

import json

import numpy as np

from common import interval, read_rows


SBL_SOURCE = 'sbl_residual_gap_20261119/out/main_v2_20261119'
DD_SOURCE = 'sigma2_dd_20261118/out/main_20261118'
ARMS = {'R0': 'R0', 'U2': 'U2', 'K': 'K′', 'M': 'M', 'KM': 'KM′'}
METRICS = ('beta', 'converged', 'iterations', 'co_delay_pairs', 'nmse')


def fmt(point, ci, scale=1, digits=3):
    return f'{point * scale:.{digits}f} [{ci[0] * scale:.{digits}f}, {ci[1] * scale:.{digits}f}]'


def estimate(point, samples):
    return {'point': float(point), 'ci95': interval(samples)}


def sbl(root, rng, draws):
    archive = root / SBL_SOURCE
    if (archive / 'STATUS').read_text().strip() != 'DONE':
        raise ValueError(f'Incomplete archive: {archive}')
    config = json.loads((archive / 'config.json').read_text())['_config']
    frames = range(4800, 5000)
    snrs = (600, 700, 800, 900, 1000, 1100)
    scenarios = ('G', 'U')
    grid = {(sc, 300, snr, f) for sc in scenarios for snr in snrs for f in frames}
    if config['keys'] != len(grid):
        raise ValueError('SBL source configuration differs from the key grid')
    measures = np.empty((len(frames), len(snrs), len(scenarios), len(ARMS), len(METRICS)))
    failures = np.empty(measures.shape[:-1], dtype=bool)
    fingerprints = {}
    for wrapper in read_rows(archive):
        row = wrapper['row']
        key = tuple(wrapper['key'])
        scenario, rho, snr, frame = key
        if (key not in grid or tuple(row['key']) != key
                or tuple(row[field] for field in ('scenario', 'rho_permille', 'snr_centi_db', 'frame')) != key
                or row['family'] != 'P1' or set(row['variants']) != set(ARMS)
                or any(wrapper[field] != config[field] for field in
                       ('snapshot_sha256', 'producing_commit', 'freeze_commit', 'glue_commit'))):
            raise ValueError(f'Invalid or repeated SBL key: {key}')
        grid.remove(key)
        common = tuple(row['pairing'][field] for field in ('info_sha256', 'coded_sha256', 'noise_sha256'))
        if fingerprints.setdefault(frame, common) != common:
            raise ValueError(f'SBL exogenous pairing differs at {key}')
        base = (frame - frames.start, snrs.index(snr), scenarios.index(scenario))
        for a, arm in enumerate(ARMS):
            score = row['variants'][arm]
            fit = score['sbl']
            if (score['fer'] != int(score['info_errors'] > 0) or score['info_errors'] < 0
                    or score['n_pair'] != len(score['pairs']) or fit['max_iter'] != 100
                    or not 1 <= fit['iterations'] <= 100 or type(fit['converged']) is not bool
                    or not np.isfinite([fit['beta'], score['nmse']]).all()
                    or fit['beta'] <= 0 or score['nmse'] < 0):
                raise ValueError(f'Invalid SBL measurements at {key}/{arm}')
            measures[base + (a,)] = (fit['beta'], fit['converged'], fit['iterations'],
                                     score['n_pair'], score['nmse'])
            failures[base + (a,)] = score['fer']
    if grid:
        raise ValueError(f'Missing {len(grid)} SBL keys')
    if not (np.array_equal(measures[..., 1, :3], measures[..., 3, :3])
            and np.array_equal(measures[..., 2, :3], measures[..., 4, :3])):
        raise ValueError('SBL shared-fit arms disagree')

    # Each draw retains both scenarios and every SNR and arm on a sampled frame.
    weights = rng.multinomial(len(frames), np.full(len(frames), 1 / len(frames)), size=draws)
    by_frame = measures.mean(axis=2)
    point = by_frame.mean(axis=0)
    boot = (weights @ by_frame.reshape(len(frames), -1) / len(frames)).reshape(draws, *point.shape)
    strata = {}
    restored_lines = []
    table = ['| SNR (dB) | Arm | β mean | EM converged (%) | EM iterations (mean) | Co-delay pairs (mean, total) | NMSE mean |',
             '|---:|---|---:|---:|---:|---:|---:|']
    for i, snr in enumerate(snrs):
        data = {}
        for j, label in enumerate(ARMS.values()):
            estimates = {metric: estimate(point[i, j, k], boot[:, i, j, k])
                         for k, metric in enumerate(METRICS)}
            total = int(measures[:, i, :, j, 3].sum())
            estimates['total_co_delay_pairs'] = total
            values = [fmt(estimates[name]['point'], estimates[name]['ci95'], scale, digits)
                      for name, (scale, digits) in zip(METRICS, ((1, 3), (100, 1), (1, 2), (1, 2), (1, 4)))]
            values[3] += f' ({total:,})'
            table.append(f'| {snr / 100:g} | {label} | ' + ' | '.join(values) + ' |')
            data[label] = estimates

        restore = {}
        for k, name in ((0, 'beta'), (1, 'converged')):
            baseline, u2, kprime = point[i, [0, 1, 2], k]
            paired = boot[:, i, 2, k] - boot[:, i, 0, k]
            restore[name] = dict(k_minus_R0=estimate(kprime - baseline, paired),
                                 u2_minus_R0=float(u2 - baseline),
                                 closer=bool(abs(kprime - baseline) < abs(u2 - baseline)))
        beta, conv = (restore[name]['k_minus_R0'] for name in ('beta', 'converged'))
        restored_lines.append(
            f'- At {snr / 100:g} dB, K′−R0 is {fmt(beta["point"], beta["ci95"])} for β and '
            f'{fmt(conv["point"], conv["ci95"], 100, 1)} pp for convergence. '
            f'Closer to R0 than U2 for β? {"Yes" if restore["beta"]["closer"] else "No"}. '
            f'For convergence? {"Yes" if restore["converged"]["closer"] else "No"}.')
        strata[f'{snr / 100:g}'] = dict(n=400, arms=data, restoration=restore)

    beta_closer = sum(s['restoration']['beta']['closer'] for s in strata.values())
    conv_closer = sum(s['restoration']['converged']['closer'] for s in strata.values())
    b1 = dict(
        source=SBL_SOURCE,
        fields='`row.frame`, `snr_centi_db`, `scenario`, `row.variants[arm].sbl.{beta,converged,iterations}`, '
               '`n_pair` and `nmse`. Saved `K` and `KM` are K′ and KM′.',
        outcome='Descriptive',
        headline=f'K′ closer to R0 in β at {beta_closer}/6 SNRs and in convergence at {conv_closer}/6',
        report='Each stratum has 400 paired keys (200 physical frames × 2 scenarios). '
               'Brackets are frame-cluster bootstrap 95% intervals. Pair counts are output counts after refinement.\n\n'
               + '\n'.join(table)
               + '\n\nRestoration is described by distance to R0 and a paired K′−R0 interval. '
                 'The brief supplies no equivalence margin.\n\n' + '\n'.join(restored_lines),
        strata=strata,
    )

    eligible = failures[..., 1] & ~failures[..., 0]
    kfix, mfix = ~failures[..., 2], ~failures[..., 3]
    cells = [(False, False), (False, True), (True, False), (True, True)]
    by_frame = np.column_stack([(eligible & (kfix == k) & (mfix == m)).sum(axis=(1, 2)) for k, m in cells])
    counts = by_frame.sum(axis=0)
    n = int(counts.sum())
    if not n:
        raise ValueError('No eligible paired SBL failures')
    boot_counts = weights @ by_frame
    boot_totals = boot_counts.sum(axis=1)
    valid = boot_totals > 0
    probabilities = boot_counts[valid] / boot_totals[valid, None]
    off_diag = counts[1:3] / n
    outcome = ('Two mechanisms' if (off_diag >= .15).all() else
               'One mechanism' if (off_diag < .05).any() else 'Unresolved')
    table = ['| K′ fixes | M fixes | Keys | Fraction % [95% CI] |', '|---|---|---:|---:|']
    data = []
    for i, (k, m) in enumerate(cells):
        est = estimate(counts[i] / n, probabilities[:, i])
        table.append(f'| {k} | {m} | {counts[i]} | {fmt(est["point"], est["ci95"], 100, 1)} |')
        data.append(dict(K_fixes=k, M_fixes=m, n=int(counts[i]), **est))
    combined = int((eligible & ~failures[..., 4]).sum())
    b2 = dict(
        source=SBL_SOURCE,
        fields='`row.variants[arm].fer` is the archived `info_errors > 0` indicator. '
               'K′ and KM′ are saved as `K` and `KM`.',
        outcome=outcome,
        headline=f'K′-only {counts[2]}/{n} ({off_diag[1]:.1%}), M-only {counts[1]}/{n} ({off_diag[0]:.1%})',
        report=f'{n} keys fail under U2 and succeed under R0. Paired intervals resample physical frames. '
               f'{draws - len(probabilities)} draws had an empty eligible set. KM′ rescues {combined}/{n}.\n\n'
               + '\n'.join(table)
               + '\n\nThe cutoffs apply to the two off-diagonal point fractions.',
        eligible=n, cells=data, km_rescues=combined,
    )
    return {'R-B1': b1, 'R-B2': b2}


def median_summary(values, row_frames, weights):
    values = np.asarray(values)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Expected finite saved DD measurements')
    order = values.argsort()
    values = values[order]
    row_frames = np.asarray(row_frames)[order]
    boot = []
    for start in range(0, len(weights), 128):
        totals = weights[start:start + 128, row_frames].cumsum(axis=1)
        n = totals[:, -1:]
        valid = n[:, 0] > 0
        lower = (totals[valid] > (n[valid] - 1) // 2).argmax(axis=1)
        upper = (totals[valid] > n[valid] // 2).argmax(axis=1)
        boot.extend((values[lower] + values[upper]) / 2)
    return dict(n=len(values), median=float(np.median(values)), iqr=np.quantile(values, [.25, .75]).tolist(),
                ci95=interval(boot), nonempty_draws=len(boot))


def dd(root, rng, draws):
    archive = root / DD_SOURCE
    if (archive / 'STATUS').read_text().split()[0] != 'DONE':
        raise ValueError(f'Incomplete archive: {archive}')
    cfg = json.loads((archive / 'RUN_CONFIG.json').read_text())['_config']
    first, last = cfg['frame_range']
    selected_snrs = (450, 500, 550, 600)
    grid = {(frame, snr) for frame in range(first, last + 1) for snr in cfg['snr_centi_db']}
    if (cfg['expected_keys'] != len(grid) or not set(selected_snrs) <= set(cfg['snr_centi_db'])
            or (first, last) != (11000, 11999)):
        raise ValueError('DD source configuration differs from the expected key grid')
    groups = {'F0 undecoded / trigger': [], 'F0 decoded / no trigger': [],
              'Triggered / final failure': [], 'Triggered / final rescue': []}
    for row in read_rows(archive):
        frame, snr = row['frame'], row['snr_centi_db']
        grid.remove((frame, snr))
        if snr not in selected_snrs:
            continue
        arm = row['arms']['DD']['B']
        syndrome = arm['f0']['syndrome']
        triggered = syndrome > 0
        sigma2 = row['sigma2']
        residual, uncertainty = (arm['noise'][field] for field in ('residual_power', 'uncertainty_power'))
        if (syndrome < 0 or triggered != (arm['a1c'] is not None) or arm['info_errors'] < 0
                or not np.isfinite([sigma2, residual, uncertainty]).all()
                or sigma2 <= 0 or min(residual, uncertainty) < 0):
            raise ValueError(f'Invalid DD source metrics at {(frame, snr)}')
        ratios = (frame - first, residual / sigma2,
                  (residual - sigma2) / uncertainty if uncertainty > .05 * sigma2 else None)
        groups['F0 undecoded / trigger' if triggered else 'F0 decoded / no trigger'].append(ratios)
        if triggered:
            group = 'Triggered / final failure' if arm['info_errors'] > 0 else 'Triggered / final rescue'
            groups[group].append(ratios)
    if grid:
        raise ValueError(f'Missing {len(grid)} DD keys')
    n_frames = last - first + 1
    weights = rng.multinomial(n_frames, np.full(n_frames, 1 / n_frames), size=draws)
    results = {}
    table = ['| Cohort | r_norm n | r_norm median (IQR) [95% CI] | c_ratio n | c_ratio median (IQR) [95% CI] |',
             '|---|---:|---:|---:|---:|']
    for group, entries in groups.items():
        frames, residual, _ = zip(*entries)
        ratio_frames, ratios = zip(*[(frame, ratio) for frame, _, ratio in entries if ratio is not None])
        estimates = (median_summary(residual, frames, weights), median_summary(ratios, ratio_frames, weights))
        results[group] = dict(zip(('r_norm', 'c_ratio'), estimates))
        fields = [f'{e["n"]} | {e["median"]:.3f} ({e["iqr"][0]:.3f}–{e["iqr"][1]:.3f}) '
                  f'[{e["ci95"][0]:.3f}, {e["ci95"][1]:.3f}]' for e in estimates]
        table.append(f'| {group} | ' + ' | '.join(fields) + ' |')

    rule = results['F0 undecoded / trigger']
    r, c = rule['r_norm']['median'], rule['c_ratio']['median']
    overfit, dies = r < 1., c >= .80
    return dict(
        source=DD_SOURCE,
        fields='`frame`, `snr_centi_db`, `sigma2`, `arms.DD.B.f0.syndrome` and '
               '`arms.DD.B.noise.{residual_power,uncertainty_power}`. Final outcome uses `arms.DD.B.info_errors`.',
        outcome=('Overfitting criterion met' if overfit else 'Overfitting criterion missed')
                + (', cross-term claim dies' if dies else ', cross-term kill criterion missed'),
        headline=f'undecoded median r_norm {r:.3f}, c_ratio {c:.3f}',
        report='Pooled 4.5, 5.0, 5.5 and 6.0 dB. The cited agy I4 recipe stratifies by the syndrome '
               'after the second DD F0 round. Nonzero syndrome triggers continuation, and zero syndrome '
               'defines the decoded comparator. Within-trigger final failure and rescue are also shown to '
               'resolve the wording in the brief. r_norm uses all rows. c_ratio requires uncertainty power '
               'strictly greater than 0.05σ². Brackets are frame-cluster bootstrap intervals on medians.\n\n'
               + '\n'.join(table)
               + '\n\nBoth median cutoffs apply to the F0 undecoded trigger cohort. '
                 'The archived ratios do not directly isolate a residual cross term.',
        snr_centi_db=list(selected_snrs), groups=results,
        overfit_rule_met=overfit, cross_term_kill_rule_met=dies,
    )


def run(root, rng, draws):
    return dict(sbl(root, rng, draws), **{'R-F': dd(root, rng, draws)})
