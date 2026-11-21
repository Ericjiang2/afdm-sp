"""Aggregate the frozen SBL spectral split from a complete main-run directory."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import bootstrap_means, linear_summary, ratio_summary  # noqa: E402

ARMS = ('R0', 'R1', 'R2', 'S0', 'T0', 'S-lo', 'S-hi', 'S-isolo', 'S-isohi')
EXTENDED = ('R1', 'S0', 'S-lo', 'S-hi')
MAIN_FRAMES = range(4000, 4100)
EXTENDED_FRAMES = range(4000, 4050)
SCENARIOS = ('U', 'G')
SNRS = range(600, 1200, 100)
DRAWS = 20_000
SEED = 20261119
SHAPE_MARGIN = .01
MAIN_KEYS = {(scenario, 300, snr, frame)
             for scenario in SCENARIOS for snr in SNRS for frame in MAIN_FRAMES}
FINGERPRINTS = ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256')
DIAGNOSTICS = ('beta', 'iterations', 'atoms_em_end', 'atoms_output', 'co_delay_pairs',
               'added_trace_sbl', 'added_trace_refinement', 'nmse')
SUPPORT = 'Intervention-level support'
LOW_ONLY_INSUFFICIENT = 'Low-half-only account does not hold'
UNESTABLISHED = 'Not established'
PREDICTIONS = {SUPPORT: .25, LOW_ONLY_INSUFFICIENT: .35, UNESTABLISHED: .40}
PROJECTOR = 'Projector shape superior'
EQUIVALENT = 'Equivalent within 1 pp'
ISOTROPIC = 'Isotropic shape superior'
UNCERTAIN = 'Uncertain'
CARRIES = 'Carries recovery'
INSUFFICIENT = 'Insufficient alone'
UNEVALUABLE = 'Unevaluable'


def cluster(row):
    return row['rng_entropy'], row['rng_domain'], row['key'][3]


def validate_arm(arm, budget, candidates):
    sbl = arm['sbl']
    n_atoms = arm['n_atoms']
    errors, fer = arm['info_errors'], arm['fer']
    counts = (errors, n_atoms, arm['n_pair'], sbl['n_final'], sbl['iterations'])
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError('invalid decoder or SBL counts')
    if type(fer) is not int or fer != int(errors > 0):
        raise ValueError('FER and decoded error count disagree')
    if not (1 <= n_atoms <= sbl['n_final'] <= candidates):
        raise ValueError('invalid active-set/output atom counts')
    if arm['n_pair'] > n_atoms * (n_atoms - 1) // 2:
        raise ValueError('invalid co-delay pair count')
    if sbl['max_iter'] != budget or not (1 <= sbl['iterations'] <= budget):
        raise ValueError('wrong SBL iteration budget')
    if type(sbl['converged']) is not bool or not math.isfinite(sbl['beta']) or sbl['beta'] <= 0:
        raise ValueError('invalid EM status or precision')
    for field in ('nmse', 'added_trace_sbl', 'added_trace_refinement'):
        if not math.isfinite(arm[field]) or arm[field] < 0:
            raise ValueError(f'invalid {field}')


def load_rows(out, config, config_sha256):
    workers = config['workers']
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError(f'invalid worker count: {workers}')
    files = sorted(out.glob('rows_shard*.jsonl'))
    if [p.name for p in files] != [f'rows_shard{index:03d}.jsonl' for index in range(workers)]:
        raise ValueError('raw shard names or count do not match the run configuration')

    rows, fingerprints = {}, {}
    for path in files:
        with path.open() as handle:
            for index, line in enumerate(handle, start=1):
                try:
                    row = json.loads(line)
                    key = tuple(row['key'])
                    if key not in MAIN_KEYS or key in rows:
                        raise ValueError(f'duplicate or unexpected key: {key}')
                    if row['status'] != 'ok' or row['config_sha256'] != config_sha256:
                        raise ValueError('failed row or run configuration mismatch')
                    budgets = {'100': ARMS}
                    if key[3] in EXTENDED_FRAMES:
                        budgets['400'] = EXTENDED
                    if set(row['budgets']) != set(budgets):
                        raise ValueError(f'wrong budgets for {key}')
                    for budget, arms in budgets.items():
                        variants = row['budgets'][budget]
                        if set(variants) != set(arms):
                            raise ValueError(f'wrong arms for {key} at {budget} iterations')
                        for arm in variants.values():
                            validate_arm(arm, int(budget), row['n_candidates_stage2'])

                    total = row['census']['eigenvalues_total']
                    ambiguous = row['census']['eigenvalues_in_025_075']
                    if (type(total) is not int or total != row['n_candidates_stage2']
                            or type(ambiguous) is not int or not 0 <= ambiguous <= total):
                        raise ValueError('invalid candidate eigenvalue census')
                    group = cluster(row)
                    if any(not isinstance(item, str) or not item for item in group[:2]):
                        raise ValueError('missing RNG identity')
                    exogenous = tuple(row['pairing'][field] for field in FINGERPRINTS)
                    if any(not isinstance(value, str) or len(value) != 64 for value in exogenous):
                        raise ValueError('invalid exogenous fingerprint')
                    if fingerprints.setdefault(group, exogenous) != exogenous:
                        raise ValueError(f'exogenous hashes differ within cluster {group}')
                    rows[key] = row
                except (KeyError, ValueError, TypeError) as exc:
                    raise ValueError(f'{path.name}:{index}: {exc}') from exc
    if set(rows) != MAIN_KEYS:
        raise ValueError(f'incomplete main key set: {len(rows)}/{len(MAIN_KEYS)}')
    if len(fingerprints) != len(MAIN_FRAMES):
        raise ValueError(f'expected one physical RNG cluster per frame, got {len(fingerprints)}')
    return [rows[key] for key in sorted(rows)]


def bootstrap(values, rows):
    clusters = [':'.join(map(str, cluster(row))) for row in rows]
    point = {name: statistics.mean(column) for name, column in values.items()}
    draws, count = bootstrap_means(values, clusters, n_boot=DRAWS, seed=SEED)
    return point, draws, count


def contrasts(point, draws):
    g = {'R1': 1, 'R2': -1}
    gs = {'R1': 1, 'S0': -1}
    metrics = {
        'G': linear_summary(point, draws, g),
        'G_s': linear_summary(point, draws, gs),
        's': ratio_summary(point, draws, gs, g),
        't': ratio_summary(point, draws, {'R1': 1, 'T0': -1}, g),
        'I': ratio_summary(point, draws, {'S0': 1, 'T0': 1, 'R1': -1, 'R2': -1}, g),
        'delta_lo': linear_summary(point, draws, {'S-isolo': 1, 'S-lo': -1}),
        'delta_hi': linear_summary(point, draws, {'S-isohi': 1, 'S-hi': -1}),
    }
    for half in ('lo', 'hi', 'isolo', 'isohi'):
        metrics[f'f_{half}'] = ratio_summary(point, draws, {'R1': 1, f'S-{half}': -1}, gs)
    return metrics


def shape_class(ci):
    lo, hi = ci['ci_lo'], ci['ci_hi']
    equivalent = -SHAPE_MARGIN <= lo <= hi <= SHAPE_MARGIN
    # §7.3 lists superiority, equivalence, then isotropic superiority.
    # The numerical predicates can overlap for an interval strictly on one
    # side of zero inside the margin. Retain the listed order and report overlap.
    if lo > 0:
        return PROJECTOR, equivalent
    if equivalent:
        return EQUIVALENT, hi < 0
    if hi < 0:
        return ISOTROPIC, False
    return UNCERTAIN, False


def frozen_verdicts(metrics):
    s, t = metrics['s'], metrics['t']
    stage = 'INCONCLUSIVE'
    if s['evaluable'] and t['evaluable']:
        if s['ci_lo'] >= .5 and t['ci_hi'] <= .25:
            stage = 'SBL'
        elif t['ci_lo'] >= .5 and s['ci_hi'] <= .25:
            stage = 'REFINEMENT'
        elif s['ci_lo'] >= .25 and t['ci_lo'] >= .25:
            stage = 'SHARED'

    def half_class(ci):
        if not ci['evaluable']:
            return UNEVALUABLE
        if ci['ci_lo'] >= .5:
            return CARRIES
        if ci['ci_hi'] <= .25:
            return INSUFFICIENT
        return UNCERTAIN

    lo, hi = (half_class(metrics[f'f_{half}']) for half in ('lo', 'hi'))
    delta_lo, overlap_lo = shape_class(metrics['delta_lo'])
    delta_hi, overlap_hi = shape_class(metrics['delta_hi'])
    if stage == 'SBL' and lo == CARRIES and hi == INSUFFICIENT and delta_lo == PROJECTOR:
        candidate = SUPPORT
    elif stage == 'REFINEMENT' or lo == INSUFFICIENT:
        candidate = LOW_ONLY_INSUFFICIENT
    else:
        candidate = UNESTABLISHED
    return dict(stage=stage, lo=lo, hi=hi, delta_lo=delta_lo, delta_hi=delta_hi, candidate=candidate,
                shape_equivalence_overlap={'delta_lo': overlap_lo, 'delta_hi': overlap_hi})


def prediction_score(candidate):
    probabilities = PREDICTIONS
    return dict(probabilities=probabilities, observed=candidate,
                brier=sum((prob - (outcome == candidate)) ** 2 for outcome, prob in probabilities.items()),
                log_loss=-math.log(probabilities[candidate]))


def variant_diagnostics(variants):
    sbl = [variant['sbl'] for variant in variants]
    return dict(
        beta=statistics.mean(row['beta'] for row in sbl),
        iterations=statistics.mean(row['iterations'] for row in sbl),
        converged_count=sum(row['converged'] for row in sbl),
        atoms_em_end=statistics.mean(row['n_final'] for row in sbl),
        atoms_output=statistics.mean(item['n_atoms'] for item in variants),
        co_delay_pairs=statistics.mean(item['n_pair'] for item in variants),
        total_co_delay_pairs=sum(item['n_pair'] for item in variants),
        **{field: statistics.mean(item[field] for item in variants)
           for field in ('added_trace_sbl', 'added_trace_refinement', 'nmse')},
    )


def summarize(rows):
    primary = {arm: [row['budgets']['100'][arm] for row in rows] for arm in ARMS}
    values = {arm: [item['fer'] for item in variants] for arm, variants in primary.items()}
    point, draws, count = bootstrap(values, rows)
    fer = {arm: dict(failures=sum(values[arm]), **linear_summary(point, draws, {arm: 1})) for arm in ARMS}
    metrics = contrasts(point, draws)
    verdicts = frozen_verdicts(metrics)

    cells = defaultdict(list)
    for row in rows:
        cells[row['key'][0], row['key'][2]].append(row)
    cell_fer = {f'{scenario}/{snr / 100:g}': {arm: statistics.mean(row['budgets']['100'][arm]['fer']
                                                                   for row in subset)
                                                   for arm in ARMS}
                for (scenario, snr), subset in cells.items()}

    extended = [row for row in rows if row['key'][3] in EXTENDED_FRAMES]
    ext_variants = {
        f'{arm}/{budget}': [row['budgets'][budget][arm] for row in extended]
        for arm in EXTENDED for budget in ('100', '400')
    }
    ext_values = {name: [item['fer'] for item in variants] for name, variants in ext_variants.items()}
    ext_point, ext_draws, ext_count = bootstrap(ext_values, extended)
    ext_fer = {
        arm: {
            '100': linear_summary(ext_point, ext_draws, {f'{arm}/100': 1}),
            '400': linear_summary(ext_point, ext_draws, {f'{arm}/400': 1}),
            'change': linear_summary(ext_point, ext_draws, {f'{arm}/400': 1, f'{arm}/100': -1}),
            'diagnostics_400': variant_diagnostics(ext_variants[f'{arm}/400']),
        }
        for arm in EXTENDED
    }
    total = sum(row['census']['eigenvalues_total'] for row in rows)
    ambiguous = sum(row['census']['eigenvalues_in_025_075'] for row in rows)
    return dict(n_keys=len(rows), n_clusters=count, per_arm_fer=fer, contrasts=metrics,
                diagnostics={name: variant_diagnostics(variants) for name, variants in primary.items()},
                per_cell_fer=cell_fer, verdicts=verdicts, predictions=prediction_score(verdicts['candidate']),
                extended=dict(n_keys=len(extended), n_clusters=ext_count, frames=[4000, 4049], arms=ext_fer),
                census=dict(eigenvalues_total=total, eigenvalues_in_025_075=ambiguous, share=ambiguous / total))


def estimate(metric):
    if not metric.get('evaluable', True):
        return f"Unevaluable ({metric['denominator_nonpositive_fraction']:.2%} nonpositive draws)"
    return f"{metric['point']:.5f} [{metric['ci_lo']:.5f}, {metric['ci_hi']:.5f}]"


def diagnostics_table(arms):
    return [
        '| Arm | Mean β | Mean iterations | Converged | Mean EM-end atoms | Mean output atoms | Mean co-delay pairs | Mean EM added trace | Mean refinement added trace | Mean NMSE |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        *('| ' + ' | '.join([arm, *(f"{row[name]:.6g}" for name in DIAGNOSTICS[:2]),
                              str(row['converged_count']), *(f"{row[name]:.6g}" for name in DIAGNOSTICS[2:])]) + ' |'
          for arm, row in arms.items()),
    ]


def render(result):
    fer, contrasts_ = result['per_arm_fer'], result['contrasts']
    ext, census = result['extended'], result['census']
    verdict = result['verdicts']
    lines = [
        '# SBL spectral split, Phase 2', '', '## Observation', '',
        f"{result['n_keys']:,} paired keys in {result['n_clusters']} physical-frame clusters. "
        f"95% percentile intervals use {DRAWS:,} paired cluster draws with seed {SEED}. "
        'The 100-iteration R0/R1/R2 outcomes are joined from verified E-3c rows. '
        f"The receiver receipt records {result['receiver_core_hours']:.2f} core-hours.", '',
        '| Arm | Frame errors | FER [95% CI] |', '|---|---:|---:|',
        *(f"| {arm} | {item['failures']} | {estimate(item)} |" for arm, item in fer.items()), '',
        '| Contrast | Estimate [95% CI] |', '|---|---:|',
        *(f"| {name} | {estimate(contrasts_[name])} |"
          for name in ('G', 's', 't', 'I', 'G_s', 'f_lo', 'f_hi', 'f_isolo', 'f_isohi', 'delta_lo', 'delta_hi')), '',
        f"Eigenvalues in [.25, .75] account for {census['eigenvalues_in_025_075']:,}/"
        f"{census['eigenvalues_total']:,} ({census['share']:.2%}) across the initial candidate sets.", '',
        '### Receiver diagnostics, 100 iterations', '', *diagnostics_table(result['diagnostics']), '',
        '### Per-cell FER, 100 iterations', '',
        '| Scenario / SNR (dB) | ' + ' | '.join(ARMS) + ' |',
        '|---|' + '---:|' * len(ARMS),
        *('| ' + ' | '.join([cell, *(f'{rates[arm]:.3f}' for arm in ARMS)]) + ' |'
          for cell, rates in result['per_cell_fer'].items()), '',
        '### 400-iteration subset', '',
        f"Frames 4000–4049 contribute {ext['n_keys']} keys in {ext['n_clusters']} clusters. "
        'The 100-iteration column uses the same keys. Differences are 400 minus 100.', '',
        '| Arm | 100-iteration FER [95% CI] | 400-iteration FER [95% CI] | Difference [95% CI] |',
        '|---|---:|---:|---:|',
        *(f"| {arm} | {estimate(item['100'])} | {estimate(item['400'])} | {estimate(item['change'])} |"
          for arm, item in ext['arms'].items()), '',
        *diagnostics_table({arm: item['diagnostics_400'] for arm, item in ext['arms'].items()}), '',
        '## Frozen verdicts', '',
        '§7 governs the 100-iteration classifications. Ratio intervals use positive-denominator draws. '
        'A nonpositive point denominator or more than 1% nonpositive draws makes a ratio unevaluable.', '',
        '| Test | Verdict |', '|---|---|',
        *(f"| {label} | {verdict[field]} |" for field, label in [
            ('stage', 'Stage'), ('lo', 'Low half'), ('hi', 'High half'), ('delta_lo', 'Δ_lo'),
            ('delta_hi', 'Δ_hi'), ('candidate', 'Candidate')
        ]), '',
    ]
    for name, overlap in verdict['shape_equivalence_overlap'].items():
        if overlap:
            lines.append(f"The {name} interval satisfies both a sign criterion and the 1 pp margin. "
                         'The verdict uses the first applicable criterion in the written §7 order.')
    if any(verdict['shape_equivalence_overlap'].values()):
        lines.append('')
    p = result['predictions']
    lines.extend([
        '### Claude’s §7.4 prediction score', '',
        '| Candidate outcome | Forecast | Observed |', '|---|---:|---:|',
        *(f"| {outcome} | {prob:.0%} | {int(outcome == p['observed'])} |"
          for outcome, prob in p['probabilities'].items()), '',
        f"Multiclass Brier score (sum of squared errors) {p['brier']:.4f}. "
        f"Natural-log loss {p['log_loss']:.4f}.", '',
    ])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = sys.argv[1:] if argv is None else argv
    out = parser.parse_args(args).out
    config_path = out / 'config.json'
    config_bytes = config_path.read_bytes()
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    envelope = json.loads(config_bytes)
    rows = load_rows(out, envelope['_config'], config_sha256)
    receiver_receipt = json.loads((out / 'receiver_receipt.json').read_bytes())
    result = summarize(rows)
    result.update(receiver_core_hours=receiver_receipt['receiver_core_hours'],
                  _argv=[str(Path(__file__).resolve()), *args], _config=dict(
        run_config_sha256=config_sha256, run=envelope, receiver_receipt=receiver_receipt,
        bootstrap=dict(draws=DRAWS, seed=SEED, ci='percentile 95%',
                       cluster='RNG entropy/domain/frame; joint scenarios and SNR'),
        ratio_failure_limit=.01, shape_margin=SHAPE_MARGIN, primary_max_iter=100,
        shape_order=[PROJECTOR, EQUIVALENT, ISOTROPIC, UNCERTAIN],
    ))
    with (out / 'results.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    with (out / 'RESULTS.md').open('x') as handle:
        handle.write(render(result))


if __name__ == '__main__':
    main()
