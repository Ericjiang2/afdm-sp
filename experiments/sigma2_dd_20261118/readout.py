"""Verify the completed DD archive and apply the frozen paired FER analysis."""

import argparse
from collections import defaultdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from run_main import ARMS, CORE_HOUR_CAP, FIRST, FRAMES_PER_SHARD, SNRS, STOP

CROSSING_SHA = '43b98016a398aa9cb1a24f8921162f9da1d967546ef594ceb86500095742d94e'
BOOTSTRAPS = 20_000
SEED = 20261019
BAND = .25
CURVES = ('B_known', 'B_SF', 'B_DD', 'A3_known', 'A3_SF', 'A3_DD')


def load_crossings(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != CROSSING_SHA:
        raise ValueError('Slot-mismatch crossing implementation differs')
    spec = importlib.util.spec_from_file_location('slot_crossings', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_archive(run):
    cfg = json.loads((run / 'RUN_CONFIG.json').read_text())['_config']
    receipt = json.loads((run / 'main_receipt.json').read_text())
    status = (run / 'STATUS').read_text().split()
    if cfg != receipt['_config'] or len(status) != 3 or status[0] != 'DONE' or receipt['reason'] or receipt['errors']:
        raise ValueError('Expected a complete main-run receipt')
    total = (STOP - FIRST) * len(SNRS)
    n_shards = (STOP - FIRST) // FRAMES_PER_SHARD
    if (cfg['frame_range'] != [FIRST, STOP - 1] or cfg['snr_centi_db'] != list(SNRS)
            or cfg['expected_keys'] != total or receipt['keys'] != total or cfg['arms'] != list(ARMS)
            or receipt['completed_shards'] != n_shards or receipt['planned_shards'] != n_shards
            or int(status[1]) != n_shards or abs(float(status[2]) - receipt['core_hours']) > .0000005
            or not 0 < receipt['core_hours'] <= CORE_HOUR_CAP):
        raise ValueError('Main run differs from the frozen scope or cap')
    raw_manifest = (run / 'REMOTE_ROWS_MD5.txt').read_bytes()
    manifest = [line.split() for line in raw_manifest.decode().splitlines()]
    if [name for _, name in manifest] != [f'rows_shard{i:03d}.jsonl.gz' for i in range(n_shards)]:
        raise ValueError('Unexpected shard inventory')
    shape = (STOP - FIRST, len(CURVES), len(SNRS))
    failures = np.full(shape, -1, dtype=np.float32)
    diagnostics = defaultdict(list)
    snr_index = {snr: i for i, snr in enumerate(SNRS)}
    for number, (expected, name) in enumerate(manifest):
        path = run / name
        if hashlib.md5(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'MD5 mismatch for {name}')
        lo = FIRST + number * FRAMES_PER_SHARD
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                frame, snr, arms = row['frame'], row['snr_centi_db'], row['arms']
                if not lo <= frame < lo + FRAMES_PER_SHARD or set(arms) != set(ARMS):
                    raise ValueError(f'Malformed receiver key {frame}/{snr}')
                idx, snr_idx = frame - FIRST, snr_index[snr]
                if (failures[idx, :, snr_idx] != -1).any():
                    raise ValueError(f'Duplicate receiver key {frame}/{snr}')
                for i, method in enumerate(ARMS):
                    arm = arms[method]
                    if min(arm['B']['info_errors'], arm['A3_errors']) < 0:
                        raise ValueError(f'Negative error count at {frame}/{snr}/{method}')
                    failures[idx, i, snr_idx] = arm['B']['info_errors'] > 0
                    failures[idx, i + len(ARMS), snr_idx] = arm['A3_errors'] > 0
                dd = arms['DD']['B']
                triggered = dd['f0']['syndrome'] != 0
                if triggered != (dd['a1c'] is not None):
                    raise ValueError(f'DD trigger and continuation differ at {frame}/{snr}')
                known_delays = set(arms['known']['B']['round1_delays'])
                dd_delays = set(dd['round1_delays'])
                truth_delays = set(row['truth_delays'])
                noise = dd['noise']
                diagnostics[snr].append((triggered, noise['ratio'], noise['estimate'] == .001,
                                         dd_delays != known_delays, len(truth_delays - dd_delays),
                                         len(truth_delays - known_delays),
                                         noise['raw'] / row['sigma2']))
    if (failures == -1).any():
        raise ValueError('Incomplete paired receiver grid')
    return cfg, receipt, failures, diagnostics, hashlib.md5(raw_manifest).hexdigest()


def summarize(rows):
    n = len(rows)
    if not n:
        return dict(n=0)
    _, ratios, floored, geometry_diff, missed_dd, missed_known, raw = map(np.asarray, zip(*rows))
    return dict(n=n, mean_ratio=float(ratios.mean()), sd_ratio=float(ratios.std(ddof=1)) if n > 1 else None,
                floor_hits=int(floored.sum()), floor_rate=float(floored.mean()),
                mean_unclipped_ratio=float(raw.mean()), round1_delay_set_differences=int(geometry_diff.sum()),
                mean_missed_true_delays_DD=float(missed_dd.mean()),
                mean_missed_true_delays_known=float(missed_known.mean()))


def bootstrap(math, failures):
    frame_count = failures.shape[0]
    counts = failures.sum(axis=0, dtype=np.int64)
    observed = math.crossing_bounds(counts, frame_count)
    samples = np.empty((BOOTSTRAPS, len(CURVES), 2))
    rng = np.random.default_rng(SEED)
    matrix = failures.reshape(frame_count, -1)
    for start in range(0, BOOTSTRAPS, 512):
        batch = min(512, BOOTSTRAPS - start)
        weights = np.empty((batch, frame_count), dtype=np.float32)
        for draw in weights:
            ids = rng.integers(0, frame_count, frame_count)
            draw[:] = np.bincount(ids, minlength=frame_count)
        boot_counts = (weights @ matrix).reshape(batch, len(CURVES), len(SNRS))
        samples[start:start + batch] = math.crossing_bounds(boot_counts, frame_count)
    return counts, observed, samples


def inside(bounds, lo, hi):
    if bounds[0] >= lo and bounds[1] <= hi:
        return True
    if bounds[1] < lo or bounds[0] > hi:
        return False
    return None


def greater(bounds, threshold):
    if bounds[0] > threshold:
        return True
    if bounds[1] <= threshold:
        return False
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--crossings', required=True, type=Path)
    args = parser.parse_args()
    math = load_crossings(args.crossings)
    cfg, receipt, failures, diagnostics, manifest_md5 = read_archive(args.run)
    frozen_sha = cfg['study_sha256'].get('receiver_study.py')
    if hashlib.sha256(Path(__file__).with_name('receiver_study.py').read_bytes()).hexdigest() != frozen_sha:
        raise ValueError('Readout receiver interface differs from the producing snapshot')
    counts, observed, samples = bootstrap(math, failures)
    delta = math.contrast_bounds(observed, [2], [0])
    recovery = math.contrast_bounds(observed, [1], [2])
    delta_ci = math.paired_ci(math.contrast_bounds(samples, [2], [0]))
    recovery_ci = math.paired_ci(math.contrast_bounds(samples, [1], [2]))
    robust = inside(delta_ci, -BAND, BAND) is True
    degraded = delta_ci[0] > BAND
    verdict = 'ROBUST' if robust else 'DEGRADED' if degraded else 'INCONCLUSIVE'
    bias_parts = (greater(delta, BAND), greater(recovery, 0))
    bias = False if False in bias_parts else True if all(bias_parts) else None
    forecasts = dict(SD1=inside(delta, -BAND, BAND), SD2=bias,
                     SD3=inside(recovery, -BAND, BAND), SD4=greater(recovery, .5))
    curves = {name: dict(info_error_frames=counts[i].tolist(), crossing=math.bounds_json(observed[i]),
                         crossing_ci=math.bounds_json(math.paired_ci(samples[:, i])))
              for i, name in enumerate(CURVES)}

    def noise_summaries(rows):
        return {name: summarize(group) for name, group in (
            ('all', rows), ('trigger', [r for r in rows if r[0]]),
            ('no_trigger', [r for r in rows if not r[0]]))}

    result = dict(_argv=sys.argv, _config=dict(producing_commit=cfg['commit'], raw_manifest_md5=manifest_md5,
                  readout_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), crossing_sha256=CROSSING_SHA,
                  frames=[FIRST, STOP - 1], snr_centi_db=SNRS, n_bootstrap=BOOTSTRAPS, seed=SEED, numpy=np.__version__),
                  core_hours=receipt['core_hours'], keys=receipt['keys'], curves=curves, verdict=verdict,
                  rules=dict(robust=robust, degraded=bool(degraded), inconclusive=not (robust or degraded)),
                  delta_dd=math.bounds_json(delta), delta_dd_ci=math.bounds_json(delta_ci),
                  recovery=math.bounds_json(recovery), recovery_ci=math.bounds_json(recovery_ci),
                  floor_and_geometry={str(snr): noise_summaries(diagnostics[snr]) for snr in SNRS},
                  pooled=noise_summaries([r for rows in diagnostics.values() for r in rows]), forecasts=forecasts)
    with (args.run / 'results.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(verdict, result['delta_dd'], result['delta_dd_ci'], result['recovery'])


if __name__ == '__main__':
    main()
