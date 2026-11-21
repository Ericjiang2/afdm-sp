"""Score the frozen identifiability gate at two archived receiver states."""

import argparse
from hashlib import sha256
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np
import scipy
from scipy.stats import beta

import s1
import s2

HERE = Path(__file__).resolve().parent
WORKERS = 8
TIMEOUT_SECONDS = 785
LIMITS = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS',
          'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def interval(flags):
    # Each endpoint has one Bernoulli draw per physical frame. The exact
    # 95% binomial interval has frame as the unit and stays valid at 0/n.
    total, num = len(flags), sum(flags)
    return dict(n=total, floored=num, fraction=num / total,
                ci95=[float(beta.ppf(.025, num, total - num + 1)) if num else 0.,
                      float(beta.ppf(.975, num + 1, total - num)) if num < total else 1.])


def summarize_s1(rows):
    if len({row['frame'] for row in rows}) != len(rows):
        raise RuntimeError('Expected unique physical MIXED8 frames')
    checked = sum(row['support_bit_identical'] for row in rows)
    if checked < 20 or checked != len(rows):
        raise RuntimeError('S1 entering support verification failed')
    endpoints = {}
    for gap, name in (('0.35', 'narrow'), ('0.75', 'control')):
        endpoints[gap] = {str(delay): interval([row[f'{name}_floored'] for row in rows
                                                if delay == 'pooled' or row[f'{name}_delay'] == delay])
                          for delay in ('pooled', 6, 22)}
    lo, hi = endpoints['0.35']['pooled']['ci95']
    verdict = 'fails' if lo >= .5 else 'passes the screen' if hi < .5 else 'uncertain'
    return dict(support_bit_identical_frames=checked, endpoints=endpoints, verdict=verdict, frames=rows)


def quartiles(values):
    return dict(zip(('q1', 'median', 'q3'), np.percentile(values, [25, 50, 75]).tolist(), strict=True))


def summarize_s2(rows):
    out = {}
    for snr in s2.SNRS:
        keys = [row for row in rows if row['key'][2] == snr]
        blocks = [block for row in keys for block in row['blocks']]
        ranked = [block for block in blocks if block['s_lo_rank'] > 0]
        full = [block for block in blocks if block['atoms'] == 25]
        out[str(snr // 100)] = dict(
            keys=len(keys), blocks=len(blocks), s_lo_rank_zero_blocks=len(blocks) - len(ranked),
            gate_rank=quartiles([block['gate_rank'] for block in blocks]),
            s_lo_rank=quartiles([block['s_lo_rank'] for block in blocks]),
            gate_rank_over_s_lo=quartiles([block['gate_rank'] / block['s_lo_rank'] for block in ranked]),
            overlap=quartiles([block['overlap_trace'] / block['s_lo_rank'] for block in ranked]),
            full_blocks=len(full),
            full_block_gate_rank=quartiles([block['gate_rank'] for block in full]),
            full_block_s_lo_rank=quartiles([block['s_lo_rank'] for block in full]),
        )
    return dict(verified_keys=sum(row['verified'] for row in rows), by_snr=out, keys=rows)


def setup(leg, provenance):
    global LEG, PROVENANCE, CONTEXT
    LEG, PROVENANCE, CONTEXT = leg, provenance, None


def score(row):
    global CONTEXT
    module = s1 if LEG == 'S1' else s2
    if CONTEXT is None:
        CONTEXT = module.make_context(PROVENANCE)
    replay = module.run_frame if LEG == 'S1' else module.run_key
    return replay(CONTEXT, row)


def replay(leg, rows, provenance, preflight):
    # Keep the two frozen import trees in separate worker processes.
    with mp.get_context('fork').Pool(WORKERS, initializer=setup, initargs=(leg, provenance)) as pool:
        checked = pool.map(score, rows[:preflight], chunksize=1)
        print(f'{leg}: verified the first {len(checked)} archived states', flush=True)
        results = checked + pool.map(score, rows[preflight:], chunksize=1)
        pool.close()
        pool.join()
    print(f'{leg}: verified and scored {len(results)} archived states', flush=True)
    return results


def cpu_seconds():
    usage = [resource.getrusage(who) for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    return sum(r.ru_utime + r.ru_stime for r in usage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--producing-commit', required=True)
    args = parser.parse_args()
    started = time.monotonic()
    threads = {name: os.environ.get(name) for name in LIMITS}
    if (os.environ.get('CUDA_VISIBLE_DEVICES') != '' or set(threads.values()) != {'1'}
            or platform.system() != 'Linux' or not sys.dont_write_bytecode):
        raise RuntimeError('Run under the CPU-only launcher with one thread and bytecode disabled')

    pair_rows, s1_archive = s1.load_archive()
    grid_keys, s2_archive = s2.load_archive()
    archives = dict(S1=s1_archive, S2=s2_archive)
    s1_summary = summarize_s1(replay('S1', pair_rows, s1_archive, preflight=20))
    s2_summary = summarize_s2(replay('S2', grid_keys, s2_archive, preflight=1))
    cost = dict(cpu_seconds=cpu_seconds(), elapsed_seconds=time.monotonic() - started)
    cost['core_hours'] = cost['cpu_seconds'] / 3600
    payload = dict(
        _argv=sys.argv,
        _config=dict(producing_commit=args.producing_commit, archives=archives,
                     source_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                                    if p.is_file() and p.suffix in ('.py', '.sh')},
                     runtime=dict(host=platform.node(), python=platform.python_version(),
                                  numpy=np.__version__, scipy=scipy.__version__, threads=threads,
                                  cpu_only=True, worker_processes=WORKERS, timeout_seconds=TIMEOUT_SECONDS),
                     gate=dict(max_variance_fraction=.5, mode_cutoff=1., s_lo_cutoff=.5,
                               pair_ridge='sigma2', grid_ridge='lambda + sum(v)/N'),
                     s1_interval='95% Clopper-Pearson, unique physical frame per endpoint and stratum',
                     s2_quartiles='linear empirical quartiles, one co-delay block per observation'),
        S1=s1_summary, S2=s2_summary, cost=cost,
    )
    with (args.out / 'screen.json').open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
