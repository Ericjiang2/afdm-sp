#!/usr/bin/env python3
"""Run the preregistered paired C1 receiver screen on deinlab's AFDM CPU env."""
import argparse
from contextlib import redirect_stdout
from copy import copy
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
HEADROOM = HERE.parent / 'headroom_ladder_20261008'
REFERENCE = HEADROOM / 'out' / 'c1g_r10x'
# The experiment's own analyze.py takes precedence over the legacy namesake.
sys.path.insert(1, str(HEADROOM))

from analyze import ARMS, FRAMES, GRID, crossing, summarize, validate_cell
from codes import build_irregular_code, qualify
import c1_t1_transfer as t1
import driver as base
import driver_c1 as c1
import driver_c1i as c1i


RHO = .3
ROUNDS = 10
WORKERS = 24
CPU_SECONDS = 20 * 3600
CONTROLLER_SECONDS = 300
REFERENCE_ROWS_MD5 = 'a134194f79ea75e1619268901dc50040'


class BudgetStop(Exception):
    pass


def set_cpu_limit(limit, hard_limit=None):
    def stop(_signal, _frame):
        raise BudgetStop(f'process approached its {limit} CPU-second limit')

    signal.signal(signal.SIGXCPU, stop)
    resource.setrlimit(resource.RLIMIT_CPU, (limit - 5, hard_limit if hard_limit is not None else limit))


def load_context():
    ref = json.loads((REFERENCE / 'config_shard000.json').read_text())['_config']
    args = argparse.Namespace(project=PROJECT, native_dir=ref['native_dir'],
                              baseline_dir=ref['baseline_dir'],
                              m2_config=HEADROOM / 'out/m2_dev_exp/frozen_m2_config.json',
                              m2_config_sha256=c1.M2_CONFIG_SHA256)
    cfgs, digest, _ = c1.load_cfgs(args)
    if cfgs['SPg_flat'] != ref['sp_cfgs']['SPg_flat'] or digest != ref['m2_config_sha256']:
        raise ValueError('C1 refit config differs from historical source')
    ctx = c1.load_context(args)
    ctx.sources['driver_c1i.py'] = base.sha256_file(c1i.__file__)
    expected = ref['source_sha256']
    mismatches = sorted(k for k in ctx.sources.keys() | expected.keys()
                        if ctx.sources.get(k) != expected.get(k))
    if mismatches:
        raise ValueError(f'actual C1 imports differ from historical sources: {mismatches}')
    if ctx.header['checkpoint_sha256'] != ref['checkpoint_sha256']:
        raise ValueError('C1 checkpoint differs from historical source')
    decoder = ctx.native.decoder_messages
    return ctx, cfgs['SPg_flat'], decoder


def contexts(ctx, codes):
    arms = {}
    for arm, code in codes.items():
        instance = copy(ctx)
        instance.code = code
        instance.H = code['H'].astype(np.int32)
        arms[arm] = instance
    return arms


def frame_row(ctx, arms, cfg, load, snr, frame):
    paths = c1.draw_c1_paths(c1i.C1_MAP_ENTROPY, frame, load)
    channel = c1.c1_physical_h(ctx, paths)
    taps = c1.tap_sequences(paths, ctx.system.N_total)
    if not np.isclose(sum(np.vdot(a, a).real for a in taps.values()), np.vdot(channel, channel).real,
                      rtol=1e-8):
        raise ValueError('true tap and physical operator energies differ')
    row = dict(frame=frame, load=load, snr_centi_db=snr, arms={})
    for arm, model in arms.items():
        msg = c1.c1_message(model, c1i.C1_MAP_ENTROPY, frame, RHO)
        raw, diag = c1.c1_base(model, msg, paths, channel)
        raw = base.cluster_at_snr(raw, snr / 100)
        obs = base.observe(raw, RHO, snr / 100)
        truth = base.truth_from_raw(raw, diag)
        # Each codeword changes y. The channel, message, pilot and unit noise are held fixed.
        common = dict(info_sha256=hashlib.sha256(truth['info'].tobytes()).hexdigest(),
                      noise_sha256=truth['noise_sha256'], pilot_sha256=ctx.array_hash(obs['pilot']),
                      channel_seed=truth['channel_seed'], gains_sha256=truth['physical_gains_sha256'])
        if not row['arms']:
            row.update(common)
        if any(row[key] != value for key, value in common.items()):
            raise ValueError('different exogenous C1 data within a paired frame')
        result = c1i.run_arm(model, obs, truth, f'FULL_R{ROUNDS}', paths['tap_delays'], cfg, taps)
        score = base.score(model, result, truth)
        trace = result['diag']
        score.update(round_decoded_sha256=[trace[f'dsha{i}'] for i in range(1, ROUNDS + 1)],
                     round_info_errors=[trace[f'ierr{i}'] for i in range(1, ROUNDS + 1)],
                     coded_sha256=ctx.array_hash(truth['coded']), observed_sha256=ctx.array_hash(obs['y']))
        row['arms'][arm] = score
    return row


def historical_check(ctx, cfg):
    rows_path = REFERENCE / 'rows_shard000.jsonl'
    data = rows_path.read_bytes()
    if hashlib.md5(data).hexdigest() != REFERENCE_ROWS_MD5:
        raise ValueError('historical row file differs from its registered digest')
    historic = next(row for row in map(json.loads, data.splitlines())
                    if row['L'] == 28 and row['frame'] == 1000 and row['status'] == 'ok')
    new = frame_row(ctx, {'regular': ctx}, cfg, 28, 650, 1000)
    score = new['arms']['regular']
    if (score['round_decoded_sha256'] != [historic[f'dsha{i}'] for i in range(1, ROUNDS + 1)] or
            score['round_info_errors'] != [historic[f'ierr{i}'] for i in range(1, ROUNDS + 1)] or
            new['info_sha256'] != historic['info_sha256'] or new['noise_sha256'] != historic['noise_sha256'] or
            new['gains_sha256'] != historic['physical_gains_sha256'] or
            new['channel_seed'] != historic['channel_seed']):
        raise ValueError('historical regular C1 frame did not replay exactly')
    return new


def awgn_check(ctx, decoder):
    from afdm_sp_joint_unrolled.e1_ldpc import demap_llr

    ctx.demap_llr = demap_llr
    points = np.array([.8, 1., 1.2, 1.4, 1.6])
    errors = []
    for snr in points:
        failures = 0
        for frame in FRAMES:
            info, _, _, llr = t1.frame_data(ctx, frame, 10 ** (snr / 10))
            result = decoder(ctx.code, llr, maxiter=50)
            failures += np.any(ctx.extract_info(ctx.code, result['decoded']) != info)
        errors.append(int(failures))
    lower, upper = crossing(points, np.asarray(errors) / len(FRAMES), .5)
    if not np.isfinite(lower) or lower != upper:
        raise ValueError(f'regular AWGN .5 crossing is unbracketed: {errors}')
    _, mi = t1.gh_uncoded(10 ** (lower / 10))
    if abs(mi - .5770) > .025:
        raise ValueError(f'regular AWGN threshold mismatch: {mi:.6f} bit')
    return dict(snr_db=points.tolist(), frame_errors=errors, frames_per_point=len(FRAMES),
                crossover_db=float(lower), crossover_input_mi=mi)


def write_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def part_path(out, load, snr, worker):
    return out / f'rows_L{load}_{snr}_part{worker:02d}.jsonl'


def worker(args, response):
    set_cpu_limit(args.worker_cpu_limit)
    ctx, cfg, _ = load_context()
    codes = {'regular': ctx.code}
    with np.load(args.out / 'codes.npz', allow_pickle=False) as arrays:
        for arm in ARMS[1:]:
            codes[arm] = {key: arrays[f'{arm}_{key}'] for key in ('H', 'G', 'free_cols', 'chk', 'var', 'row_ptr')}
            codes[arm].update(n=2048, k=1024)
    arms = contexts(ctx, codes)
    print(json.dumps(dict(cpu_seconds=time.process_time())), file=response, flush=True)
    try:
        for line in sys.stdin:
            load, snr = json.loads(line)
            with part_path(args.out, load, snr, args.worker).open('x') as part:
                for frame in FRAMES[args.worker::WORKERS]:
                    row = frame_row(ctx, arms, cfg, load, snr, frame)
                    part.write(json.dumps(row, allow_nan=False) + '\n')
                    part.flush()
            print(json.dumps(dict(cpu_seconds=time.process_time())), file=response, flush=True)
    except BudgetStop as exc:
        print(json.dumps(dict(cpu_seconds=time.process_time(), budget_stop=str(exc))), file=response, flush=True)


def receive_cpu(process):
    line = process.stdout.readline()
    if not line:
        code = process.wait()
        if code in (-signal.SIGKILL, -signal.SIGXCPU):
            raise BudgetStop(f'worker {process.pid} stopped at its CPU ceiling')
        raise RuntimeError(f'worker {process.pid} exited with status {code}')
    status = json.loads(line)
    if 'budget_stop' in status:
        raise BudgetStop(status['budget_stop'])
    return status['cpu_seconds']


def cpu_used():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def controller(args):
    # Children inherit the maximum and cannot raise it. Retain their allowance
    # through spawn while keeping the controller's own soft alarm in force.
    set_cpu_limit(CONTROLLER_SECONDS, hard_limit=max(CONTROLLER_SECONDS, args.worker_cpu_limit))
    args.out.mkdir()
    result = dict(_argv=sys.argv, _config=dict(source_commit=args.commit, prediction_commit='c545a5863',
                  rho=RHO, receiver_internal_rho=.5, rounds=ROUNDS, detector_iterations=20, decoder_maxiter=50,
                  cohort=list(FRAMES), grid_centi_db=list(GRID), l16_grid_centi_db=[650, 675, 700],
                  budget_cpu_seconds=CPU_SECONDS, prior_cpu_seconds=args.prior_cpu_seconds,
                  worker_cap_cpu_seconds=args.worker_cpu_limit,
                  controller_cap_cpu_seconds=CONTROLLER_SECONDS, workers=WORKERS,
                  entropy_hex=c1i.C1_MAP_ENTROPY, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS,
                  code_rate=.5, bootstrap=dict(seed=20261123, replicates=4000)))
    processes = []
    cells = {}
    active_cell = None
    stop = None
    failed = False
    try:
        ctx, cfg, decoder = load_context()
        own_sources = {file.name: base.sha256_file(file) for file in HERE.glob('*.py')}
        modules = {module: str(Path(sys.modules[module].__file__).resolve())
                   for module in ctx.sources if module in sys.modules}
        result['_config'].update(source_sha256={**ctx.sources, **own_sources,
                                 'c1A_stats.py': base.sha256_file(HEADROOM / 'c1A_stats.py'),
                                 'c1_t1_transfer.py': base.sha256_file(t1.__file__)},
                                 source_paths=modules, environment=ctx.environment,
                                 code_g_sha256=ctx.header['code_g_sha256'],
                                 checkpoint_sha256=ctx.header['checkpoint_sha256'], refit=cfg)
        codes = {'regular': ctx.code, **{arm: build_irregular_code(arm) for arm in ARMS[1:]}}
        result['codes'] = {arm: qualify(arm, code, decoder, ctx.array_hash) for arm, code in codes.items()}
        result['qualification'] = dict(awgn=awgn_check(ctx, decoder))
        result['qualification']['historical'] = historical_check(ctx, cfg)
        arms = contexts(ctx, codes)
        smoke_time = time.process_time()
        smoke = [frame_row(ctx, arms, cfg, 28, 650, frame) for frame in (11998, 11999)]
        cell_cost = {28: (time.process_time() - smoke_time) * len(FRAMES) / len(smoke)}
        result['qualification'].update(smoke=smoke, initial_cpu_forecast=cell_cost[28])
        write_json(args.out / 'qualification.json', result)
        np.savez_compressed(args.out / 'codes.npz', **{f'{arm}_{key}': codes[arm][key]
                            for arm in ARMS[1:] for key in ('H', 'G', 'free_cols', 'chk', 'var', 'row_ptr')})
        print(f'Qualification passed, initial L28 cell estimate {cell_cost[28] / 3600:.2f} core-hours', flush=True)

        for index in range(WORKERS):
            processes.append(subprocess.Popen([sys.executable, '-B', *sys.argv, '--worker', str(index)],
                                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                              text=True, bufsize=1))
        set_cpu_limit(CONTROLLER_SECONDS)
        reported = [receive_cpu(process) for process in processes]
        exogenous = {}

        def measure(load, snr):
            nonlocal active_cell, reported
            estimate = cell_cost.get(load, cell_cost[28])
            available = args.worker_cpu_limit * WORKERS - sum(reported)
            limiting_worker = args.worker_cpu_limit - max(reported)
            if 1.15 * estimate > min(available, limiting_worker * WORKERS):
                raise BudgetStop(f'L{load} {snr / 100:.2f} dB needs ~{estimate / 3600:.2f} core-hours; '
                                 f'{available / 3600:.2f} worker core-hours remain')
            active_cell = (load, snr)
            for process in processes:
                process.stdin.write(json.dumps(active_cell) + '\n')
                process.stdin.flush()
            previous = reported
            reported = [receive_cpu(process) for process in processes]
            cost = float(sum(current - past for current, past in zip(reported, previous)))
            cell_cost[load] = cost
            rows = [row for index in range(WORKERS)
                    for row in map(json.loads, part_path(args.out, load, snr, index).read_text().splitlines())]
            rates = validate_cell(rows, exogenous, active_cell).mean(axis=0)
            cells[active_cell] = rows
            result.setdefault('cpu_seconds_per_cell', {})[f'L{load}_{snr / 100:.2f}'] = cost
            print(f'L{load} {snr / 100:.2f} dB FER {rates.tolist()} cell {cost / 3600:.2f}, '
                  f'cumulative {(sum(reported) + time.process_time() + args.prior_cpu_seconds) / 3600:.2f} core-hours',
                  flush=True)
            active_cell = None
            return rates

        high = 650
        rates = measure(28, high)
        seen_low = rates <= .1
        seen_very_low = rates <= .01
        while not seen_low.all() and high < GRID[-1]:
            high += 25
            rates = measure(28, high)
            seen_low |= rates <= .1
            seen_very_low |= rates <= .01
        if high == 650:
            high = 675
            seen_very_low |= measure(28, high) <= .01
        for snr in range(625, GRID[0] - 1, -25):
            seen_very_low |= measure(28, snr) <= .01
        for snr in (650, 675, 700):
            measure(16, snr)
        while not seen_very_low.all() and high < GRID[-1]:
            high += 25
            seen_very_low |= measure(28, high) <= .01
    except BudgetStop as exc:
        stop = str(exc)
    except Exception as exc:
        stop = f'{type(exc).__name__}: {exc}'
        failed = True
    finally:
        for process in processes:
            process.stdin.close()
            if active_cell is not None:
                process.terminate()
        for process in processes:
            process.wait()
            process.stdout.close()
        result.update(summarize(cells))
        result.update(status='STOPPED' if stop else 'DONE', stop_reason=stop, partial_cell=active_cell,
                      measured_cpu_seconds=cpu_used())
        result['cumulative_cpu_seconds'] = result['measured_cpu_seconds'] + args.prior_cpu_seconds
        write_json(args.out / 'results.json', result)
        print(f"{result['status']} {stop or result['verdict']} CPU={result['cumulative_cpu_seconds'] / 3600:.3f} core-hours",
              flush=True)
    if failed:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--prior-cpu-seconds', type=int, default=0)
    parser.add_argument('--worker', type=int, choices=range(WORKERS))
    args = parser.parse_args()
    args.worker_cpu_limit = (CPU_SECONDS - CONTROLLER_SECONDS - 120 - args.prior_cpu_seconds) // WORKERS
    if args.prior_cpu_seconds < 0 or args.worker_cpu_limit <= 5:
        parser.error('prior CPU use leaves no positive worker allocation')
    if args.worker is None:
        controller(args)
    else:
        # The historical receiver prints startup diagnostics on stdout.
        response = sys.stdout
        with redirect_stdout(sys.stderr):
            worker(args, response)


if __name__ == '__main__':
    main()
