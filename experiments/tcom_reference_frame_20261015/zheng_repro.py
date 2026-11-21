#!/usr/bin/env python
"""P2a part 1: reproduce Zheng et al. 2025 in its own regime (protocol.md implementation note I4) and evaluate gates G-Z1..G-Z3.

    python -B zheng_repro.py run   --out DIR --frames 2000 --shard i --nshard n [--points p50M8,p40M8,p50M1,p50M4] [--c2 0] [--snr-d 17] [--delta .1]
    python -B zheng_repro.py gates --rows DIR [--c2-rows DIR0 DIR1] --out DIR
    python -B zheng_repro.py audit

Rows: one JSONL row per (frame, point, SNR_d) with the bit-error count (1024 bits per frame) and the channel-estimation error of every arm.
Frames share channel, bits and noise across points and arms (SeedSequence(entropy words, DOMAIN, frame, component)).
Nothing in this file depends on the project's frozen AFDM code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zheng_rx import Zheng  # noqa: E402

# New 256-bit OS entropy (os.urandom(32).hex(), 2026-10-15, before any P2a data) and a domain distinct from every earlier stream.
ENTROPY_HEX = '83103fa458e2c4c413173efb758fd85d8a03e204b3d2b625e13b0b5e72893825'
DOMAIN = 0x5A48454E  # "ZHEN"
COMPONENTS = {'channel': 1, 'bits': 2, 'noise': 3}
SNR_D = (8, 11, 14, 17, 20, 23)
POINTS = {
    'p50M8': dict(snr_p=50., M=8, snr_d=SNR_D, arms=('prop', 'perfect', 'noic')),
    'p40M8': dict(snr_p=40., M=8, snr_d=SNR_D, arms=('prop',)),
    'p50M1': dict(snr_p=50., M=1, snr_d=SNR_D[1:], arms=('prop',)),
    'p50M4': dict(snr_p=50., M=4, snr_d=SNR_D[1:], arms=('prop',)),   # informational (Fig. 5 read values exist)
}
# read-off values from the paper's figures (zheng2025-extraction.md section 5; about +-10% on a log axis)
READ_BER = {
    'p50M8': [4.3e-2, 1.4e-2, 3.4e-3, 9.3e-4, 3.8e-4, 3.5e-4],
    'p40M8': [4.3e-2, 1.4e-2, 3.9e-3, 1.25e-3, 1.0e-3, 3.9e-3],
    'p50M1': [1.5e-2, 5.5e-3, 3.0e-3, 2.45e-3, 2.5e-3],
    'p50M4': [1.45e-2, 4.3e-3, 1.7e-3, 1.18e-3, 1.2e-3],
}
READ_MSE_PROP = [8.4e-3, 7.8e-3, 8.0e-3, 9.0e-3, 1.07e-2, 1.4e-2]   # Fig. 2, SNR_p 50 (definition not stated: orderings and trends only)
READ_ITER_PROP = {8: 19., 23: 8.}                                  # Fig. 3a, Prop. SP, SNR_p 50 (approximate)
BITS_PER_FRAME = 1024


def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def entropy_words(hex_):
    return [int(x) for x in np.frombuffer(bytes.fromhex(hex_), dtype='<u4').astype(np.uint32)]


def stream(frame, component):
    return np.random.default_rng(np.random.SeedSequence(entropy_words(ENTROPY_HEX) + [DOMAIN, int(frame), COMPONENTS[component]]))


def frame_draw(z, frame):
    r = stream(frame, 'channel')
    alphas = r.integers(-z.alpha_max, z.alpha_max + 1, size=z.P)
    h = (r.standard_normal(z.P) + 1j * r.standard_normal(z.P)) / np.sqrt(2. * z.P)
    bits = stream(frame, 'bits').integers(0, 2, size=2 * z.N).astype(np.uint8)
    rn = stream(frame, 'noise')
    noise = (rn.standard_normal(z.N) + 1j * rn.standard_normal(z.N)) / np.sqrt(2.)
    grid = [z.grid_index(i, int(alphas[i])) for i in range(z.P)]   # path i has delay i (distinct delays 0..l_max)
    return grid, h, bits, noise


# ----------------------------------------------------------------------------- runner
def cell_key(row):
    return (row['frame'], row['point'], row['snr_d'])


def load_done(path):
    path = Path(path)
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):
        path.write_bytes(data[:cut])
    return {cell_key(json.loads(x)) for x in data[:cut].decode().splitlines() if x.strip()}


def run_shard(args, argv):
    z = Zheng(c2=args.c2, delta=args.delta)
    names = [x for x in args.points.split(',') if x]
    snr_filter = None if not args.snr_d else {int(x) for x in args.snr_d.split(',')}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    config = dict(_argv=list(argv), _config=dict(
        args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}, entropy=ENTROPY_HEX, domain=DOMAIN,
        constants=dict(N=z.N, alpha_max=z.alpha_max, l_max=z.l_max, P=z.P, K_psk=4, delta=z.delta, gamma=z.gamma, eps=z.eps, i_max=z.i_max,
                       c1=z.c1, c2=z.c2, M_p=z.Mp, pilot_spacing=z.spacing, sigma2=1.0, bits_per_frame=BITS_PER_FRAME),
        points={n: POINTS[n] for n in names}, code_md5=dict(zheng_rx=md5_file(HERE / 'zheng_rx.py'), zheng_repro=md5_file(HERE / 'zheng_repro.py')),
        numpy=np.__version__, python=sys.version.split()[0], audit=z.audit(np.random.default_rng(0))))
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    cmp_key = {k: v for k, v in config['_config'].items() if k not in ('args',)}
    cmp_key['args'] = {k: v for k, v in config['_config']['args'].items() if k not in ('shard', 'out')}
    if cfg_path.exists():
        prev = json.loads(cfg_path.read_text())
        pk = {k: v for k, v in prev['_config'].items() if k != 'args'}
        pk['args'] = {k: v for k, v in prev['_config']['args'].items() if k not in ('shard', 'out')}
        if json.loads(json.dumps(pk)) != json.loads(json.dumps(cmp_key)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        cfg_path.write_text(json.dumps(config, indent=1, default=float, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    started = time.perf_counter()
    n_cells = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            grid, h, bits, noise = frame_draw(z, frame)
            h_true = np.zeros(z.Mp, complex)
            h_true[grid] = h
            h_norm2 = float(np.sum(np.abs(h_true) ** 2))
            for name in names:
                pt = POINTS[name]
                sp2 = 10 ** (pt['snr_p'] / 10)
                xp = z.pilot(pt['M'], sp2)
                for snr_d in pt['snr_d']:
                    if snr_filter is not None and snr_d not in snr_filter:
                        continue
                    if (frame, name, snr_d) in done:
                        continue
                    sd2 = 10 ** (snr_d / 10)
                    x = xp + z.modulate(bits, sd2)
                    y = z.heff_apply(x, grid, h) + noise
                    arms = {}
                    for mode in pt['arms']:
                        t0 = time.perf_counter()
                        res = z.run(y, pt['M'], sp2, sd2, mode=mode, true_grid=grid, true_gains=h)
                        rec = dict(bit_errors=int(np.count_nonzero(res['bits'] != bits)), iterations=int(res['iterations']),
                                   zeta_star=float(res['zeta_star']), seconds=time.perf_counter() - t0,
                                   path_set_correct=bool(set(res['ind']) == set(grid)))
                        if mode != 'perfect':
                            rec['mse_num'] = float(np.sum(np.abs(res['h_hat'] - h_true) ** 2))
                            rec['mse_num_topP'] = float(np.sum(np.abs(z.topp(res['h_hat']) - h_true) ** 2))
                        arms[mode] = rec
                    row = dict(frame=int(frame), point=name, snr_p=pt['snr_p'], M=pt['M'], snr_d=int(snr_d), h_norm2=h_norm2, arms=arms)
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
                    handle.flush()
                    os.fsync(handle.fileno())
                    n_cells += 1
            print(f'[{time.perf_counter() - started:8.1f}s] frame={frame} cells so far={n_cells}', flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_cells} cells in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- aggregation and gates
def load_rows(dirs):
    rows, files = [], []
    for d in dirs:
        found = sorted(Path(d).glob('rows_shard*.jsonl'))
        if not found:
            raise FileNotFoundError(d)
        for f in found:
            rows += [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
            files.append(f)
    return rows, files


def aggregate(rows):
    acc = {}
    seen = set()
    for r in rows:
        key = (r['point'], r['snr_d'], r['frame'])
        if key in seen:
            raise ValueError(f'duplicate row {key}')
        seen.add(key)
        for mode, a in r['arms'].items():
            s = acc.setdefault((r['point'], r['snr_d'], mode), dict(n=0, errors=0, mse=0., mse_topP=0., h2=0., iters=0., zeta=0., sec=0., path_ok=0))
            s['n'] += 1
            s['errors'] += a['bit_errors']
            s['iters'] += a['iterations']
            s['zeta'] += a['zeta_star']
            s['sec'] += a['seconds']
            s['path_ok'] += int(a['path_set_correct'])
            if 'mse_num' in a:
                s['mse'] += a['mse_num']
                s['mse_topP'] += a['mse_num_topP']
                s['h2'] += r['h_norm2']
    out = {}
    for k, s in acc.items():
        bits = s['n'] * BITS_PER_FRAME
        ber = s['errors'] / bits
        out[k] = dict(frames=s['n'], bit_errors=s['errors'], bits=bits, ber=ber, ber_se=math.sqrt(max(ber * (1 - ber), 0.) / bits),
                      mse=(s['mse'] / s['h2'] if s['h2'] else None), mse_topP=(s['mse_topP'] / s['h2'] if s['h2'] else None),
                      mean_iterations=s['iters'] / s['n'], mean_zeta_star=s['zeta'] / s['n'], seconds_per_run=s['sec'] / s['n'],
                      path_set_correct_fraction=s['path_ok'] / s['n'])
    return out


def curve(agg, point, mode, field='ber'):
    return [agg[(point, d, mode)][field] for d in POINTS[point]['snr_d']]


def evaluate(agg):
    g = {}
    ber_perf = curve(agg, 'p50M8', 'perfect')
    idx = [SNR_D.index(d) for d in (8, 14, 20)]
    read = READ_BER['p50M8']
    z1_vals = {str(SNR_D[i]): dict(ours=ber_perf[i], paper_prop_sp=read[i], ok=bool(ber_perf[i] <= read[i])) for i in idx}
    z1_decreasing = all(ber_perf[i] > ber_perf[i + 1] for i in range(len(ber_perf) - 1))
    g['G-Z1'] = dict(passed=bool(all(v['ok'] for v in z1_vals.values()) and z1_decreasing), at_snr_d=z1_vals, strictly_decreasing=z1_decreasing,
                     perfect_ber_curve=ber_perf, criterion='perfect-CSI BER at 8/14/20 dB <= paper Prop. SP (SNR_p 50, M 8) read values 4.3e-2 / 3.4e-3 / 3.8e-4 and decreasing in SNR_d')
    mse_p, mse_n = curve(agg, 'p50M8', 'prop', 'mse'), curve(agg, 'p50M8', 'noic', 'mse')
    below = [a < b for a, b in zip(mse_p, mse_n)]
    rising = bool(mse_p[3] < mse_p[4] < mse_p[5])
    g['G-Z2'] = dict(passed=bool(all(below) and rising), prop_mse=mse_p, noic_mse=mse_n, prop_below_noic_at_every_snr_d=below, prop_mse_17_20_23_increasing=rising,
                     paper_prop_mse_read=READ_MSE_PROP, criterion='Prop. SP MSE < SP-without-IC MSE at every SNR_d; Prop. SP MSE at 17, 20, 23 dB increasing')
    ber = curve(agg, 'p50M8', 'prop')
    ratios = [b / r for b, r in zip(ber, read)]
    within = [abs(math.log10(x)) <= math.log10(2.) + 1e-12 for x in ratios]
    p40 = curve(agg, 'p40M8', 'prop')
    upturn = bool(p40[5] > p40[4])
    m1 = curve(agg, 'p50M1', 'prop')               # 11..23 dB
    m8 = ber[1:]
    m1_gt = [m1[i] > m8[i] for i in (2, 3, 4)]      # 17, 20, 23 dB
    g['G-Z3'] = dict(passed=bool(sum(within) >= 4 and upturn and all(m1_gt)),
                     part_a=dict(passed=bool(sum(within) >= 4), ours=ber, paper=read, ratio=ratios, within_factor_2=within, n_within=int(sum(within))),
                     part_b=dict(passed=upturn, snr_p40_ber=p40, ber_20=p40[4], ber_23=p40[5]),
                     part_c=dict(passed=bool(all(m1_gt)), m1_ber_11_to_23=m1, m8_ber_11_to_23=m8, m1_greater_at_17_20_23=m1_gt),
                     criterion='Prop. SP (SNR_p 50, M 8) within a factor 2 of the read values at >= 4 of 6 points; SNR_p 40: BER(23) > BER(20); M = 1 BER > M = 8 BER at 17, 20, 23 dB')
    g['all_pass'] = bool(all(g[k]['passed'] for k in ('G-Z1', 'G-Z2', 'G-Z3')))
    return g


def informational(agg):
    info = {}
    for point in POINTS:
        for mode in POINTS[point]['arms']:
            info[f'{point}/{mode}'] = dict(snr_d=list(POINTS[point]['snr_d']), ber=curve(agg, point, mode), bit_errors=curve(agg, point, mode, 'bit_errors'),
                                           paper=READ_BER.get(point) if mode == 'prop' else None, mse=curve(agg, point, mode, 'mse') if mode != 'perfect' else None,
                                           mse_topP=curve(agg, point, mode, 'mse_topP') if mode != 'perfect' else None,
                                           mean_iterations=curve(agg, point, mode, 'mean_iterations'), mean_zeta_star=curve(agg, point, mode, 'mean_zeta_star'),
                                           path_set_correct_fraction=curve(agg, point, mode, 'path_set_correct_fraction'), seconds_per_run=curve(agg, point, mode, 'seconds_per_run'))
    return info


def c2_report(agg_default, agg_zero, snr_d=17):
    out = {}
    for tag, agg in (('c2_1_over_2piN2', agg_default), ('c2_0', agg_zero)):
        a = agg[('p50M8', snr_d, 'prop')]
        out[tag] = dict(ber=a['ber'], bit_errors=a['bit_errors'], bits=a['bits'], mse=a['mse'], mean_iterations=a['mean_iterations'], frames=a['frames'])
    d, zz = out['c2_1_over_2piN2'], out['c2_0']
    se = math.sqrt(d['ber'] / d['bits'] + zz['ber'] / zz['bits'])
    out['ber_difference_in_standard_errors'] = (zz['ber'] - d['ber']) / se if se > 0 else 0.
    return out


def render_md(result):
    g, info = result['gates'], result['informational']
    flag = lambda ok: 'PASS' if ok else 'FAIL'  # noqa: E731
    L = ['# Zheng et al. 2025 reproduction in its own regime (P2a part 1)\n',
         f"Overall: **{flag(g['all_pass'])}**.  N = 512, QPSK, P = 3 (delays 0..2, alpha in {{-1,0,1}}), delta .1, gamma .1, epsilon .2, i_m 20, uncoded, "
         f"{result['frames']} frames per point.  Code md5: {result['_code_md5']}.  Entropy `{ENTROPY_HEX}`, domain 0x{DOMAIN:08X}.\n",
         '| gate | criterion | result |\n|---|---|---|']
    z1, z2, z3 = g['G-Z1'], g['G-Z2'], g['G-Z3']
    L.append(f"| G-Z1 | {z1['criterion']} | **{flag(z1['passed'])}** " + '; '.join(f"{d} dB: ours {v['ours']:.2e} vs paper {v['paper_prop_sp']:.1e}" for d, v in z1['at_snr_d'].items())
             + f"; strictly decreasing: {z1['strictly_decreasing']} |")
    L.append(f"| G-Z2 | {z2['criterion']} | **{flag(z2['passed'])}** Prop < no-IC at every SNR_d: {z2['prop_below_noic_at_every_snr_d']}; 17/20/23 dB increasing: {z2['prop_mse_17_20_23_increasing']} |")
    L.append(f"| G-Z3 | {z3['criterion']} | **{flag(z3['passed'])}** (a) {z3['part_a']['n_within']}/6 within factor 2; (b) p40 BER(23) {z3['part_b']['ber_23']:.2e} vs BER(20) {z3['part_b']['ber_20']:.2e}; "
             f"(c) M=1 > M=8 at 17/20/23: {z3['part_c']['m1_greater_at_17_20_23']} |\n")
    L.append('## Prop. SP, SNR_p 50 dB, M = 8: BER and MSE next to the paper\n')
    L.append('| SNR_d | ours BER | paper BER | ratio | perfect CSI BER | no-IC BER | MSE prop | MSE no-IC | paper MSE (Fig. 2) |\n|---|---|---|---|---|---|---|---|---|')
    ip, ipc, inc = info['p50M8/prop'], info['p50M8/perfect'], info['p50M8/noic']
    for i, d in enumerate(SNR_D):
        L.append(f"| {d} | {ip['ber'][i]:.3e} | {READ_BER['p50M8'][i]:.2e} | {ip['ber'][i] / READ_BER['p50M8'][i]:.2f} | {ipc['ber'][i]:.3e} | {inc['ber'][i]:.3e} | "
                 f"{ip['mse'][i]:.3e} | {inc['mse'][i]:.3e} | {READ_MSE_PROP[i]:.2e} |")
    for pt, lab in (('p40M8', 'SNR_p 40 dB, M = 8'), ('p50M1', 'SNR_p 50 dB, M = 1'), ('p50M4', 'SNR_p 50 dB, M = 4 (informational)')):
        if f'{pt}/prop' not in info:
            continue
        v = info[f'{pt}/prop']
        L.append(f'\n## Prop. SP, {lab}\n\n| SNR_d | ours BER | paper BER | ratio |\n|---|---|---|---|')
        for d, b, r in zip(v['snr_d'], v['ber'], v['paper']):
            L.append(f'| {d} | {b:.3e} | {r:.2e} | {b / r:.2f} |')
    L.append('\n## Iterations and final zeta (Prop. SP, SNR_p 50, M 8; informational)\n')
    L.append('| SNR_d | mean iterations | paper (Fig. 3a, approx.) | final zeta* | path set correct |\n|---|---|---|---|---|')
    for i, d in enumerate(SNR_D):
        L.append(f"| {d} | {ip['mean_iterations'][i]:.2f} | {READ_ITER_PROP.get(d, '')} | {ip['mean_zeta_star'][i]:.4f} | {ip['path_set_correct_fraction'][i]:.3f} |")
    if result.get('c2_sensitivity'):
        c = result['c2_sensitivity']
        L.append(f"\n## c2 sensitivity (Prop. SP, SNR_p 50, M 8, SNR_d 17 dB)\n\nc2 = 1/(2 pi N^2): BER {c['c2_1_over_2piN2']['ber']:.3e} ({c['c2_1_over_2piN2']['bit_errors']} errors, MSE {c['c2_1_over_2piN2']['mse']:.3e}); "
                 f"c2 = 0: BER {c['c2_0']['ber']:.3e} ({c['c2_0']['bit_errors']} errors, MSE {c['c2_0']['mse']:.3e}); difference {c['ber_difference_in_standard_errors']:.2f} standard errors.\n")
    if result.get('diagnostic_alt_damping'):
        alt = result['diagnostic_alt_damping']
        L.append('\n## DIAGNOSTIC ONLY (not a gate, not a substitute for the gates): the alternative reading of eq. (29), delta = 0.9 '
                 '(delta weighting the old message, i.e. p = 0.1 p_old + 0.9 p_tilde)\n')
        L.append('| SNR_d | Prop BER | paper | ratio | perfect-CSI BER | no-IC BER | Prop mean iterations |\n|---|---|---|---|---|---|---|')
        for i, d in enumerate(SNR_D):
            pr, pf, ni = alt[f'p50M8/{d}/prop'], alt[f'p50M8/{d}/perfect'], alt[f'p50M8/{d}/noic']
            L.append(f"| {d} | {pr['ber']:.3e} | {READ_BER['p50M8'][i]:.2e} | {pr['ber'] / READ_BER['p50M8'][i]:.2f} | {pf['ber']:.3e} | {ni['ber']:.3e} | {pr['mean_iterations']:.2f} |")
    L.append(f"\nSeconds per MP run (N = 512): prop {ip['seconds_per_run'][0]:.4f}, perfect {ipc['seconds_per_run'][0]:.4f}, no-IC {inc['seconds_per_run'][0]:.4f} (SNR_d 8 dB); "
             f"{result['seconds_per_frame_all_points']:.3f} s per frame over all {result['runs_per_frame']} runs.\n")
    return '\n'.join(L) + '\n'


def run_gates(args, argv):
    rows, files = load_rows([Path(d) for d in args.rows])
    agg = aggregate(rows)
    frames = max(a['frames'] for a in agg.values())
    result = dict(_argv=list(argv), _code_md5=dict(zheng_rx=md5_file(HERE / 'zheng_rx.py'), zheng_repro=md5_file(HERE / 'zheng_repro.py')),
                  frames=frames, gates=evaluate(agg), informational=informational(agg))
    runs = sum(len(POINTS[p]['snr_d']) * len(POINTS[p]['arms']) for p in POINTS)
    secs = sum(a['seconds_per_run'] * a['frames'] for a in agg.values()) / frames
    result.update(runs_per_frame=runs, seconds_per_frame_all_points=secs)
    if args.c2_rows:
        zero_rows, _ = load_rows([Path(d) for d in args.c2_rows])
        result['c2_sensitivity'] = c2_report(agg, aggregate(zero_rows))
    if args.alt_rows:
        alt, _ = load_rows([Path(d) for d in args.alt_rows])
        a2 = aggregate(alt)
        result['diagnostic_alt_damping'] = {f'{k[0]}/{k[1]}/{k[2]}': dict(ber=v['ber'], bit_errors=v['bit_errors'], mean_iterations=v['mean_iterations'], mse=v['mse'])
                                            for k, v in sorted(a2.items())}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = dict(result, _config=dict(rows_md5={str(f): md5_file(f) for f in files}, entropy=ENTROPY_HEX, domain=DOMAIN,
                                         read_values=dict(ber=READ_BER, mse_prop_fig2=READ_MSE_PROP, iterations_fig3a=READ_ITER_PROP)))
    (out / 'zheng_gates.json').write_text(json.dumps(payload, indent=1, default=float, allow_nan=False) + '\n')
    (out / 'ZHENG_GATES.md').write_text(render_md(payload))
    print('gates:', {k: v['passed'] for k, v in result['gates'].items() if isinstance(v, dict)}, 'all_pass =', result['gates']['all_pass'])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--frames', type=int, default=2000)
    r.add_argument('--frame-offset', type=int, default=0)
    r.add_argument('--shard', type=int, default=0)
    r.add_argument('--nshard', type=int, default=1)
    r.add_argument('--points', default='p50M8,p40M8,p50M1,p50M4')
    r.add_argument('--snr-d', default='', help='comma list restricting SNR_d (default: all of the point)')
    r.add_argument('--c2', type=float, default=None, help='default 1/(2 pi N^2)')
    r.add_argument('--delta', type=float, default=.1)
    g = sub.add_parser('gates')
    g.add_argument('--rows', nargs='+', required=True)
    g.add_argument('--c2-rows', nargs='+', default=None)
    g.add_argument('--alt-rows', nargs='+', default=None)
    g.add_argument('--out', type=Path, required=True)
    sub.add_parser('audit')
    args = p.parse_args()
    if args.cmd == 'run':
        run_shard(args, sys.argv[1:])
    elif args.cmd == 'gates':
        run_gates(args, sys.argv[1:])
    else:
        print(json.dumps(Zheng().audit(np.random.default_rng(0)), indent=1))


if __name__ == '__main__':
    main()
