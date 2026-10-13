"""Registered independent calibration/evaluation of observed-only methods.

Truth is consumed only by the continuous actual generator and downstream
reporting. All inference calls receive exactly (Y, public method config).
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_method_advantage import methods
from experiments.afdm_method_advantage.protocol import ROOT, ARTIFACT, dump, run
from experiments.afdm_higher_order_information.prior import frozen_components

CONFIG_PATH = ARTIFACT / 'METHOD_CONFIG.json'


def plain(value):
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError('nonfinite research output must be classified explicitly')
    return value


def specification(mode, condition, config):
    if mode == 'qualification':
        if condition != 0:
            raise ValueError('qualification has a single registered bundle')
        points = [config['null_points'][2], config['evaluation_points'][10]]
        return points, 4, 0
    key = {'calibration': 'null_points', 'evaluation': 'evaluation_points'}[mode]
    if condition < 0 or condition >= len(config[key]):
        raise ValueError('condition outside frozen point list')
    return [config[key][condition]], config[mode + '_groups'], 1 if mode == 'calibration' else 2


def calculate(output):
    cfg = json.loads(CONFIG_PATH.read_text())
    points, groups, split_id = specification(ARGS.mode, ARGS.condition, cfg)
    max_r = max(cfg['repeats'])
    generator = ActualPrior(n=4, model='g0', pdp='marginal')
    count = 0
    all_records, generation = [], []
    for local_index, point in enumerate(points):
        theta = [point['delta'], point['mu'], np.log(point['tau']), np.log(point['sigma2'])]
        seed = [*cfg['seed'], split_id, ARGS.condition, local_index]
        before = time.perf_counter()
        y = generator.sample(theta, groups * max_r, seed)
        generation.append(dict(point=point, seed=seed, seconds=time.perf_counter()-before,
                               branch=plain(generator.branch(theta)['signature'])))
        np.savez_compressed(output / f'observations_{local_index:02d}.npz',
                            y=y, theta=np.array(theta), seed=np.array(seed))
        count += len(y)
        for group in range(groups):
            for repeat in cfg['repeats']:
                observed = y[group * max_r:group * max_r + repeat]
                before = time.perf_counter()
                result = methods.evaluate_methods(observed, cfg['method_config'])
                complete_seconds = time.perf_counter() - before
                all_records.append(dict(local_condition=local_index, group=group,
                                        repeats=repeat, complete_seconds=complete_seconds,
                                        **plain(result)))
            # Preserve complete inference records during the admitted attempt.
            if (group + 1) % 16 == 0 or group + 1 == groups:
                dump(output / 'records.json', all_records)
                print(json.dumps(dict(mode=ARGS.mode, condition=ARGS.condition,
                                      local_condition=local_index, groups=group+1)), flush=True)
    dump(output / 'generation.json', generation)
    dump(output / 'records.json', all_records)
    failures = [dict(local_condition=r['local_condition'], group=r['group'],
                     repeats=r['repeats'], failures=r['failures'])
                for r in all_records if r['failures']]
    dump(output / 'failures.json', failures)
    return dict(new_observations=count, mode=ARGS.mode, condition=ARGS.condition,
                points=points, groups=groups, records=len(all_records),
                failed_records=len(failures), receiver_calls=0, decoder_calls=0,
                scope='actual conditional G0/P2/N4 development; independent calibration/evaluation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--mode', required=True, choices=['qualification', 'calibration', 'evaluation'])
    parser.add_argument('--condition', type=int, default=0)
    parser.add_argument('--wall-seconds', type=int, default=180)
    ARGS = parser.parse_args()
    cfg = json.loads(CONFIG_PATH.read_text())
    points, groups, split_id = specification(ARGS.mode, ARGS.condition, cfg)
    frozen_components()
    from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths
    sources = [Path(__file__), CONFIG_PATH,
               ROOT / 'experiments/afdm_efficient_information/prior_likelihood.py',
               ROOT / 'experiments/afdm_collision_resolution/collision_teacher.py',
               ROOT / 'experiments/afdm_higher_order_information/prior.py',
               *source_paths()]
    registration = dict(seed=cfg['seed'], new_observations=len(points)*groups*max(cfg['repeats']),
                        mode=ARGS.mode, condition=ARGS.condition, frozen_config=cfg,
                        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)
    run(ARGS.stage, registration, sources, calculate, wall_seconds=ARGS.wall_seconds)
