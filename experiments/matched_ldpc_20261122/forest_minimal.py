#!/usr/bin/env python3
"""Evaluate only the frozen forest code at the two preregistered C1 points."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

import run as c1run
from analyze import FRAMES, GRID, crossing, difference, json_bounds

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / 'out/main_49470497'
SNRS = (750, 775)
SHARED = ('info_sha256', 'pilot_sha256', 'noise_sha256', 'channel_seed', 'gains_sha256')
HASHES = {
    'H': '6ed1a4a83e3635a633479166b28d2047026abde4a983dbdb957bcb79fde4129a',
    'G': '105683bd64239500970d90855e5d136e3a0da16bfe95d3dbac91fab8a699dd5b',
    'free_cols': 'd1e628d1ff301eb8459236d5b2e4100126d2284d0f035711af5cb8de53d7d4d8',
}
ROWS_DIGEST = '9569c410afa79359a3807ff88343c5ec370b739483e09bdb5de43e9619817caf'
WORKER_CPU, CONTROLLER_CPU = 280, 60
BOOT_SEED, BOOT_DRAWS = 20261126, 4000


def old_rows():
    """Use the published L28 rows and bind them byte-for-byte to the run manifest."""
    manifest = hashlib.sha256()
    cells = {snr: {} for snr in GRID}
    for path in sorted(ARCHIVE.glob('rows_L28_*_part*.jsonl')):
        raw = path.read_bytes()
        manifest.update(f'{hashlib.md5(raw).hexdigest()}  {path.name}\n'.encode())
        for row in map(json.loads, raw.splitlines()):
            by_frame = cells[row['snr_centi_db']]
            if row['load'] != 28 or row['frame'] in by_frame:
                raise ValueError('wrong or duplicate archived L28 row')
            by_frame[row['frame']] = row
    if manifest.hexdigest() != ROWS_DIGEST or any(set(cell) != set(FRAMES) for cell in cells.values()):
        raise ValueError('old paired cohort differs from its frozen source')
    return cells


def forest_code(path):
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    from afdm_sp_joint_unrolled.e1_ldpc import _edge_structs, _gf2_rref

    with np.load(path, allow_pickle=False) as obj:
        H = obj['H']
    if array_hash(H) != HASHES['H']:
        raise ValueError('forest parity-check matrix does not match the screened code')
    reduced, pivots, free, rank = _gf2_rref(H)
    if rank != 1024:
        raise ValueError('wrong forest code rank')
    G = np.zeros((2048, 1024), dtype=np.uint8)
    G[free, np.arange(1024)] = 1
    G[pivots] = reduced[:, free]
    if array_hash(G) != HASHES['G'] or array_hash(free) != HASHES['free_cols']:
        raise ValueError('reconstructed forest encoder differs from the screened code')
    chk, var, row_ptr = _edge_structs(H)
    return dict(H=H, G=G, n=2048, k=1024, free_cols=free, chk=chk, var=var, row_ptr=row_ptr)


def worker(args):
    c1run.set_cpu_limit(WORKER_CPU)
    ctx, cfg, _ = c1run.load_context()
    code = forest_code(args.matrix)
    arms = c1run.contexts(ctx, {'forest': code})
    if args.worker == 0:
        c1run.write_json(args.out / 'runtime.json', dict(source_sha256=ctx.sources, environment=ctx.environment,
                             checkpoint_sha256=ctx.header['checkpoint_sha256'], refit=cfg))
    for snr in SNRS:
        path = c1run.part_path(args.out, 28, snr, args.worker)
        with path.open('x') as handle:
            for frame in FRAMES[args.worker::c1run.WORKERS]:
                row = c1run.frame_row(ctx, arms, cfg, 28, snr, frame)
                score = row['arms']['forest']
                if score['syndrome'] == 0 and 0 < score['coded_errors'] <= 4:
                    raise ValueError('forest decoder returned an impossible low-weight codeword difference')
                handle.write(json.dumps(row, allow_nan=False) + '\n')


def error(score):
    return score['info_errors'] > 0


def paired_outcomes(old, out):
    errors = []
    counts = {}
    for snr, w4_count in zip(SNRS, (13, 12)):
        rows = [row for k in range(c1run.WORKERS)
                for row in map(json.loads, c1run.part_path(out, 28, snr, k).read_text().splitlines())]
        if sorted(row['frame'] for row in rows) != list(FRAMES):
            raise ValueError('missing or duplicated forest result row')
        regular, matched, forest, w4 = [], [], [], []
        for row in sorted(rows, key=lambda row: row['frame']):
            ref = old[snr][row['frame']]
            if (row['load'], row['snr_centi_db']) != (28, snr) or any(row[key] != ref[key] for key in SHARED):
                raise ValueError('forest frame is not paired to the original observations')
            mate = ref['arms']['matched']
            regular.append(error(ref['arms']['regular']))
            matched.append(error(mate))
            forest.append(error(row['arms']['forest']))
            w4.append(error(mate) and mate['coded_errors'] == 4 and mate['syndrome'] == 0)
        regular, matched, forest, w4 = (np.asarray(a, dtype=bool) for a in (regular, matched, forest, w4))
        if w4.sum() != w4_count:
            raise ValueError('unexpected old four-bit failure cohort')
        item = dict(frames=len(FRAMES), frame_errors=dict(regular=int(regular.sum()), matched=int(matched.sum()),
                                                         forest=int(forest.sum())),
                    old_w4_failures=w4_count, rescued_old_w4=int((w4 & ~forest).sum()))
        for name, previous in (('matched', matched), ('regular', regular)):
            saved = int((previous & ~forest).sum())
            new = int((~previous & forest).sum())
            item[f'versus_{name}'] = dict(rescued=saved, newly_failed=new, net_reduction=saved-new)
        counts[f'{snr / 100:.2f}'] = item
        errors.append(forest)
    return np.stack(errors, axis=1), counts


def forest_crossing(rates):
    if rates[0] <= .1 < rates[1]:
        return -np.inf, np.inf
    return crossing(np.asarray(SNRS) / 100, rates, .1)


def summarize(old, out):
    forest, counts = paired_outcomes(old, out)
    regular = np.array([[error(old[snr][frame]['arms']['regular']) for snr in GRID] for frame in FRAMES])
    grid = np.asarray(GRID) / 100
    point_reg = crossing(grid, regular.mean(axis=0), .1)
    if point_reg != (8.4375, 8.4375):
        raise ValueError('original regular crossing does not reproduce its frozen value')
    point_new = forest_crossing(forest.mean(axis=0))
    gain = difference(point_reg, point_new)
    verdict = 'PASS' if gain[0] >= .8 else 'BELOW' if gain[1] < .8 else 'UNRESOLVED'
    rng = np.random.default_rng(BOOT_SEED)
    n = len(FRAMES)
    weights = rng.multinomial(n, np.full(n, 1 / n), size=BOOT_DRAWS)
    reg_draws = weights @ regular / n
    forest_draws = weights @ forest / n
    bounds = np.array([difference(crossing(grid, old_draw, .1), forest_crossing(new_draw))
                       for old_draw, new_draw in zip(reg_draws, forest_draws)])
    interval = [np.quantile(bounds[:, 0], .025, method='inverted_cdf'),
                np.quantile(bounds[:, 1], .975, method='inverted_cdf')]
    return dict(cells=counts, regular_10_db=json_bounds(point_reg), forest_10_db=json_bounds(point_new),
                gain_10_db=json_bounds(gain), gain_bootstrap95_db=json_bounds(interval), verdict=verdict)


def controller(args):
    c1run.set_cpu_limit(CONTROLLER_CPU, hard_limit=WORKER_CPU)
    args.out.mkdir()
    result = dict(_argv=sys.argv, _config=dict(commit=args.commit, prediction_commit=args.prediction_commit,
                  matrix_hashes=HASHES, archived_l28_files_sha256=ROWS_DIGEST, load=28, snr_centi_db=list(SNRS),
                  cohort=list(FRAMES), pilot_fraction=c1run.RHO, rounds=c1run.ROUNDS, workers=c1run.WORKERS,
                  bootstrap_seed=BOOT_SEED, bootstrap_draws=BOOT_DRAWS,
                  cpu_allocation_seconds=CONTROLLER_CPU+c1run.WORKERS*WORKER_CPU))
    workers = []
    try:
        old = old_rows()
        for shard in range(c1run.WORKERS):
            workers.append(subprocess.Popen([sys.executable, '-B', *sys.argv, '--worker', str(shard)]))
        c1run.set_cpu_limit(CONTROLLER_CPU)
        statuses = [worker.wait() for worker in workers]
        if any(statuses):
            raise RuntimeError(f'worker failed or stopped: {statuses}')
        result['_config'].update(json.loads((args.out / 'runtime.json').read_text()))
        result.update(summarize(old, args.out), status='DONE', receiver_calls=len(FRAMES)*len(SNRS))
    except Exception as exc:
        for child in workers:
            if child.poll() is None:
                child.terminate()
            child.wait()
        result.update(status='STOPPED', reason=f'{type(exc).__name__}: {exc}')
    result['cpu_seconds'] = c1run.cpu_used()
    c1run.write_json(args.out / 'results.json', result)
    print(result['status'], result.get('verdict', result.get('reason')), result['cpu_seconds'], flush=True)
    if result['status'] != 'DONE':
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--prediction-commit', required=True)
    parser.add_argument('--worker', type=int, choices=range(c1run.WORKERS))
    args = parser.parse_args()
    controller(args) if args.worker is None else worker(args)


if __name__ == '__main__':
    main()
