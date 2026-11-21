#!/usr/bin/env python
"""Timing and core-hour projection of the information-budget screen (phase 1; no scored frame).  Single-thread, one quiet process (plus an optional concurrency check).

    python -B ib_screen_timing.py --out out/ib_screen/timing [--contention-json file]
Per reference and L in {4, 16, 32, 48, 64, 96}: seconds per frame for ALL 5 conditions (frames are shared across conditions), split into draw / A (pivoted QR) / f+J; RAY, GMI and the
9.5 dB column are timed separately.  Projection: locate = 64 frames x full grid (24 L) x {MODEL, PHYS}; confirm = 512 frames per confirmed L (literal rule: the locate stage cannot
pass, so only L = 4 and 8 are confirmed -- see the Bernstein offset table -- ; worst case: all 24 L).  Per-L seconds are interpolated linearly in L between the measured points.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

import ib_screen_core as C

HERE = Path(__file__).resolve().parent


def measure(consts, tab, ref, L, nrep=3, **kw):
    secs = []
    for rep in range(nrep + 1):
        o = C.frame_terms(consts, tab, ref, 'timing', L, rep, want_time=True, **kw)
        if rep > 0:
            secs.append(o['sec'])
    return {k: float(np.mean([s[k] for s in secs])) for k in secs[0]}, o['side']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=C.OUT / 'timing')
    ap.add_argument('--contention-json', type=Path, default=None)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    consts, tab, model, phys = C.Consts(), C.QpskMI(), C.ModelRef(), C.PhysRef()
    refs = {'MODEL': model, 'PHYS': phys}
    Lm = (4, 16, 32, 48, 64, 96)
    per = {}
    for name, ref in refs.items():
        per[name] = {}
        for L in Lm:
            sec, side = measure(consts, tab, ref, L)
            per[name][L] = dict(sec, side=side)
            print(name, L, side, {k: round(v, 3) for k, v in sec.items()}, flush=True)
    extra = {}
    for L in (16, 48, 96):
        ts = []
        for rep in range(3):
            t0 = time.perf_counter()
            C.ray_terms(consts, tab, phys, 'timing', L, rep)
            ts.append(time.perf_counter() - t0)
        extra[f'RAY_{L}'] = float(np.mean(ts[1:]))
        g, _ = measure(consts, tab, phys, L, nrep=2, want_gmi=True)
        extra[f'GMI_{L}'] = g['gmi']
        c9, _ = measure(consts, tab, phys, L, nrep=2, conds=C.CONDS + ((9.5, .3),))
        extra[f'cond6_total_{L}'] = c9['total']
        print('extra', L, {k: round(v, 3) for k, v in extra.items() if k.endswith(str(L))}, flush=True)
    # Bernstein offsets (range terms only, S^2 = 0 lower bound) per symbol, endpoint delta as frozen
    d = C.delta_endpoint() / 3.
    offs = {}
    for name, ref in refs.items():
        for cond in C.CONDS:
            for L in (4, 48, 96):
                r = C.term_ranges(ref, L, cond)
                row = {}
                for n in (64, 512):
                    ln = np.log(2. / d)
                    row[str(n)] = dict(eA=7 * r['A'] * ln / (3 * (n - 1)) / C.N, ef=7 * r['f'] * ln / (3 * (n - 1)) / C.N, eJ=7 * r['J'] * ln / (3 * (n - 1)) / C.N)
                    row[str(n)]['total_range_offset_per_symbol'] = row[str(n)]['eA'] + row[str(n)]['ef'] + row[str(n)]['eJ']
                row['ranges_over_N'] = dict(A=r['A'] / C.N, f=r['f'] / C.N, J=r['J'] / C.N, beta=r['beta'])
                row['max_possible_LB_over_N'] = (r['A'] + r['J']) / C.N
                offs[f'{name}|{cond[0]:g}|{cond[1]:g}|L{L}'] = row
    # projection
    grid = np.array(C.LGRID, float)
    tpoly = {n: np.interp(grid, Lm, [per[n][L]['total'] for L in Lm]) for n in refs}
    contention = None
    if args.contention_json and args.contention_json.exists():
        contention = json.loads(args.contention_json.read_text())
    fac = 1. if contention is None else contention['factor_20']
    both = tpoly['MODEL'] + tpoly['PHYS']
    locate = 64 * both.sum()
    conf_lit = 512 * both[:2].sum()
    conf_worst = 512 * both.sum()
    proj = dict(locate_core_hours=locate / 3600., confirm_literal_core_hours=conf_lit / 3600., confirm_worst_case_core_hours=conf_worst / 3600.,
                total_literal_core_hours=(locate + conf_lit) / 3600., total_worst_case_core_hours=(locate + conf_worst) / 3600.,
                contention_factor=fac, total_literal_core_hours_contended=fac * (locate + conf_lit) / 3600., total_worst_case_core_hours_contended=fac * (locate + conf_worst) / 3600.,
                per_L_seconds_per_frame={n: dict(zip([int(x) for x in grid], tpoly[n].tolist())) for n in refs},
                confirm_core_hours_per_L_512_frames_both_refs={int(L): float(512 * b / 3600.) for L, b in zip(grid, both)})
    out = dict(_argv=sys.argv, _config=dict(Lmeasured=Lm, frames_per_point=3, conds=[list(c) for c in C.CONDS], k_switch=700, date=time.strftime('%Y-%m-%d'),
                                             delta_endpoint=C.delta_endpoint(), n_endpoints=C.n_endpoints(), phys_rank=phys.r), per_frame=per, extra_seconds=extra,
               bernstein_offsets=offs, projection=proj, contention=contention)
    (args.out / 'timing.json').write_text(json.dumps(out, indent=1, default=float))
    L = ['# Information-budget screen: timing and projection', '', 'Single-thread numpy/scipy, one process, seconds per frame for all 5 conditions at once (frames are shared across conditions).', '',
         '| ref | L | side | draw | A (pivoted QR) | f + J | total |', '|---|---|---|---|---|---|---|']
    for n in refs:
        for l in Lm:
            p = per[n][l]
            L.append(f"| {n} | {l} | {p['side']} | {p['draw']:.3f} | {p['A']:.3f} | {p['fJ']:.3f} | {p['total']:.3f} |")
    L += ['', '| extra (PHYS) | L16 | L48 | L96 |', '|---|---|---|---|', '| RAY (A under rays + U + J_z), s | ' + ' | '.join(f"{extra[f'RAY_{l}']:.2f}" for l in (16, 48, 96)) + ' |',
          '| LMMSE-GMI column, s | ' + ' | '.join(f"{extra[f'GMI_{l}']:.2f}" for l in (16, 48, 96)) + ' |', '| 6 conditions (with 9.5 dB), total s | ' + ' | '.join(f"{extra[f'cond6_total_{l}']:.3f}" for l in (16, 48, 96)) + ' |', '',
          '## Projection (core-hours, single quiet process)', '', f"- locate (64 frames x 24 L x MODEL+PHYS): {proj['locate_core_hours']:.2f}", f"- confirm, literal rule (L = 4, 8 only): {proj['confirm_literal_core_hours']:.3f}",
          f"- confirm, worst case (all 24 L x 512 frames x MODEL+PHYS): {proj['confirm_worst_case_core_hours']:.2f}", f"- **total literal: {proj['total_literal_core_hours']:.2f}; worst case: {proj['total_worst_case_core_hours']:.2f}**"]
    if contention:
        L += [f"- measured slowdown of the mean row time (L = 48): x{contention['factor_20']:.2f} at 20 concurrent single-thread shards, x{contention['factor_40']:.2f} at 40 -> at 20 concurrent: literal "
              f"{proj['total_literal_core_hours_contended']:.2f}, worst case {proj['total_worst_case_core_hours_contended']:.2f} core-hours; at 40 concurrent: literal "
              f"{contention['factor_40'] * proj['total_literal_core_hours']:.2f}, worst case {contention['factor_40'] * proj['total_worst_case_core_hours']:.2f}"]
    L += ['', '## Bernstein range-term offsets per symbol (S^2 = 0, i.e. a lower bound of the true offset), delta per endpoint = ' f"{C.delta_endpoint():.3e} (/3 per term)", '',
          '| ref | cond | L | n=64 offset (A + f + J) | n=512 offset | max possible LB/N = (2N + J range)/N |', '|---|---|---|---|---|---|']
    for k, v in offs.items():
        if k.endswith('L48') or k.endswith('L4'):
            nm = k.split('|')
            L.append(f"| {nm[0]} | {nm[1]} dB rho {nm[2]} | {nm[3][1:]} | {v['64']['total_range_offset_per_symbol']:.2f} | {v['512']['total_range_offset_per_symbol']:.2f} | {v['max_possible_LB_over_N']:.2f} |")
    (args.out / 'TIMING.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
