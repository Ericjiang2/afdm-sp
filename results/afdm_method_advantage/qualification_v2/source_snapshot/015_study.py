"""Registered independent calibration/evaluation of observed-only methods.

Truth is consumed only by the continuous actual generator and downstream
reporting. All inference calls receive exactly (Y, public method config).
"""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_method_advantage import methods
from experiments.afdm_method_advantage.protocol import ROOT, ARTIFACT, dump, hashes, run
from experiments.afdm_higher_order_information.prior import frozen_components

CONFIG_PATH = ARTIFACT / 'METHOD_CONFIG.json'


def project_source_paths():
    """Bind actual preloaded project dependencies, including frozen UP modules."""
    paths = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.suffix == '.py' and path.is_file():
                paths.add(path)
    return sorted(paths)


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


def replay_inputs(stage_name):
    """Only replay saved qualification observations, with immutable hash checks."""
    if not stage_name or Path(stage_name).name != stage_name:
        raise ValueError('one local qualification stage name required')
    source = ARTIFACT / stage_name
    registration = json.loads((source/'registration.json').read_text())
    attempt = json.loads((source/'attempt.json').read_text())
    if registration['config'].get('mode') != 'qualification':
        raise ValueError('only qualification replay is supported')
    paths = [source/f'observations_{i:02d}.npz' for i in range(2)]
    for path, digest in hashes(paths).items():
        if attempt['artifact_sha256'].get(path) != digest:
            raise ValueError('qualification replay raw hash mismatch')
    return paths, [source/'registration.json', source/'attempt.json', *paths]


def calculate(output):
    cfg = json.loads(CONFIG_PATH.read_text())
    points, groups, split_id = specification(ARGS.mode, ARGS.condition, cfg)
    max_r = max(cfg['repeats'])
    generator = ActualPrior(n=4, model='g0', pdp='marginal')
    count = 0
    all_records, generation = [], []
    checkpoint_start = 0
    replay_name = ARGS.replay_qualification
    replay = replay_inputs(replay_name)[0] if replay_name else None
    for local_index, point in enumerate(points):
        theta = [point['delta'], point['mu'], np.log(point['tau']), np.log(point['sigma2'])]
        seed = [*cfg['seed'], split_id, ARGS.condition, local_index]
        before = time.perf_counter()
        if replay is None:
            y = generator.sample(theta, groups * max_r, seed)
            count += len(y)
        else:
            with np.load(replay[local_index], allow_pickle=False) as saved:
                y = saved['y']
                if not np.array_equal(saved['theta'], theta) or not np.array_equal(saved['seed'], seed):
                    raise ValueError('qualification replay configuration mismatch')
                if y.shape != (groups * max_r, 4) or not np.isfinite(y).all():
                    raise ValueError('qualification replay observation shape/value mismatch')
        generation.append(dict(point=point, seed=seed, seconds=time.perf_counter()-before,
                               branch=plain(generator.branch(theta)['signature']),
                               reused_from=str(replay[local_index].relative_to(ROOT)) if replay else None))
        np.savez_compressed(output / f'observations_{local_index:02d}.npz',
                            y=y, theta=np.array(theta), seed=np.array(seed))
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
                dump(output / f'checkpoint_c{local_index:02d}_g{group+1:04d}.json',
                     all_records[checkpoint_start:])
                checkpoint_start = len(all_records)
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
    parser.add_argument('--replay-qualification', default=None)
    ARGS = parser.parse_args()
    cfg = json.loads(CONFIG_PATH.read_text())
    points, groups, split_id = specification(ARGS.mode, ARGS.condition, cfg)
    if ARGS.replay_qualification and ARGS.mode != 'qualification':
        raise ValueError('replay is limited to qualification; main evaluation stays independent')
    frozen_components()
    sources = [Path(__file__), CONFIG_PATH,
               ROOT / 'experiments/afdm_efficient_information/prior_likelihood.py',
               ROOT / 'experiments/afdm_collision_resolution/collision_teacher.py',
               ROOT / 'experiments/afdm_higher_order_information/prior.py',
               *project_source_paths()]
    if ARGS.replay_qualification:
        sources.extend(replay_inputs(ARGS.replay_qualification)[1])
    registration = dict(seed=cfg['seed'], new_observations=0 if ARGS.replay_qualification else len(points)*groups*max(cfg['repeats']),
                        mode=ARGS.mode, condition=ARGS.condition, frozen_config=cfg,
                        replay_qualification=ARGS.replay_qualification,
                        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)
    run(ARGS.stage, registration, sources, calculate, wall_seconds=ARGS.wall_seconds)
