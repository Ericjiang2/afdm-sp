"""Registered, saved-score-only diagnosis. Does not call any estimator or RNG."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, thread_binding
from .audit import file_hash


def candidate_diagnosis(fourth, likelihood, truth, selected):
    values = fourth.ravel()
    indices = np.arange(len(values))
    rank = 1+np.count_nonzero(values > values[truth])+np.count_nonzero((values == values[truth]) & (indices < truth))
    wrong = likelihood[indices != truth]
    return dict(truth_fourth_rank=int(rank), truth_minus_best_wrong=float(likelihood[truth]-wrong.max()),
                selected_is_truth=bool(selected == truth))


def calculate(output, input_root):
    pilot = Path(input_root)/'execution/P'
    if json.loads((pilot/'attempt.json').read_text())['status'] != 'complete':
        raise ValueError('complete immutable pilot required')
    records = json.loads((pilot/'records.json').read_text())
    if [r['group'] for r in records] != list(range(256)):
        raise ValueError('all original groups required')
    rows = []
    for row in records:
        n, delay = row['N'], row['delay']
        a = (row['cfo']+5*delay) % n
        truth = a*(n//4)+delay
        path = pilot/row['estimates_path']
        if not path.resolve().is_relative_to(pilot.resolve()) or file_hash(path) != row['estimates_sha256']:
            raise ValueError('saved-score path/hash mismatch')
        with np.load(path, allow_pickle=False) as source:
            for arm in ('current', 'quadratic', 'random'):
                answer = row['estimates'][f'{arm}_FULL']
                selected = answer['a']*(n//4)+answer['delay']
                item = candidate_diagnosis(source[f'{arm}_FOURTH_fourth_scores'],
                                           source[f'{arm}_FULL_profile_scores'], truth, selected)
                rows.append(dict(group=row['group'], N=n, snr_db=row['snr_db'], arm=arm,
                                 delta_a=(answer['a']-a) % n, delta_delay=(answer['delay']-delay) % (n//4),
                                 gain_magnitude=float(np.hypot(*row['gain'])), **item))
    cells = []
    for n in (32, 64):
        for snr in (5, 15):
            arms = {}
            for arm in ('current', 'quadratic', 'random'):
                selected = [r for r in rows if (r['N'], r['snr_db'], r['arm']) == (n, snr, arm)]
                wrong = [r for r in selected if not r['selected_is_truth']]
                histogram = Counter((r['delta_a'], r['delta_delay']) for r in wrong)
                arms[arm] = dict(groups=len(selected), full_errors=len(wrong),
                    truth_outside32=sum(r['truth_fourth_rank'] > 32 for r in selected),
                    full_correct_but_truth_outside32=sum(r['truth_fourth_rank'] > 32 and r['selected_is_truth'] for r in selected),
                    fourth_rank_quantiles=np.quantile([r['truth_fourth_rank'] for r in selected], [0, .5, .9, 1]).tolist(),
                    likelihood_margin_quantiles=np.quantile([r['truth_minus_best_wrong'] for r in selected], [0, .5, .9, 1]).tolist(),
                    error_displacements=[dict(delta_a=k[0], delta_delay=k[1], count=v) for k, v in sorted(histogram.items())])
            cells.append(dict(N=n, snr_db=snr, arms=arms))
    result = dict(new_observations=0, geometry_probes=0, acquisition_calls=0,
                  source_records_sha256=file_hash(pilot/'records.json'), diagnosed_groups=256,
                  cells=cells, scope='Descriptive saved-score diagnosis; all original cells retained; no new uncertainty or performance claim')
    dump(output/'diagnostic_rows.json', rows)
    dump(output/'diagnosis.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--artifact-root', type=Path, required=True)
    args = parser.parse_args()
    _ = thread_binding.blas_binding
    pilot = args.input_root/'execution/P'
    records = json.loads((pilot/'records.json').read_text())
    sources = [pilot/'records.json', pilot/'attempt.json', *[pilot/r['estimates_path'] for r in records]]

    def callback(output):
        return calculate(output, args.input_root)

    protocol.run('S', dict(seed=0, new_observations=0, new_geometry_probes=0, receiver_calls=0,
                          decoder_calls=0, new_confirmation_stream=False, phase='saved_diagnosis'),
                 sources, callback, artifact_root=args.artifact_root.resolve(), wall_seconds=60)


if __name__ == '__main__':
    main()
