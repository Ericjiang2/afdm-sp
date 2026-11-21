"""Validate frozen main receiver rows and report the registered readouts."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from statistics import mean
import sys

import numpy as np

from aggregate_main import aggregate
from gate_verdict import paired_interval
from main_schedule import s_keys

S_ARMS = ('R0', 'S-lo', 'G')
X_ARMS = ('F0', 'CD', 'G-ex')
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
P1_ENTROPY = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
P1_DOMAIN = str(0x54435246)
SHA256 = re.compile(r'[0-9a-f]{64}')
CONTRASTS = ('G − R0', 'S-lo − R0')
BLOCK_LABELS = ('2', '3–24', '25')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _count(value):
    return type(value) is int and value >= 0


def _fingerprint(record):
    data = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return sha256(data.encode()).hexdigest()


def _s_rows(rows):
    fingerprints = {}
    for row in rows:
        key = tuple(row['key'])
        scenario, rho, _, frame = key
        _require(row['family'] == 'P1' and tuple(row[field] for field in KEY_FIELDS) == key
                 and row['rng_entropy'] == P1_ENTROPY and row['rng_domain'] == P1_DOMAIN
                 and isfinite(row['sigma2']) and row['sigma2'] > 0
                 and set(row['variants']) == set(S_ARMS)
                 and 'error' not in row and row.get('status') not in ('error', 'failed'),
                 f'Invalid S receiver row at {key}')
        pair, inputs = row['pairing'], row['input_sha256']
        common = tuple(pair[k] for k in ('info_sha256', 'coded_sha256', 'noise_sha256'))
        signal = (pair['physical_gains_sha256'], inputs['pilot'], inputs['data_true'])
        for group, hashes in ((frame, common), ((scenario, rho, frame), signal)):
            _require(all(SHA256.fullmatch(digest) for digest in hashes)
                     and fingerprints.setdefault(group, hashes) == hashes,
                     f'Invalid or changed S exogenous hashes at {key}')
        for arm, score in row['variants'].items():
            errors, fit = score['info_errors'], score['sbl']
            _require(_count(errors) and type(score['fer']) is int and score['fer'] == int(errors > 0)
                     and score['decoded'] is (errors == 0)
                     and SHA256.fullmatch(score['decoded_sha256'])
                     and isfinite(score['nmse']) and score['nmse'] >= 0
                     and _count(score['n_pair']) and len(score['pairs']) == score['n_pair']
                     and fit['max_iter'] == 100 and _count(fit['iterations'])
                     and 1 <= fit['iterations'] <= 100 and type(fit['converged']) is bool
                     and isfinite(fit['beta']) and fit['beta'] > 0,
                     f'Invalid S FER or EM evidence at {key}/{arm}')
        blocks = row['gate_census']
        _require(bool(blocks) and sum(block['size'] for block in blocks) == row['n_candidates_stage2']
                 and type(row['projectors_equal']) is bool
                 and row['projectors_equal'] == all(block['projectors_equal'] for block in blocks),
                 f'Invalid S census or projector-equality flag at {key}')
        for block in blocks:
            size, gate, low = (block[k] for k in ('size', 'gate_rank', 's_lo_rank'))
            trace = block['overlap_trace']
            _require(all(map(_count, (size, gate, low))) and 1 <= size <= 25
                     and max(gate, low) <= size and -1e-10 <= trace <= min(gate, low) + 1e-10
                     and block['gate_in_s_lo'] is (abs(trace - gate) <= 1e-12)
                     and type(block['projectors_equal']) is bool,
                     f'Invalid S projector census at {key}/{block["delay"]}')


def _x_events(census):
    return dict(
        trial_firings=census['nonempty_trials'],
        local_pass_firings=sum(any(block['gate_rank'] > 0 for block in blocks)
                               for blocks in census['local_pass_blocks']),
        final_refit_firings=int(any(block['gate_rank'] > 0 for block in census['final_blocks'])),
    )


def _x_rows(rows, snr_db):
    for row in rows:
        frame = row['frame']
        _require(row['scenario'] == 'MIXED8' and row['snr_db'] == snr_db
                 and set(row['arms']) == set(row['arm_diagnostics']) == set(X_ARMS)
                 and SHA256.fullmatch(row['info_sha']) and SHA256.fullmatch(row['noise_sha'])
                 and 'error' not in row and row.get('status') not in ('error', 'failed'),
                 f'Invalid X receiver row at {frame}')
        diagnostics = row['arm_diagnostics']
        for arm, record in row['arms'].items():
            errors, diag = record['info_errors'], diagnostics[arm]
            flags = record['doublet_two_atoms']
            _require(_count(errors) and SHA256.fullmatch(record['decoded_sha'])
                     and type(diag['fer']) is int and diag['fer'] == int(errors > 0)
                     and diag['decoded'] is (errors == 0)
                     and set(flags) == {'0.35', '0.75'} and all(type(value) is bool for value in flags.values()),
                     f'Invalid X FER or representation evidence at {frame}/{arm}')
        for arm in ('CD', 'G-ex'):
            expected = _fingerprint(dict(record=row['arms'][arm], **diagnostics[arm]))
            _require(row['output_fingerprints'][arm] == expected,
                     f'X output fingerprint mismatch at {frame}/{arm}')
        census = row['gate_census']
        trials, total = census['nonempty_trials'], census['valid_trials']
        _require(_count(total) and _count(trials) and trials <= total and _count(census['active_refits']),
                 f'Invalid X firing counts at {frame}')
        if not any(_x_events(census).values()) and not census['active_refits']:
            _require(_x_identical(row), f'X outputs differ on a frame with empty projectors at {frame}')


def _x_identical(row):
    fingerprints = row['output_fingerprints']
    return fingerprints['CD'] == fingerprints['G-ex']


def _rate(values):
    failures = sum(values)
    return dict(failures=failures, fer=failures / len(values))


def _s_fer(rows):
    failures = {arm: [r['variants'][arm]['fer'] for r in rows] for arm in S_ARMS}
    frames = [r['key'][3] for r in rows]
    contrasts = {
        name: paired_interval(np.subtract(failures[arm], failures['R0']), frames)
        for arm, name in zip(('G', 'S-lo'), CONTRASTS, strict=True)
    }
    return dict(keys=len(rows), arms={arm: _rate(failures[arm]) for arm in S_ARMS}, contrasts=contrasts)


def _quartiles(values):
    if not values:
        return None
    return dict(zip(('q25', 'median', 'q75'), map(float, np.percentile(values, [25, 50, 75])), strict=True))


def _s_census(groups):
    cells = {}
    for label, rows in groups.items():
        by_size = defaultdict(list)
        for row in rows:
            for block in row['gate_census']:
                size = block['size']
                if size > 1:
                    bucket = str(size) if size in (2, 25) else '3–24'
                    by_size[bucket].append(block)
        cells[label] = {}
        for bucket in BLOCK_LABELS:
            blocks = by_size[bucket]
            if not blocks:
                continue
            positive = [b for b in blocks if b['s_lo_rank'] > 0]
            subset_count = sum(b['gate_in_s_lo'] for b in blocks)
            cells[label][bucket] = dict(
                blocks=len(blocks), gate_rank=_quartiles([b['gate_rank'] for b in blocks]),
                low_rank=_quartiles([b['s_lo_rank'] for b in blocks]),
                overlap_trace=_quartiles([b['overlap_trace'] for b in blocks]),
                overlap_fraction=_quartiles([b['overlap_trace'] / b['s_lo_rank'] for b in positive]),
                positive_low_rank_blocks=len(positive), subset_blocks=subset_count,
                subset_fraction=subset_count / len(blocks),
            )
    return cells


def _s_secondary(rows, primary):
    snrs, scenarios, cells = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        scenario, _, snr, _ = row['key']
        snrs[snr].append(row)
        scenarios[scenario].append(row)
        cells[(scenario, snr)].append(row)
    axes = [(f'{snr / 100:g}', group) for snr, group in sorted(snrs.items())]
    overall = _s_fer(rows)
    fer = dict(overall=overall['arms'], overall_contrasts=overall['contrasts'],
               by_snr_db={k: _s_fer(group) for k, group in axes},
               by_scenario={k: _s_fer(group) for k, group in sorted(scenarios.items())},
               by_scenario_snr_db={scenario: {
                   f'{snr / 100:g}': _s_fer(group)
                   for (cell_scenario, snr), group in sorted(cells.items()) if cell_scenario == scenario
               } for scenario in sorted(scenarios)})
    em = {}
    for arm in S_ARMS:
        scores = [row['variants'][arm] for row in rows]
        pairs = [s['n_pair'] for s in scores]
        em[arm] = dict(mean_beta=mean(s['sbl']['beta'] for s in scores),
                       mean_iterations=mean(s['sbl']['iterations'] for s in scores),
                       convergence_rate=mean(s['sbl']['converged'] for s in scores),
                       mean_output_co_delay_pairs=mean(pairs), total_output_co_delay_pairs=sum(pairs),
                       keys_with_output_co_delay_pairs=sum(p > 0 for p in pairs))
    return dict(fer=fer, gate_census=_s_census(dict(overall=rows, **dict(axes))), em=em,
                different_projector_keys=primary['n_keys'] - primary['same_projector_keys'],
                different_projector_fraction=1 - primary['same_projector_fraction'])


def _x_secondary(rows):
    frames = [row['frame'] for row in rows]
    failures = {arm: [row['arm_diagnostics'][arm]['fer'] for row in rows] for arm in X_ARMS}
    two_atoms = {}
    for arm in X_ARMS:
        two_atoms[arm] = {}
        for spacing in ('0.35', '0.75'):
            count = sum(row['arms'][arm]['doublet_two_atoms'][spacing] for row in rows)
            two_atoms[arm][spacing] = dict(frames=count, rate=count / len(rows))
    counts = [_x_events(row['gate_census']) for row in rows]
    return dict(
        fer={arm: _rate(failures[arm]) for arm in X_ARMS},
        gate_minus_cd=paired_interval(np.subtract(failures['G-ex'], failures['CD']), frames),
        byte_identical_frames=sum(_x_identical(row) for row in rows),
        firings={name: sum(entry[name] for entry in counts) for name in counts[0]},
        legal_trial_supports=sum(row['gate_census']['valid_trials'] for row in rows),
        two_atom_rate=two_atoms,
    )


def summarize(s_rows, x_rows, *, expected_s_keys, expected_x_frames, x_snr_db):
    _s_rows(s_rows)
    _x_rows(x_rows, x_snr_db)
    primary = aggregate(s_rows, x_rows, expected_s_keys=expected_s_keys, expected_x_frames=expected_x_frames)
    return dict(**primary, s_secondary=_s_secondary(s_rows, primary['s_leg']), x_secondary=_x_secondary(x_rows))


def _estimate(stats, *, scale=100):
    if stats['point'] is None:
        return 'unavailable'
    point, lo, hi = (stats[k] * scale for k in ('point', 'ci_lo', 'ci_hi'))
    return f'{point:.3f} [{lo:.3f}, {hi:.3f}]'


def _iq(stats, *, scale=1):
    if stats is None:
        return '—'
    q1, med, q3 = (stats[k] * scale for k in ('q25', 'median', 'q75'))
    return f'{med:.3f} [{q1:.3f}, {q3:.3f}]'


def _s_report(result):
    s = result['s_secondary']
    fer = s['fer']
    lines = [
        '### S leg',
        '',
        '| Stratum | Keys | R0 FER (%) | S-lo FER (%) | G FER (%) | G − R0 (pp) | S-lo − R0 (pp) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    groups = [('Overall', dict(keys=result['s_leg']['n_keys'], arms=fer['overall'],
                               contrasts=fer['overall_contrasts']))]
    groups += [(f'{snr} dB', group) for snr, group in fer['by_snr_db'].items()]
    groups += [(f'Scenario {scenario}', group) for scenario, group in fer['by_scenario'].items()]
    groups += [(f'{scenario}, {snr} dB', group)
               for scenario, by_snr in fer['by_scenario_snr_db'].items() for snr, group in by_snr.items()]
    for label, group in groups:
        rates = ' | '.join(f"{100 * group['arms'][arm]['fer']:.3f}" for arm in S_ARMS)
        estimates = ' | '.join(_estimate(group['contrasts'][name]) for name in CONTRASTS)
        lines.append(f"| {label} | {group['keys']:,} | {rates} | {estimates} |")
    lines.extend([
        '',
        'The contrasts use paired 95% percentile intervals with physical-frame clusters.',
        '',
        '| Arm | Output co-delay pairs, mean | Output pairs, total | Keys with pairs | Mean β | Mean iterations | Converged (%) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ])
    for arm, stats in s['em'].items():
        lines.append(
            f"| {arm} | {stats['mean_output_co_delay_pairs']:.3f} | {stats['total_output_co_delay_pairs']:,} | "
            f"{stats['keys_with_output_co_delay_pairs']:,} | {stats['mean_beta']:.6g} | "
            f"{stats['mean_iterations']:.3f} | {100 * stats['convergence_rate']:.3f} |"
        )
    p = result['retained_penalty']
    lines.extend([
        '',
        f"Projectors differ on {s['different_projector_keys']:,} keys "
        f"({100 * s['different_projector_fraction']:.3f}%). The retained penalty norm on S-lo's "
        f"post-pruning support is {_iq(p)} (median [quartiles]), with {p['zero_count']:,}/{p['keys']:,} exact zeros.",
        '',
        'Projector census for the registered block sizes. Entries are median [quartiles]. '
        'Normalized overlap divides the trace by the S-lo rank '
        'and uses blocks with positive S-lo rank. Subset fractions use all blocks in the listed size group.',
        '',
        '| SNR (dB) | Block size | Blocks | Gate rank | S-lo rank | Overlap trace | Overlap (%) | Gate subset (%) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for snr, by_size in s['gate_census'].items():
        for size, group in by_size.items():
            lines.append(
                f"| {snr} | {size} | {group['blocks']:,} | {_iq(group['gate_rank'])} | {_iq(group['low_rank'])} | "
                f"{_iq(group['overlap_trace'])} | {_iq(group['overlap_fraction'], scale=100)} | "
                f"{100 * group['subset_fraction']:.3f} |"
            )
    return lines


def _x_report(result):
    x = result['x_secondary']
    lines = [
        '### X leg',
        '',
        '| Arm | Failures | FER (%) | 0.35-bin two-atom rate (%) | 0.75-bin two-atom rate (%) |',
        '|---|---:|---:|---:|---:|',
    ]
    for arm, rate in x['fer'].items():
        q = x['two_atom_rate'][arm]
        lines.append(f"| {arm} | {rate['failures']} | {100 * rate['fer']:.3f} | "
                     f"{100 * q['0.35']['rate']:.3f} | {100 * q['0.75']['rate']:.3f} |")
    overall, denom = x['firings'], result['x_gate_exposure']
    lines.extend([
        '',
        f"G-ex − CD FER is {_estimate(x['gate_minus_cd'])} pp (paired 95% interval). "
        f"{x['byte_identical_frames']}/{result['x_leg']['n_frames']} rows are byte-identical.",
        '',
        '| Frames | Legal trial firings | Local-pass entry firings | Final refit firings |',
        '|---|---:|---:|---:|',
        f"| All | {overall['trial_firings']:,} / {x['legal_trial_supports']:,} | "
        f"{overall['local_pass_firings']:,} | {overall['final_refit_firings']:,} |",
        f"| CD-resolved ({denom['cd_resolved_frames']}) | {denom['trial_firings']:,} | "
        f"{denom['local_pass_firings']:,} | {denom['final_refit_firings']:,} |",
    ])
    return lines


def _render(result):
    s, x = result['s_leg'], result['x_leg']
    freeze = result['_config']['freeze_commit']
    lines = [
        '# Gate SBL test',
        '',
        '## Observation',
        '',
        f"Frozen protocol `{freeze}`. S uses {s['n_keys']:,} keys in "
        f"{s['n_frame_clusters']:,} physical-frame clusters. X uses {x['n_frames']:,} MIXED8 frames.",
        '',
        *_s_report(result),
        '',
        *_x_report(result),
        '',
        '## Frozen verdict',
        '',
        '| Endpoint | Estimate [95% bounds] | Verdict |',
        '|---|---|---|',
        f"| S Δ (pp) | {_estimate(s)} | {s['verdict']} |",
        f"| X losses among CD-resolved frames (%) | {x['lost_frames']}/{x['cd_resolved_frames']}, "
        f"{_estimate(x)} | {x['verdict']} |",
        f"| Joint | — | {result['joint']} |",
        '',
        'X uses exact Clopper–Pearson bounds with a 97.5% one-sided level for each tail.',
        '',
        f"The S validity check {'passed' if s['valid'] else 'failed'}. "
        f"The S equivalence label is `{s['equivalent']}`. "
        f"The S flags `lower_positive` and `upper_negative` are `{s['lower_positive']}` and "
        f"`{s['upper_negative']}`, respectively. The X flag `leverage_insufficient` is "
        f"`{x['leverage_insufficient']}`.",
    ]
    if result['joint'] == 'supported':
        lines.extend(['', 'The S excess upper bound is below 1 pp. The loss upper bound among '
                      'CD-resolved 0.35-bin doublets is below 5% in the registered X setting.'])
    elif result['joint'] == 'not_supported':
        lines.extend(['', 'The one-rule claim was not supported under the frozen rule and endpoints.'])
    lines.extend(['', '## Untested', '', 'The mechanism behind the measured receiver outcomes remains untested.'])
    return '\n'.join(lines) + '\n'


def _rows(path):
    with path.open() as source:
        return [json.loads(line) for line in source]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    config = json.loads((out / 'config.json').read_text())
    schedule = config['_config']['main_schedule']
    first, last = schedule['x_segment']
    result = summarize(_rows(out / 's_rows.jsonl'), _rows(out / 'x_rows.jsonl'),
                       expected_s_keys=s_keys(schedule['s_segments']),
                       expected_x_frames=range(first, last + 1), x_snr_db=schedule['x_snr_db'])
    result.update(config)
    result['aggregation_argv'] = sys.argv
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n'
    markdown = _render(result)
    with (out / 'results.json').open('x') as destination:
        destination.write(text)
    with (out / 'RESULTS.md').open('x') as destination:
        destination.write(markdown)


if __name__ == '__main__':
    main()
