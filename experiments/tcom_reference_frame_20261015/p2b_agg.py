#!/usr/bin/env python
"""P2b aggregation (protocol.md section 5 + implementation note I2).  Reads rows only.  numpy only.

    python -B p2b_agg.py --rows DIR [DIR ...] --out DIR [--boot 20000] [--seed N]       test analysis (H6)
    python -B p2b_agg.py --dev DIR --out DIR                                             rho_EP selection on the dev frames
    python -B p2b_agg.py --selftest

Per SNR point: FER of every arm and goodput = info_bits x (1 - FER) per frame (SP 1024 bits, EP the actual k = 767 recorded in the rows).
Paired frame bootstrap (default B = 20000; the frame is the resampling unit, channel and noise are shared by SP and EP arms) of the
goodput difference SP-B(rho) - EP and SP-B(rho) - EP-genie, percentile 95% CI (nearest rank).
H6 per rho on SP-B - EP: "SP better" if >= 3 SNR points have a CI entirely > 0 and fewer than 3 have a CI entirely < 0; "EP better" in the
mirror case; both counts >= 3 -> "MIXED" (not a win for either); otherwise "tie".  The same labels for EP-genie are report-only.
Dev selection: the rho_EP with the largest mean goodput (ties go to the smaller rho_EP).
Report-only calibration arm SPG_r{rho} (SP frame, true H, the EP LMMSE-turbo detector; protocol I3), when present in the rows:
FER-SNR and goodput, (i) the crossing difference x(SPG) - x(A3) at FER 1e-2 in dB (positive = the LMMSE detector needs more SNR than the
TF detector) with a frame-bootstrap CI and censoring flags, (ii) the goodput difference SPG - EP-genie per SNR with frame-bootstrap CIs.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1_agg import STATUS, crossing  # noqa: E402

SP_RHO = (300, 500)
TARGET_FER = 1e-2
MIN_POINTS = 3
ALPHA = .05


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_rows(dirs):
    rows, files = [], []
    for d in dirs:
        found = sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl'))) + sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl.gz')))
        if not found:
            raise FileNotFoundError(d)
        for f in found:
            opener = gzip.open if f.endswith('.gz') else open
            with opener(f, 'rt') as stream:
                rows += [json.loads(x) for x in stream if x.strip()]
            files.append(f)
    return rows, files


def nearest_rank(draws, q):
    d = np.sort(draws)
    return float(d[min(len(d) - 1, max(0, int(math.ceil(q * len(d))) - 1))])


def build(rows, arms=None):
    """{arm: dict(fer (n, S), good (n, S), bits, seconds (n, S))}, snr list, frames; only frames complete at every SNR for every arm."""
    by = {}
    for r in rows:
        key = (int(r['frame']), int(r['snr_centi_db']))
        if key in by:
            raise ValueError(f'duplicate row {key}')
        by[key] = r['arms']
    snrs = sorted({k[1] for k in by})
    frames = sorted({k[0] for k in by})
    names = sorted(arms or {a for v in by.values() for a in v})
    keep = [f for f in frames if all((f, s) in by and all(a in by[(f, s)] and by[(f, s)][a].get('status', 'ok') == 'ok' for a in names) for s in snrs)]
    out = {}
    for a in names:
        fer = np.array([[by[(f, s)][a]['fer'] for s in snrs] for f in keep], float)
        bits = np.array([[by[(f, s)][a]['info_bits'] for s in snrs] for f in keep], float)
        out[a] = dict(fer=fer, good=bits * (1. - fer), bits=float(bits.mean()), seconds=np.array([[by[(f, s)][a]['seconds'] for s in snrs] for f in keep]))
    return out, [s / 100. for s in snrs], keep, len(frames) - len(keep)


def boot_weights(n, B, rng, chunk=500):
    start = 0
    while start < B:
        c = min(chunk, B - start)
        yield start, c, rng.multinomial(n, np.full(n, 1. / n), size=c).astype(float)
        start += c


def paired_ci(diffs, B, rng):
    """diffs: {name: (n, S)} paired per-frame differences; returns {name: dict(point, lo, hi) arrays over S} from one shared bootstrap."""
    n, S = next(iter(diffs.values())).shape
    draws = {k: np.empty((B, S)) for k in diffs}
    for start, c, W in boot_weights(n, B, rng):
        for k, d in diffs.items():
            draws[k][start:start + c] = (W @ d) / n
    out = {}
    for k, d in diffs.items():
        out[k] = dict(point=d.mean(0), lo=np.array([nearest_rank(draws[k][:, s], ALPHA / 2) for s in range(S)]),
                      hi=np.array([nearest_rank(draws[k][:, s], 1 - ALPHA / 2) for s in range(S)]))
    return out


def h6_label(lo, hi):
    n_sp = int(np.sum(lo > 0))
    n_ep = int(np.sum(hi < 0))
    if n_sp >= MIN_POINTS and n_ep >= MIN_POINTS:
        label = 'MIXED'
    elif n_sp >= MIN_POINTS:
        label = 'SP better'
    elif n_ep >= MIN_POINTS:
        label = 'EP better'
    else:
        label = 'tie'
    return label, n_sp, n_ep


def crossing_calibration(data, a, b, snr, B, rng):
    """x(a) - x(b) at FER 1e-2 (dB) with a frame-bootstrap CI; a, b are arm names (paired, shared weights).  Report only: censored
    crossings are clipped to the grid edge and flagged (fraction of censored draws reported)."""
    fa, fb = data[a]['fer'], data[b]['fer']
    n = fa.shape[0]
    snr = np.asarray(snr, float)
    xa, sa = crossing(fa.mean(0)[None, :], n, snr, TARGET_FER)
    xb, sb = crossing(fb.mean(0)[None, :], n, snr, TARGET_FER)
    draws = np.empty(B)
    cens = {k: 0 for k in ('a_low', 'a_high', 'b_low', 'b_high')}
    for start, c, W in boot_weights(n, B, rng):
        ca, sa_ = crossing((W @ fa) / n, n, snr, TARGET_FER)
        cb, sb_ = crossing((W @ fb) / n, n, snr, TARGET_FER)
        draws[start:start + c] = ca - cb
        cens['a_low'] += int(np.sum(sa_ == 1)); cens['a_high'] += int(np.sum(sa_ == 2))
        cens['b_low'] += int(np.sum(sb_ == 1)); cens['b_high'] += int(np.sum(sb_ == 2))
    return dict(arm_a=a, arm_b=b, crossing_a_db=float(xa[0]), status_a=STATUS[int(sa[0])], crossing_b_db=float(xb[0]), status_b=STATUS[int(sb[0])],
                difference_db=float(xa[0] - xb[0]), ci_lo=nearest_rank(draws, ALPHA / 2), ci_hi=nearest_rank(draws, 1 - ALPHA / 2),
                frac_draws_censored={k: v / B for k, v in cens.items()})


def analyze(rows, B=20000, seed=20261016):
    need = ['EP', 'EPG'] + [f'{a}_r{r}' for r in SP_RHO for a in ('F0', 'B', 'A3')]
    present = {a for r in rows for a in r['arms']}
    spg = [f'SPG_r{r}' for r in SP_RHO]
    have_spg = all(a in present for a in spg)
    if have_spg:
        need = need + spg
    data, snr, frames, dropped = build(rows, need)
    n = len(frames)
    rng = np.random.default_rng(seed)
    diffs = {}
    for r in SP_RHO:
        diffs[f'B_r{r}-EP'] = data[f'B_r{r}']['good'] - data['EP']['good']
        diffs[f'B_r{r}-EPG'] = data[f'B_r{r}']['good'] - data['EPG']['good']
        if have_spg:
            diffs[f'SPG_r{r}-EPG'] = data[f'SPG_r{r}']['good'] - data['EPG']['good']
    ci = paired_ci(diffs, B, rng)
    res = dict(n_frames=n, frames_dropped=dropped, snr_db=snr, bits={a: data[a]['bits'] for a in need})
    res['fer'] = {a: [float(x) for x in data[a]['fer'].mean(0)] for a in need}
    res['errors'] = {a: [int(x) for x in data[a]['fer'].sum(0)] for a in need}
    res['goodput'] = {a: [float(x) for x in data[a]['good'].mean(0)] for a in need}
    res['mean_seconds_loaded_run'] = {a: float(data[a]['seconds'].mean()) for a in need}
    res['difference_ci'] = {k: {'point': [float(x) for x in v['point']], 'lo': [float(x) for x in v['lo']], 'hi': [float(x) for x in v['hi']]} for k, v in ci.items()}
    labels, genie = {}, {}
    for r in SP_RHO:
        lab, n_sp, n_ep = h6_label(ci[f'B_r{r}-EP']['lo'], ci[f'B_r{r}-EP']['hi'])
        labels[f'rho{r}'] = dict(label=lab, points_sp_better=n_sp, points_ep_better=n_ep)
        lab, n_sp, n_ep = h6_label(ci[f'B_r{r}-EPG']['lo'], ci[f'B_r{r}-EPG']['hi'])
        genie[f'rho{r}'] = dict(label=lab, points_sp_better=n_sp, points_ep_better=n_ep)
    res['H6'] = labels
    res['H6_vs_EP_genie_report_only'] = genie
    if have_spg:
        res['SPG_report_only'] = dict(
            note='SP-genie-LMMSE: SP frame, true H, EP LMMSE-turbo detector (protocol I3); report only',
            crossing_vs_A3_fer1e2={f'rho{r}': crossing_calibration(data, f'SPG_r{r}', f'A3_r{r}', snr, B, rng) for r in SP_RHO},
            goodput_difference_vs_EPG_labels={f'rho{r}': dict(zip(('label', 'points_sp_better', 'points_ep_better'),
                                                                 h6_label(ci[f'SPG_r{r}-EPG']['lo'], ci[f'SPG_r{r}-EPG']['hi']))) for r in SP_RHO})
    return res


def dev_select(rows):
    """Mean goodput per EP arm EP_pXXX over all SNR points in the rows; returns (table, chosen rho_EP)."""
    by = {}
    for r in rows:
        for a, v in r['arms'].items():
            if a.startswith('EP_p') and v.get('status', 'ok') == 'ok':
                by.setdefault(a, []).append((v['info_bits'] * (1 - v['fer']), v['fer'], v['seconds']))
    table = {}
    for a, vals in sorted(by.items()):
        g = np.array([v[0] for v in vals])
        table[a] = dict(rho_ep=int(a[4:]) / 1000., n=len(vals), goodput=float(g.mean()), goodput_se=float(g.std(ddof=1) / math.sqrt(len(g))),
                        fer=float(np.mean([v[1] for v in vals])), errors=int(sum(v[1] for v in vals)), mean_seconds=float(np.mean([v[2] for v in vals])))
    best = max(t['goodput'] for t in table.values())
    chosen = min(t['rho_ep'] for t in table.values() if t['goodput'] == best)
    return table, chosen


def render_md(res):
    L = ['# P2b results (H6)\n', f"n = {res['n_frames']} frames per SNR (dropped {res['frames_dropped']}). H6 on SP-B - EP: {res['H6']}; "
         f"report-only vs EP-genie: {res['H6_vs_EP_genie_report_only']}\n"]
    snr = res['snr_db']
    L.append('| SNR | ' + ' | '.join(res['fer']) + ' |\n|---|' + '---|' * len(res['fer']))
    for i, s in enumerate(snr):
        L.append(f'| {s:g} | ' + ' | '.join(f"{res['fer'][a][i]:.4f}" for a in res['fer']) + ' |')
    L.append('\n(FER)\n\n| SNR | ' + ' | '.join(res['goodput']) + ' |\n|---|' + '---|' * len(res['goodput']))
    for i, s in enumerate(snr):
        L.append(f'| {s:g} | ' + ' | '.join(f"{res['goodput'][a][i]:.1f}" for a in res['goodput']) + ' |')
    L.append('\n(goodput, info bits per frame)\n')
    for k, v in res['difference_ci'].items():
        L.append(f'### goodput difference {k}\n\n| SNR | point | CI lo | CI hi |\n|---|---|---|---|')
        for i, s in enumerate(snr):
            L.append(f"| {s:g} | {v['point'][i]:.1f} | {v['lo'][i]:.1f} | {v['hi'][i]:.1f} |")
        L.append('')
    if 'SPG_report_only' in res:
        L.append('## SP-genie-LMMSE calibration arm (report only, protocol I3)\n')
        L.append('Crossing difference x(SPG) - x(A3) at FER 1e-2 (dB; positive = the LMMSE-turbo detector needs more SNR than the TF detector):\n')
        L.append('| rho | x(SPG) | x(A3) | difference [95% CI] | censoring (draw fractions) |\n|---|---|---|---|---|')
        for k, v in res['SPG_report_only']['crossing_vs_A3_fer1e2'].items():
            L.append(f"| {k} | {v['crossing_a_db']:.3f} ({v['status_a']}) | {v['crossing_b_db']:.3f} ({v['status_b']}) | {v['difference_db']:.3f} "
                     f"[{v['ci_lo']:.3f}, {v['ci_hi']:.3f}] | {v['frac_draws_censored']} |")
        L.append(f"\nGoodput difference SPG - EP-genie: labels {res['SPG_report_only']['goodput_difference_vs_EPG_labels']} (tables above, keys SPG_r*-EPG).\n")
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------- self test
def synth(rng, n, snrs, fer, bits):
    """fer: {arm: per-SNR failure probability}; nested through one latent u per (frame, SNR) so arms are strongly paired within a cell
    and the SNR points are independent."""
    u = rng.random((n, len(snrs)))
    rows = []
    for f in range(n):
        for i, s in enumerate(snrs):
            rows.append(dict(frame=f, snr_centi_db=s, arms={a: dict(status='ok', fer=int(u[f, i] < p[i]), info_bits=bits[a], seconds=.3) for a, p in fer.items()}))
    return rows


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(('PASS ' if cond else 'FAIL ') + name)
        ok &= bool(cond)

    check('h6: three SP-better points', h6_label(np.array([1., 1, 1, -1]), np.array([2., 2, 2, 1]))[0] == 'SP better')
    check('h6: two points is a tie', h6_label(np.array([1., 1, -1, -1]), np.array([2., 2, 1, 1]))[0] == 'tie')
    check('h6: three EP-better points', h6_label(np.array([-3., -3, -3, -1]), np.array([-1., -1, -1, 1]))[0] == 'EP better')
    check('h6: both sides >= 3 -> MIXED', h6_label(np.array([1., 1, 1, -3, -3, -3]), np.array([2., 2, 2, -1, -1, -1]))[0] == 'MIXED')
    snrs = (450, 500, 550, 600, 650, 700, 750, 800)
    bits = {'EP': 767, 'EPG': 767, **{f'{a}_r{r}': 1024 for r in SP_RHO for a in ('F0', 'B', 'A3', 'SPG')}}
    ep = np.array([.5, .3, .15, .06, .02, .01, .005, .002])
    genie = ep * .5
    sp_good = {f'B_r{r}': np.array([.3, .1, .03, .01, .004, .002, .001, .0005]) for r in SP_RHO}
    base = {'EP': ep, 'EPG': genie, **{f'F0_r{r}': sp_good[f'B_r{r}'] * 1.5 for r in SP_RHO}, **{f'A3_r{r}': sp_good[f'B_r{r}'] * .8 for r in SP_RHO}, **sp_good,
            **{f'SPG_r{r}': sp_good[f'B_r{r}'] * 1.04 for r in SP_RHO}}
    rng = np.random.default_rng(3)
    rows = synth(rng, 2000, snrs, base, bits)
    res = analyze(rows, B=2000, seed=1)
    check('SP clearly better -> label "SP better" at both rho', res['H6']['rho300']['label'] == 'SP better' and res['H6']['rho500']['label'] == 'SP better')
    pt = res['difference_ci']['B_r300-EP']['point']
    exp = 1024 * (1 - sp_good['B_r300']) - 767 * (1 - ep)
    check('goodput difference point estimate tracks the exact difference', np.max(np.abs(np.array(pt) - exp)) < 25)
    check('goodput of EP uses its own info_bits (767)', abs(res['goodput']['EP'][0] - 767 * (1 - ep[0])) < 20)
    # SP-genie-LMMSE calibration arm (report only)
    spg = res['SPG_report_only']
    cal = spg['crossing_vs_A3_fer1e2']['rho300']
    grid = np.array(snrs) / 100.
    x_exact = lambda c: float(crossing(np.asarray(c)[None, :], 10 ** 9, grid, TARGET_FER)[0][0])  # noqa: E731
    exp_diff = x_exact(base['SPG_r300']) - x_exact(base['A3_r300'])
    check('SPG crossing calibration is reported with CI and status ok (analyze path)',
          cal['status_a'] == STATUS[0] and cal['status_b'] == STATUS[0] and cal['ci_lo'] <= cal['difference_db'] <= cal['ci_hi'] and abs(cal['difference_db'] - exp_diff) < .5)
    # direct statistical check of the crossing-difference machinery on a large two-arm sample (exact-curve value, 3-sigma band)
    two = {'A3_r300': base['A3_r300'], 'SPG_r300': base['SPG_r300']}
    data2, snr2, _, _ = build(synth(np.random.default_rng(21), 30000, snrs, two, bits), list(two))
    cal2 = crossing_calibration(data2, 'SPG_r300', 'A3_r300', snr2, 1000, np.random.default_rng(22))
    sigma = (cal2['ci_hi'] - cal2['ci_lo']) / 3.92
    check('crossing difference SPG - A3 recovers the exact-curve %.3f dB within 3 sigma (n = 30000)' % exp_diff, abs(cal2['difference_db'] - exp_diff) <= 3 * sigma + 1e-9)
    check('SPG goodput difference vs EP-genie is reported with CIs', 'SPG_r300-EPG' in res['difference_ci'] and
          spg['goodput_difference_vs_EPG_labels']['rho300']['label'] == 'SP better')
    check('SPG FER and goodput tables are included', 'SPG_r300' in res['fer'] and abs(res['bits']['SPG_r300'] - 1024) < 1e-9)
    base_no_spg = {k: v for k, v in base.items() if not k.startswith('SPG')}
    res_no = analyze(synth(rng, 500, snrs, base_no_spg, bits), B=200, seed=9)
    check('rows without the SPG arm still analyse (no calibration section)', 'SPG_report_only' not in res_no and res_no['H6']['rho300']['label'] in ('SP better', 'tie'))
    # EP better: SP loses a large share of frames at every SNR
    ep_better = dict(base, EP=np.array([.1, .05, .02, .008, .004, .002, .001, .0005]), B_r300=np.array([.7, .6, .5, .45, .4, .35, .3, .25]),
                     B_r500=np.array([.7, .6, .5, .45, .4, .35, .3, .25]))
    res2 = analyze(synth(rng, 2000, snrs, ep_better, bits), B=1000, seed=2)
    check('EP clearly better -> "EP better"', res2['H6']['rho300']['label'] == 'EP better')
    # tie: SP FER .5 and EP FER 1 - 1024 * .5 / 767 give equal expected goodput (EP carries 767 bits, SP 1024)
    p_sp, p_ep = np.full(8, .5), np.full(8, 1 - 1024 * .5 / 767.)
    res3 = analyze(synth(rng, 2000, snrs, dict(base, B_r300=p_sp, B_r500=p_sp, EP=p_ep), bits), B=1000, seed=3)
    check('equal expected goodput -> "tie"', res3['H6']['rho300']['label'] == 'tie' and res3['H6']['rho500']['label'] == 'tie')
    # mixed: SP wins at high SNR, loses at low SNR
    mixed = dict(base, B_r300=np.array([.7, .6, .5, .45, .002, .001, .0005, .0002]), EP=np.array([.1, .05, .02, .008, .004, .002, .001, .0005]))
    res4 = analyze(synth(rng, 2000, snrs, mixed, bits), B=1000, seed=4)
    check('SP loses at 4 low SNRs and wins at 4 high SNRs -> MIXED', res4['H6']['rho300']['label'] == 'MIXED')
    # dev selection with a tie
    dev_rows = []
    for f in range(100):
        for a, p in (('EP_p050', .30), ('EP_p100', .10), ('EP_p200', .10), ('EP_p300', .5)):
            err = int((f % 100) < p * 100)
            dev_rows.append(dict(frame=f, snr_centi_db=600, arms={a: dict(status='ok', fer=err, info_bits=767, seconds=.3)}))
    table, chosen = dev_select(dev_rows)
    check('dev selection: equal goodput goes to the smaller rho_EP', abs(chosen - 0.1) < 1e-12 and table['EP_p100']['goodput'] == table['EP_p200']['goodput'])
    check('dev selection: lower-goodput values are not chosen', table['EP_p300']['goodput'] < table['EP_p100']['goodput'])
    json.dumps(res, allow_nan=False)
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', nargs='+', type=Path)
    p.add_argument('--dev', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--boot', type=int, default=20000)
    p.add_argument('--seed', type=int, default=20261016)
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not args.out or not (args.rows or args.dev):
        p.error('--out and --rows or --dev are required')
    args.out.mkdir(parents=True, exist_ok=True)
    if args.dev:
        rows, files = load_rows([args.dev])
        table, chosen = dev_select(rows)
        payload = dict(_argv=sys.argv[:], _config=dict(rows_md5={str(Path(f)): md5_file(f) for f in files}, p2b_agg_md5=md5_file(__file__),
                                                        n_rows=len(rows)), table=table, chosen_rho_ep=chosen,
                       rule='max mean goodput = info_bits x (1 - FER); ties go to the smaller rho_EP')
        (args.out / 'dev_result.json').write_text(json.dumps(payload, indent=1, allow_nan=False) + '\n')
        for a, t in table.items():
            print(f"{a}: rho_EP {t['rho_ep']:.2f}  goodput {t['goodput']:.2f} +- {t['goodput_se']:.2f}  FER {t['fer']:.4f} ({t['errors']}/{t['n']})")
        print('chosen rho_EP =', chosen)
        return
    rows, files = load_rows(args.rows)
    res = analyze(rows, B=args.boot, seed=args.seed)
    payload = dict(_argv=sys.argv[:], _config=dict(boot=args.boot, seed=args.seed, alpha=ALPHA, min_points=MIN_POINTS, n_rows=len(rows),
                                                    rows_md5={str(Path(f)): md5_file(f) for f in files}, p2b_agg_md5=md5_file(__file__)), results=res)
    (args.out / 'p2b_results.json').write_text(json.dumps(payload, indent=1, allow_nan=False) + '\n')
    (args.out / 'P2B_RESULTS.md').write_text(render_md(res))
    print('H6:', res['H6'])


if __name__ == '__main__':
    main()
