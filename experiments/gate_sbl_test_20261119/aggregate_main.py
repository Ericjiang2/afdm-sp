"""Aggregate paired SBL and MIXED8 rows under PROTOCOL §3 and §8."""

import numpy as np

from gate_verdict import readout


def s_penalty_summary(rows):
    """Summarize the initial penalty difference restricted to S-lo's retained indices."""
    norms = np.array([row['slo_retained_penalty_fro'] for row in rows], dtype=float)
    if not norms.size or norms.ndim != 1 or not np.isfinite(norms).all() or np.any(norms < 0):
        raise ValueError('Expected one finite nonnegative retained-penalty norm per S key')
    q25, median, q75 = map(float, np.percentile(norms, [25, 50, 75]))
    zero_count = int(np.count_nonzero(norms == 0))
    return dict(keys=len(norms), median=median, q25=q25, q75=q75,
                zero_count=zero_count, fraction_exactly_zero=zero_count / len(norms))


def _resolved(row, arm):
    resolved = row['arm_diagnostics'][arm]['resolution_035']['resolved']
    if type(resolved) is not bool:
        raise ValueError(f'Missing boolean resolution outcome at {row["frame"]}/{arm}')
    return resolved


def x_gate_exposure(rows):
    """Count nonempty projectors at each construction point among CD-resolved frames."""
    denominator_frames = trial_firings = local_pass_firings = final_refit_firings = 0
    for row in rows:
        if not _resolved(row, 'CD'):
            continue
        denominator_frames += 1
        census = row['gate_census']
        trials = census['nonempty_trials']
        if type(trials) is not int or not 0 <= trials <= census['valid_trials']:
            raise ValueError(f'Invalid legal trial firing count on X frame {row["frame"]}')
        trial_firings += trials
        local_pass_firings += sum(any(block['gate_rank'] > 0 for block in blocks)
                                  for blocks in census['local_pass_blocks'])
        final_refit_firings += any(block['gate_rank'] > 0 for block in census['final_blocks'])
    return dict(cd_resolved_frames=denominator_frames, trial_firings=trial_firings,
                local_pass_firings=local_pass_firings, final_refit_firings=final_refit_firings)


def _s_failed(row, arm):
    score = row['variants'][arm]
    errors, failed = score['info_errors'], score['fer']
    if type(errors) is not int or errors < 0 or type(failed) is not int or failed != int(errors > 0):
        raise ValueError(f'Invalid FER inputs at {row["key"]}/{arm}')
    return failed


def aggregate(s_rows, x_rows, *, expected_s_keys, expected_x_frames):
    """Check both schedules and resample all S settings of each physical frame together."""
    s_rows, x_rows = list(s_rows), list(x_rows)
    s_keys = [tuple(row['key']) for row in s_rows]
    x_frames = [row['frame'] for row in x_rows]
    if len(set(s_keys)) != len(s_keys) or set(s_keys) != set(map(tuple, expected_s_keys)):
        raise ValueError('S rows do not cover the expected paired key schedule exactly once')
    if len(set(x_frames)) != len(x_frames) or set(x_frames) != set(expected_x_frames):
        raise ValueError('X rows do not cover the expected paired frame schedule exactly once')

    result = readout(
        [_s_failed(row, 'G') for row in s_rows],
        [_s_failed(row, 'S-lo') for row in s_rows],
        [key[3] for key in s_keys],
        [row['projectors_equal'] for row in s_rows],
        [_resolved(row, 'CD') for row in x_rows],
        [_resolved(row, 'G-ex') for row in x_rows],
    )
    return dict(result, retained_penalty=s_penalty_summary(s_rows), x_gate_exposure=x_gate_exposure(x_rows))
