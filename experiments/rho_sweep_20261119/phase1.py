"""Qualify the rho grid on archived or smoke frames and measure CPU cost."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np

from mechanism import BRANCHES, read_first_exchange

HERE = Path(__file__).resolve().parent
UNIFIED = HERE.parent / 'unified_cov_prospective_20261119'
sys.path.insert(0, str(UNIFIED))
import archives  # noqa: E402
import cstate  # noqa: E402

stage3 = cstate.stage3
ARMS = ('F0', 'A2', 'CD')
RHOS = (150, 200, 250, 300, 400, 500)
SCENARIOS = ('U', 'G')
SNRS = tuple(sorted((*range(300, 1201, 100), 450, 550, 650)))
CELLS = tuple((s, rho) for s in SCENARIOS for rho in RHOS)
SMOKE_FRAMES = (8600, 8601)
COST_FRAMES = range(4000, 4008)
THREADS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
UNIFIED_SOURCES = {
    'cstate.py': '2914e7c47ea24231f8b7b5376bb9c2214bf13860db34abee7b0972af6cf914b8',
    'archives.py': '86258031004489ce993ba2ab717706fb5a6e9d18bc92734ce8317ecc5d3325c8',
}


def init_worker():
    global ctx, full, cd
    ctx, full, cd, _ = cstate.context()


# Adapt unified_cov_prospective_20261119/cstate.py::one for the same three-arm schedule;
# the frozen return omits the F0 symbol moments needed to log u on every key.
def run_key(base, key, arms, *, mechanism=False):
    from messages import moments

    s, rho, snr, frame = key
    start = time.process_time()
    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
    f0 = dict(**stage3.decoded(ctx, dec, truth), first_edit_type=None, state=None, decision=[])
    _, variance, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - ctx.system.rho)
    u = float(variance.sum())
    rows = {'F0': f0}
    if mechanism and set(arms) != set(BRANCHES):
        raise ValueError('The mechanism diagnostic requires both continuation arms')
    first_traces = {}
    for arm in arms:
        if not syndrome:
            rows[arm] = f0
            continue
        branch = stage3.e1.run_branch(ctx, full if arm == 'A2' else cd, obs, arrays,
                                      'A2' if arm == 'A2' else 'A1')
        if not np.array_equal(branch['ce_variance'], variance):
            raise AssertionError(f'{key} {arm}: branch moments differ from the F0 moments')
        rows[arm] = dict(**stage3.decoded(ctx, branch['decoder'], truth),
                         **cstate._geometry_record(branch['result']))
        if mechanism:
            first_traces[arm] = branch['result'].global_trace[0]
    row = dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
               syndrome=syndrome, triggered=bool(syndrome), u=u, n_symbols=len(variance),
               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
    if mechanism:
        row.update(mechanism=None, mechanism_cpu_seconds=0.0)
        if syndrome:
            mechanism_start = time.process_time()
            row['mechanism'] = read_first_exchange(first_traces, truth, arrays['r1_gains'])
            row['mechanism_cpu_seconds'] = time.process_time() - mechanism_start
    row['cpu_seconds'] = time.process_time() - start
    return row


def run_cell(job, *, mechanism=False):
    s, rho, frame, snrs, arms = job
    if not (frame in stage3.MAIN_FRAMES or frame in SMOKE_FRAMES or 7000 <= frame < 7200):
        raise ValueError(f'Phase 1 rejects frame {frame}')
    start = time.process_time()
    base = stage3.inputs(ctx, frame, s, rho)
    base_cpu = time.process_time() - start
    return base_cpu, [run_key(base, (s, rho, snr, frame), arms, mechanism=mechanism) for snr in snrs]


def parity(want, got, key, field):
    if want != got:
        raise archives.FrozenEvidenceError(f'{key} {field}: archived={want!r}, live={got!r}')


def outcome(row):
    return {name: row[name] for name in ('errors', 'decoded_sha')}


def accepted(row):
    return [edit for _, edit in row['decision'] if edit is not None]


def old_stage_parity(old, new, check_cd):
    key = archives.key(old)
    for field in ('syndrome', 'truth', 'inputs'):
        parity(old[field], new[field], key, field)
    parity(old['arms']['F0'], outcome(new['arms']['F0']), key, 'F0')
    if check_cd:
        cd_row = new['arms']['CD']
        parity(old['arms']['CODELAY'], outcome(cd_row), key, 'CD')
        if old['syndrome']:
            geometry = old['codelay_geometry']
            parity(geometry['paths'], cd_row['state']['paths'], key, 'CD paths')
            parity([[e['slot'], e['new']] for e in geometry['edits']], accepted(cd_row), key, 'CD edits')


def old_split_parity(old, new):
    key = archives.key(old)
    a2 = old['arms']['K-diag']
    parity(old['f0']['syndrome'], new['syndrome'], key, 'syndrome')
    for name, ref in (('F0', old['f0']), ('A2', a2)):
        parity(dict(errors=ref['info_errors'], decoded_sha=ref['decoded_sha256']),
               outcome(new['arms'][name]), key, name)
    live = new['arms']['A2']
    parity(list(map(list, zip(a2['final_delays'], a2['final_dopplers'], strict=True))),
           live['state']['paths'], key, 'A2 paths')
    parity([[e['slot'], e['new']] for e in a2['edits']], accepted(live), key, 'A2 edits')
    parity(a2['objective_after'], live['state']['objective'], key, 'A2 objective')


def preflight():
    for name, digest in UNIFIED_SOURCES.items():
        archives.verify(UNIFIED / name, digest)
    for name, digest in archives.STAGE3_FILES.items():
        archives.verify(HERE.parent / name, digest)
    context, _, _, source_checks = cstate.context()
    stage = archives.unique(archives.manifest_rows(
        archives.STAGE3_MAIN, 'MAIN_ROWS_MD5.txt', archives.PINS['stage3_rows'], 'main-'),
        stage3.main_keys())
    split = archives.unique(archives.manifest_rows(
        archives.SPLIT_MAIN, 'REMOTE_ROWS_MD5.txt', archives.PINS['split_rows'], 'rows_K_shard'),
        {(s, rho, snr, frame) for s, rho in stage3.CELLS for snr in range(450, 801, 50)
         for frame in range(7000, 7200)})
    for key, row in split.items():
        if (row['status'] != 'ok' or row['smoke'] or row['family'] != 'K'
                or row['triggered'] != bool(row['f0']['syndrome'])):
            raise archives.FrozenEvidenceError(f'Invalid split-prospective row {key}')
    for key, row in stage.items():
        if set(row['arms']) != set(stage3.ARMS) or (not row['syndrome']
                and not (row['arms']['F0'] == row['arms']['CODELAY'] == row['arms']['FULL'])):
            raise archives.FrozenEvidenceError(f'Invalid Stage 3 row {key}')
    source = dict(context=source_checks, stage3=archives.STAGE3_FILES, unified=UNIFIED_SOURCES,
                  manifests={k: archives.PINS[k] for k in ('stage3_rows', 'split_rows')},
                  environment=context.environment)
    return stage, split, source


def gate_keys(archive, n, is_triggered):
    selected = []
    for s, rho in stage3.CELLS:
        found = sorted(k for k, row in archive.items() if k[:2] == (s, rho) and is_triggered(row))
        if len(found) < n:
            raise archives.FrozenEvidenceError(f'Insufficient archived gate keys for {(s, rho)}')
        selected.extend(found[:n])
    return selected


def evaluate(pool, keys, arms, *, mechanism=False):
    from functools import partial

    groups = {}
    for s, rho, snr, frame in keys:
        groups.setdefault((s, rho, frame), []).append(snr)
    jobs = [(s, rho, f, snrs, arms) for (s, rho, f), snrs in sorted(groups.items())]
    cells = {}
    rows = {}
    for job, (base_cpu, cell_rows) in zip(jobs, pool.map(partial(run_cell, mechanism=mechanism), jobs), strict=True):
        cells[job[:3]] = base_cpu
        rows.update((archives.key(row), row) for row in cell_rows)
    if rows.keys() != set(keys):
        raise AssertionError('Worker keys differ from the scheduled Phase 1 keys')
    return rows, cells


def qualify(pool, out, stage, split, sources, provenance):
    stage_keys = gate_keys(stage, 2, lambda r: bool(r['syndrome']))
    stage_keys += gate_keys(stage, 1, lambda r: not r['syndrome'])
    split_keys = gate_keys(split, 2, lambda r: r['triggered'])
    old_stage, _ = evaluate(pool, stage_keys, ('CD',))
    old_split, _ = evaluate(pool, split_keys, ('A2',))
    for key, new in old_stage.items():
        old_stage_parity(stage[key], new, True)
    for key, new in old_split.items():
        old_split_parity(split[key], new)
    g1 = dict(passed=True, stage3=list(old_stage.values()), split=list(old_split.values()),
              sources=sources, archive_sizes=dict(stage3=len(stage), split=len(split)))
    stage3.write_json(out / 'g1.json', provenance | g1)
    print('G1 PASS', flush=True)

    new_rhos = set(RHOS) - set(stage3.GRID)
    smoke = [(s, rho, snr, f) for s, rho in CELLS if rho in new_rhos
             for snr in (SNRS[0], SNRS[-1]) for f in SMOKE_FRAMES]
    typical, _ = evaluate(pool, smoke, ARMS[1:])
    counts = {}
    seen = {}
    for key, row in typical.items():
        frame = key[3]
        hashes = tuple(row['inputs'][part] for part in ('info', 'coded', 'noise'))
        if seen.setdefault(frame, hashes) != hashes:
            raise AssertionError(f'{key}: broken common-randomness pairing')
        if set(row['arms']) != set(ARMS) or not 0 <= row['u'] <= (1 - .5) * row['n_symbols']:
            raise AssertionError(f'{key}: invalid arm inventory or normalized uncertainty')
        counts.setdefault(key[1], []).append(row['syndrome'] != 0)
    if any(not any(flags) or all(flags) for flags in counts.values()):
        raise AssertionError('Each new rho must exercise both intervention and bypass')
    census = {rho: dict(triggered=sum(flags), bypassed=len(flags)-sum(flags))
              for rho, flags in counts.items()}
    stage3.write_json(out / 'g2.json', provenance | dict(passed=True, census=census,
                                                        rows=list(typical.values())))
    print('G2 PASS', flush=True)

    repeated, _ = evaluate(pool, smoke, ARMS[1:])
    def semantic_rows(rows):
        return {key: {k: v for k, v in row.items() if k != 'cpu_seconds'} for key, row in rows.items()}

    if semantic_rows(typical) != semantic_rows(repeated):
        raise AssertionError('G3 repeated outputs differ outside recorded timing')
    checks = {str(key): hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
              for key, row in semantic_rows(repeated).items()}
    stage3.write_json(out / 'g3.json', provenance | dict(passed=True, keys=len(checks),
                                                        repeated_row_sha256=checks))
    print('G3 PASS', flush=True)


def leverage_rows(pool, stage, out):
    triggered = [key for key, row in stage.items() if row['syndrome']]
    replayed, _ = evaluate(pool, triggered, ('A2',))
    dst = out / 'leverage-rows.jsonl'
    with dst.open('x') as handle:
        for key, old in sorted(stage.items()):
            if old['syndrome']:
                new = replayed[key]
                old_stage_parity(old, new, False)
                a2 = outcome(new['arms']['A2'])
            else:
                a2 = old['arms']['F0']
            record = {name: old[name] for name in stage3.e1.KEY_FIELDS}
            record['arms'] = dict(F0=old['arms']['F0'], CD=old['arms']['CODELAY'], A2=a2)
            handle.write(json.dumps(record, separators=(',', ':')) + '\n')
    return dict(keys=len(stage), a2_replayed=len(replayed),
                sha256=hashlib.sha256(dst.read_bytes()).hexdigest())


def cost_projection(pool):
    keys = [(s, rho, snr, f) for s, rho in CELLS for snr in SNRS for f in COST_FRAMES]
    rows, base = evaluate(pool, keys, ARMS[1:])
    n = len(COST_FRAMES)
    by_cell = {f'{s}/{rho}/{snr}': dict(cpu_seconds_per_key=sum(
        rows[s, rho, snr, f]['cpu_seconds'] for f in COST_FRAMES) / n,
        triggered=sum(rows[s, rho, snr, f]['triggered'] for f in COST_FRAMES))
        for s, rho in CELLS for snr in SNRS}
    base_cpu = sum(base.values()) / n
    options = []
    for snrs, frames in ((SNRS, 400), (SNRS[1:-1], 400), (SNRS[1:-1], 300)):
        s_per_frame = base_cpu + sum(by_cell[f'{s}/{rho}/{snr}']['cpu_seconds_per_key']
                                    for s, rho in CELLS for snr in snrs)
        estimate = s_per_frame * frames * 1.3 / 3600
        options.append(dict(snrs_centi_db=snrs, frames=frames, keys=frames * len(CELLS) * len(snrs),
                            core_hours_with_margin=estimate))
        if estimate <= 10:
            break
    selection = options[-1] if options[-1]['core_hours_with_margin'] <= 10 else None
    return dict(keys_timed=len(keys), frames=list(COST_FRAMES), by_cell=by_cell,
                base_cpu_seconds_per_frame=base_cpu, multiplier=1.3, options=options,
                selection=selection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--workers', required=True, type=int)
    args = parser.parse_args()
    if not 1 <= args.workers <= 18:
        parser.error('Phase 1 permits at most 18 workers plus the coordinator and resource tracker')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or any(os.environ.get(t) != '1' for t in THREADS):
        parser.error('CPU visibility and single-thread environment must be set before import')
    own = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    provenance = dict(_argv=sys.argv, _config=dict(out=str(args.out), workers=args.workers,
        thread_environment={t: os.environ[t] for t in (*THREADS, 'CUDA_VISIBLE_DEVICES')},
        smoke_frames=SMOKE_FRAMES, cost_frames=list(COST_FRAMES), scenarios=SCENARIOS,
        rho_permille=RHOS, snrs_centi_db=SNRS, arms=ARMS, start_method='spawn', phase1_sha256=own))
    started = time.monotonic()
    stage, split, sources = preflight()
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=init_worker) as pool:
        qualify(pool, args.out, stage, split, sources, provenance)
        old = leverage_rows(pool, stage, args.out)
        print('Old-key A2 replay complete', flush=True)
        cost = cost_projection(pool)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    worker_seconds = children.ru_utime + children.ru_stime
    phase_seconds = worker_seconds + time.process_time()
    stage3.write_json(args.out / 'results.json', provenance | dict(
        gates=dict(G1=True, G2=True, G3=True), leverage_rows=old, cost=cost,
        phase1_cpu_seconds=phase_seconds, workers_cpu_seconds=worker_seconds,
        wall_seconds=time.monotonic()-started))
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
