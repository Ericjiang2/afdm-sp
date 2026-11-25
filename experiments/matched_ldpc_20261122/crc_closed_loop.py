#!/usr/bin/env python3
"""Transmit the CRC subcode and run the frozen C1 receiver at six cells."""
import argparse
from copy import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

import crc_terminal_replay as crc
import forest_minimal as frozen
from analyze import crossing, difference, json_bounds

c1run = frozen.c1run
CELLS = {16: (650, 700), 28: (750, 775, 875, 950)}
WORKERS, WORKER_CPU, CONTROLLER_CPU = 20, 220, 100
BOOT_SEED, BOOT_DRAWS = 20261128, 4000
HASH_KEYS = ('pilot_sha256', 'info_sha256', 'noise_sha256', 'channel_seed', 'gains_sha256')


def trailer(payload):
    value = crc.remainder(np.pad(payload, (0, crc.TRAILER)))
    return np.fromiter(((value >> i) & 1 for i in range(crc.TRAILER-1, -1, -1)), dtype=np.uint8)


def code_from_archive():
    path = frozen.ARCHIVE / 'codes.npz'
    if hashlib.md5(path.read_bytes()).hexdigest() != crc.CODE_MD5:
        raise ValueError('matched code differs from the accepted matrix')
    with np.load(path, allow_pickle=False) as arrays:
        code = {key: arrays[f'matched_{key}'] for key in ('H', 'G', 'free_cols', 'chk', 'var', 'row_ptr')}
    code.update(n=2048, k=1024)
    return code


def build_table(code):
    table = {}
    for support in crc.short_supports(code['H']):
        word = np.zeros(2048, dtype=np.uint8)
        word[list(support)] = 1
        tag = crc.remainder(word[code['free_cols']])
        if not tag or tag in table or (code['H'] @ word % 2).any():
            raise ValueError('invalid or colliding repair support')
        table[tag] = list(support)
    return table


def marginal_balance(code):
    crc_map = np.stack([trailer(bits) for bits in np.eye(crc.PAYLOAD, dtype=np.uint8)], axis=1)
    effective = code['G'][:, :crc.PAYLOAD] ^ ((code['G'][:, crc.PAYLOAD:] @ crc_map) % 2)
    varying = effective.any(axis=1)
    iq_rank_two = varying[:1024] & varying[1024:] & np.any(effective[:1024] != effective[1024:], axis=1)
    return dict(uniform_encoded_bits=int(varying.sum()), total_encoded_bits=2048,
                uniform_iq_pairs=int(iq_rank_two.sum()), total_iq_pairs=1024)


def message(ctx, frame, send_crc):
    """Reuse the C1 generator; replace only the trailing information bits."""
    old_hash = None
    tx = copy(ctx)

    def encode(code, info):
        nonlocal old_hash
        old_hash = hashlib.sha256(info.tobytes()).hexdigest()
        if send_crc:
            info[crc.PAYLOAD:] = trailer(info[:crc.PAYLOAD])
        return ctx.encode(code, info)

    tx.encode = encode
    msg = c1run.c1.c1_message(tx, c1run.c1i.C1_MAP_ENTROPY, frame, c1run.RHO)
    if old_hash is None or (send_crc and crc.remainder(msg['info'])):
        raise ValueError('actual transmitted information has an invalid CRC')
    return msg, old_hash


def propagation(ctx, msg, paths, old_hash):
    """Use the same direct CPP transmit/receive chain as driver_c1.c1_base."""
    sys = ctx.system
    wave = ctx.transform(msg['pilot'] + msg['data'], sys.c1, sys.c2, inverse=True)
    propagated = ctx.propagate_cpp(wave, sys.c1, paths['l_i'], paths['k_real'], paths['g_i'],
                                   prefix_length=int(sys.l_max_cap))
    raw = dict(msg, noiseless=ctx.transform(propagated, sys.c1, sys.c2))
    fingerprints = dict(info_sha256=old_hash,
                        noise_sha256=hashlib.sha256(np.ascontiguousarray(raw['noise']).tobytes()).hexdigest(),
                        channel_seed=paths['channel_seed'], gains_sha256=ctx.array_hash(paths['g_i']))
    return raw, fingerprints


def receive(ctx, cfg, obs, delays):
    refit = c1run.c1i.IntervenedRefine(delays, cfg, mode='full')
    with c1run.c1.dpss_rx.vector_prior(ctx.native), ctx.wrappers._hooks(ctx.native, refine=refit):
        decision, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=10, iterations=20,
                                                 ce_mode='soft', gain_mode='joint')
    if len(refit.snaps) != 10:
        raise ValueError('CRC receiver did not perform ten channel refits')
    return decision, arrays


def terminal(ctx, decoded, info, table):
    free = ctx.code['free_cols']
    if c1run.base.syndrome_weight(ctx, decoded):
        return 'ldpc_reject', None
    residual = crc.remainder(decoded[free])
    if residual == 0:
        return 'crc_pass', int(np.count_nonzero(decoded[free[:crc.PAYLOAD]] != info[:crc.PAYLOAD]))
    if residual not in table:
        return 'crc_reject', None
    corrected = decoded.copy()
    corrected[table[residual]] ^= 1
    if c1run.base.syndrome_weight(ctx, corrected) or crc.remainder(corrected[free]):
        raise ValueError('terminal support repair fails the parity or CRC gate')
    return 'repaired', int(np.count_nonzero(corrected[free[:crc.PAYLOAD]] != info[:crc.PAYLOAD]))


def check_archived(ctx, cfg, archived):
    frame = 12000
    reference = []
    for load, snr in ((16, 650), (28, 775)):
        ref = archived[load, snr][frame]
        paths = c1run.c1.draw_c1_paths(c1run.c1i.C1_MAP_ENTROPY, frame, load)
        msg, info_hash = message(ctx, frame, send_crc=False)
        raw, fingerprints = propagation(ctx, msg, paths, info_hash)
        obs = c1run.base.observe(c1run.base.cluster_at_snr(raw, snr/100), c1run.RHO, snr/100)
        fingerprints['pilot_sha256'] = ctx.array_hash(obs['pilot'])
        match = ref['arms']['matched']
        if (any(fingerprints[k] != ref[k] for k in HASH_KEYS) or ctx.array_hash(obs['y']) != match['observed_sha256'] or
                ctx.array_hash(msg['coded']) != match['coded_sha256']):
            raise ValueError('direct propagation differs from archived C1 waveform')
        _, arrays = receive(ctx, cfg, obs, paths['tap_delays'])
        hashes = [c1run.base.decoded_sha(arrays[f'r{i}_decoded']) for i in range(10)]
        if hashes != match['round_decoded_sha256']:
            raise ValueError('lightweight receiver path differs from archived ten-round decisions')
        reference.append(dict(load=load, snr_centi_db=snr, frame=frame, first_ten_decisions_match=True))
    return reference


def worker(args):
    c1run.set_cpu_limit(WORKER_CPU)
    ctx, cfg, _ = c1run.load_context()
    ctx = c1run.contexts(ctx, {'matched': code_from_archive()})['matched']
    table = build_table(ctx.code)
    with (args.out / f'rows_part{args.worker:02d}.jsonl').open('x') as handle:
        for frame in frozen.FRAMES[args.worker::WORKERS]:
            msg, old_hash = message(ctx, frame, send_crc=True)
            for load, snrs in CELLS.items():
                paths = c1run.c1.draw_c1_paths(c1run.c1i.C1_MAP_ENTROPY, frame, load)
                raw, shared = propagation(ctx, msg, paths, old_hash)
                for snr in snrs:
                    obs = c1run.base.observe(c1run.base.cluster_at_snr(raw, snr/100), c1run.RHO, snr/100)
                    decoded, arrays = receive(ctx, cfg, obs, paths['tap_delays'])
                    bits = decoded['decoded']
                    raw_info = [int(np.count_nonzero(ctx.extract_info(ctx.code, arrays[f'r{i}_decoded']) != msg['info']))
                                for i in range(10)]
                    how, payload_errors = terminal(ctx, bits, msg['info'], table)
                    weight_four = how != 'ldpc_reject' and np.count_nonzero(bits != msg['coded']) == 4
                    row = dict(frame=frame, load=load, snr_centi_db=snr, **shared,
                               pilot_sha256=ctx.array_hash(obs['pilot']), crc_info_sha256=ctx.array_hash(msg['info']),
                               coded_sha256=ctx.array_hash(msg['coded']),
                               round_info_errors=raw_info, raw_distance_four=bool(weight_four),
                               outcome=how, payload_errors=payload_errors)
                    handle.write(json.dumps(row, allow_nan=False) + '\n')
                    handle.flush()


def summarize(out, archived):
    rows = {}
    for shard in range(WORKERS):
        for row in map(json.loads, (out / f'rows_part{shard:02d}.jsonl').read_text().splitlines()):
            key = row['load'], row['snr_centi_db'], row['frame']
            if key in rows:
                raise ValueError('duplicate CRC receiver key')
            rows[key] = row
    expected = [(load, snr) for load,snrs in CELLS.items() for snr in snrs]
    if set(rows) != {(load, snr, frame) for load,snr in expected for frame in frozen.FRAMES}:
        raise ValueError('six-point replay is incomplete or has extra keys')

    rng = np.random.default_rng(BOOT_SEED)
    many = rng.multinomial(200, np.full(200, 1/200), size=BOOT_DRAWS) / 200

    def estimate(deltas):
        return dict(mean=float(np.mean(deltas)), ci95=np.quantile(many @ deltas, [.025, .975]).tolist())

    items, start, crc_fer = {}, {}, {}
    for load, snr in expected:
        key = f'L{load}_{snr/100:.2f}'
        group = [rows[load, snr, frame] for frame in frozen.FRAMES]
        baseline = [archived[load, snr][frame] for frame in frozen.FRAMES]
        for row, ref in zip(group, baseline):
            if (any(row[name] != ref[name] for name in HASH_KEYS) or len(row['round_info_errors']) != 10):
                raise ValueError('CRC outcome does not align with its archived frame')
        new_rounds = np.array([r['round_info_errors'] for r in group])
        old_rounds = np.array([r['arms']['matched']['round_info_errors'] for r in baseline])
        delta = (new_rounds[:, 0] - old_rounds[:, 0]) / 1024
        start[load, snr] = delta
        failed = np.array([r['payload_errors'] != 0 for r in group])
        crc_fer[load, snr] = failed
        four = [r for r in group if r['raw_distance_four']]
        items[key] = dict(regular_errors=sum(frozen.error(r['arms']['regular']) for r in baseline),
                          old_matched_errors=int(np.count_nonzero(old_rounds[:, -1])),
                          crc_raw_errors=int(np.count_nonzero(new_rounds[:, -1])), crc_terminal_errors=int(failed.sum()),
                          r1_old_info_ber=float(old_rounds[:, 0].mean()/1024),
                          r1_crc_info_ber=float(new_rounds[:, 0].mean()/1024), r1_delta=estimate(delta),
                          by_r5_old=int(np.any(old_rounds[:, :5] == 0, axis=1).sum()),
                          by_r5_crc=int(np.any(new_rounds[:, :5] == 0, axis=1).sum()),
                          raw_distance_four=len(four), w4_repaired=sum(r['payload_errors'] == 0 for r in four),
                          repaired=sum(r['outcome'] == 'repaired' and r['payload_errors'] == 0 for r in group),
                          rejects=sum(r['payload_errors'] is None for r in group),
                          wrong_accepts=sum(r['payload_errors'] not in (0, None) for r in group))
    startup = {load: estimate(np.mean([start[load,snr] for snr in snrs], axis=0)) for load,snrs in CELLS.items()}
    n_four = sum(v['raw_distance_four'] for v in items.values())
    fixed_four = sum(v['w4_repaired'] for v in items.values())
    wrong_accepts = sum(v['wrong_accepts'] for v in items.values())
    gate = startup[28]['mean'] <= .01 and n_four > 0 and n_four == fixed_four and wrong_accepts == 0
    snrs = np.asarray(frozen.GRID) / 100
    regular = np.array([[frozen.error(archived[28,snr][f]['arms']['regular']) for snr in frozen.GRID]
                        for f in frozen.FRAMES])
    old = crossing(snrs, regular.mean(axis=0), .1)
    if old != (8.4375, 8.4375):
        raise ValueError('frozen regular reference crossing changed')
    local = np.stack([crc_fer[28,snr] for snr in (750,775)], axis=1)
    new = frozen.forest_crossing(local.mean(axis=0))
    gain = difference(old, new)
    paired = np.asarray([difference(crossing(snrs, a, .1), frozen.forest_crossing(b))
                         for a,b in zip(many @ regular, many @ local)])
    interval = [np.quantile(paired[:,0], .025, method='inverted_cdf'),
                np.quantile(paired[:,1], .975, method='inverted_cdf')]
    tax = 10*np.log10(1024/1008)
    return dict(cells=items, startup_delta=startup, w4_total=n_four, w4_repaired=fixed_four,
                wrong_accepts=wrong_accepts, closure_pass=gate, regular_10_db=json_bounds(old),
                crc_10_db=json_bounds(new), gain_10_db=json_bounds(gain), gain_95_db=json_bounds(interval),
                payload_energy_tax_db=float(tax), payload_gain_10_db=json_bounds([x-tax for x in gain]),
                receive_snr_gate='PASS' if gain[0]>=.8 else 'BELOW' if gain[1]<.8 else 'UNRESOLVED')


def controller(args):
    c1run.set_cpu_limit(CONTROLLER_CPU, hard_limit=WORKER_CPU)
    args.out.mkdir()
    result = dict(_argv=sys.argv, _config=dict(commit=args.commit, cells=CELLS, frames=list(frozen.FRAMES),
                  polynomial=hex(crc.POLYNOMIAL), payload_bits=crc.PAYLOAD, crc_bits=crc.TRAILER,
                  rounds=10, detector_updates=20, decoder_cap=50, pilot_fraction=c1run.RHO,
                  total_cpu_cap=CONTROLLER_CPU+WORKERS*WORKER_CPU, worker_count=WORKERS,
                  archive_code_md5=crc.CODE_MD5, archive_l16_sha256=crc.L16_DIGEST,
                  archive_l28_sha256=frozen.ROWS_DIGEST, bootstrap_seed=BOOT_SEED, bootstrap_draws=BOOT_DRAWS))
    children = []
    try:
        archived, _, _, _ = crc.load_archive()
        ctx, cfg, _ = c1run.load_context()
        ctx = c1run.contexts(ctx, {'matched': code_from_archive()})['matched']
        result['_config'].update(c1_source_hashes=ctx.sources, environment=ctx.environment,
                                 checkpoint_sha256=ctx.header['checkpoint_sha256'], refit=cfg)
        result['marginal_balance'] = marginal_balance(ctx.code)
        result['qualification'] = check_archived(ctx, cfg, archived)
        print('Qualification passed; starting only the six CRC cells', flush=True)
        for shard in range(WORKERS):
            children.append(subprocess.Popen([sys.executable, '-B', *sys.argv, '--worker', str(shard)]))
        c1run.set_cpu_limit(CONTROLLER_CPU)
        statuses = [child.wait() for child in children]
        if any(statuses):
            raise RuntimeError(f'incomplete workers; exit statuses: {statuses}')
        result.update(summarize(args.out, archived), status='DONE', crc_receiver_calls=1200, control_calls=2)
    except Exception as exc:
        for child in children:
            if child.poll() is None:
                child.terminate()
            child.wait()
        result.update(status='STOPPED', reason=f'{type(exc).__name__}: {exc}')
    result['cpu_seconds'] = c1run.cpu_used()
    c1run.write_json(args.out / 'results.json', result)
    print(result['status'], result.get('reason', str(result.get('closure_pass'))), result['cpu_seconds'], flush=True)
    if result['status'] != 'DONE':
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--worker', type=int, choices=range(WORKERS))
    args = parser.parse_args()
    controller(args) if args.worker is None else worker(args)


if __name__ == '__main__':
    main()
