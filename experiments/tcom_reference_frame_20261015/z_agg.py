#!/usr/bin/env python
"""P2a part 2 aggregation: H5 (B against the ported Zheng baselines), protocol.md section 4.3 + I4 + A2 + A3.  Reads rows only.  numpy + scipy.

    python -B z_agg.py --rows DIR [DIR ...] --p1 DIR --out DIR [--frames 1000] [--boot 20000] [--seed N]
    python -B z_agg.py --selftest

Per (scenario, rho) cell, on the port frames 0..999: FER of Z-faithful (delta_new .1 / .9), Z-adapted (.1 / .9), Z-OMP (.1 / .9; our adaptation, A3) and Z-turbo (report-only)
and P1's B on the SAME frames (read from the P1 rows; the channel / noise / information hashes of every joined row are asserted equal).  Crossing x(.) at FER 1e-2 by log-linear
interpolation (p1_agg.crossing, zero-FER floor 0.5/n, censored crossings clipped to the grid edge and flagged), frame-block bootstrap (B 20000, one shared set of weights for every
arm so the pairing with B is kept).
A3 baseline: per cell the variant with the lowest crossing point estimate among {Z-faithful, Z-adapted, Z-OMP} x {delta_new .1, .9} (ties: lower mean FER over the SNR grid), chosen on
these frames (this favours the baseline and is conservative for our claim).
H5 per cell: gain = x(Z*) - x(B) with the p1_agg censoring rule (Z censored high stays at the clipped, lower-bound value, which only weakens the claim; Z censored low or B censored
high -> -inf); "B better" iff the 95% CI of the gain lies entirely above 0.  H5 overall: PASS iff B is better in every cell; INCOMPLETE if a cell is missing; else NOT SUPPORTED.
Per-family results (best reading inside each family, same rule) and Z-turbo are reported for information.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1_agg import (HIGH, LOW, STATUS, crossing, diff_gain, diff_gain_fav, jf, jsum, md5_file, summarize)  # noqa: E402

CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
READINGS = {'faithful': ('Zf01', 'Zf09'), 'adapted': ('Za01', 'Za09'), 'omp': ('Zo01', 'Zo09')}
ALL_Z = ('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09')
TURBO = 'Zt'
FRAME_RE = re.compile(r'"frame": (\d+),')
TARGET = 1e-2
HASH_KEYS = ('channel_seed', 'noise_sha256', 'info_sha256', 'physical_gains_sha256')


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


def load_p1_b(p1_dir, max_frame):
    """{(scenario, rho_permille, snr, frame): dict(fer=B fer, hashes...)} for frames < max_frame."""
    out, files = {}, []
    found = sorted(glob.glob(str(Path(p1_dir) / 'rows_shard*.jsonl'))) + sorted(glob.glob(str(Path(p1_dir) / 'rows_shard*.jsonl.gz')))
    if not found:
        raise FileNotFoundError(p1_dir)
    for f in found:
        opener = gzip.open if f.endswith('.gz') else open
        with opener(f, 'rt') as stream:
            for line in stream:
                m = FRAME_RE.search(line)
                if not m or int(m.group(1)) >= max_frame:
                    continue
                r = json.loads(line)
                b = r['arms']['B']
                if b.get('status', 'ok') != 'ok':
                    continue
                out[(r['scenario'], int(r['rho_permille']), int(r['snr_centi_db']), int(r['frame']))] = dict(fer=int(b['fer']), **{k: r[k] for k in HASH_KEYS})
        files.append(f)
    return out, files


def build_cells(port_rows, p1_b, max_frame):
    """{(scenario, rho_pm): dict(snr, frames, fail{arm}(n, S), extras)} on the frames present at every SNR in both sources."""
    raw = {}
    for r in port_rows:
        if r['frame'] >= max_frame:
            continue
        key = (r['scenario'], int(r['rho_permille']))
        k2 = (r['frame'], int(r['snr_centi_db']))
        cell = raw.setdefault(key, {})
        if k2 in cell:
            raise ValueError(f'duplicate port row {key} {k2}')
        cell[k2] = r
    mismatches = 0
    out = {}
    for key, cell in raw.items():
        snrs = sorted({k[1] for k in cell})
        frames = sorted({k[0] for k in cell})
        arms = [a for a in ('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09', 'Zt') if any(a in r['variants'] for r in cell.values())]
        keep = []
        for f in frames:
            ok = all((f, s) in cell and all(a in cell[(f, s)]['variants'] for a in arms) and (key[0], key[1], s, f) in p1_b for s in snrs)
            if ok:
                for s in snrs:
                    ref = p1_b[(key[0], key[1], s, f)]
                    mismatches += sum(cell[(f, s)][k] != ref[k] for k in HASH_KEYS)
                keep.append(f)
        fail = {a: np.array([[cell[(f, s)]['variants'][a]['fer'] for s in snrs] for f in keep], np.int8) for a in arms}
        fail['B'] = np.array([[p1_b[(key[0], key[1], s, f)]['fer'] for s in snrs] for f in keep], np.int8)
        metric = lambda a, field: [float(np.mean([cell[(f, s)]['variants'][a][field] for f in keep])) for s in snrs]  # noqa: E731
        extras = dict(mean_trunc_true=float(np.mean([cell[(f, snrs[0])]['trunc_true'] for f in keep])) if keep else None,
                      mean_true_delays_hit={a: metric(a, 'n_true_delays_hit') for a in arms} if keep else {}, mean_mp_iterations={a: metric(a, 'mp_iterations') for a in arms} if keep else {},
                      mean_trunc_est={a: metric(a, 'trunc_est') for a in arms if a.startswith('Za') or a == 'Zt'} if keep else {},
                      mean_seconds={a: metric(a, 'seconds') for a in arms} if keep else {},
                      mean_zeta_star={a: metric(a, 'zeta_star') for a in arms} if keep else {})
        out[key] = dict(snr=np.array(snrs) / 100., frames=keep, fail=fail, arms=arms, extras=extras, frames_in_rows=len(frames))
    if mismatches:
        raise ValueError(f'{mismatches} channel / noise / information hash mismatches between the port rows and the P1 rows')
    return out


def boot_fer(fail, B, rng, chunk=500):
    n = next(iter(fail.values())).shape[0]
    fers = {a: np.empty((B + 1, m.shape[1])) for a, m in fail.items()}
    mats = {a: m.astype(float) for a, m in fail.items()}
    for a in fail:
        fers[a][0] = mats[a].mean(0)
    start = 1
    while start <= B:
        c = min(chunk, B + 1 - start)
        W = rng.multinomial(n, np.full(n, 1. / n), size=c).astype(float)
        for a in fail:
            fers[a][start:start + c] = (W @ mats[a]) / n
        start += c
    return fers


def choose_reading(names, x, fail):
    """A2: the reading with the lower crossing point estimate; ties -> lower mean FER over the grid."""
    return min(names, key=lambda a: (float(x[a][0]), float(fail[a].mean())))


def analyze_cell(key, cell, B, rng):
    snr, n = cell['snr'], len(cell['frames'])
    res = dict(scenario=key[0], rho=key[1] / 1000., n_frames=n, frames_in_rows=cell['frames_in_rows'], snr_db=[float(s) for s in snr], arms=list(cell['fail']))
    res['fer'] = {a: [float(v) for v in m.mean(0)] for a, m in cell['fail'].items()}
    res['errors'] = {a: [int(v) for v in m.sum(0)] for a, m in cell['fail'].items()}
    res['extras'] = cell['extras']
    if n < 2 or len(snr) < 2:
        res['label'] = 'NO-DATA'
        return res
    fers = boot_fer(cell['fail'], B, rng)
    X, ST = {}, {}
    for a in fers:
        X[a], ST[a] = crossing(fers[a], n, snr, TARGET)
    res['crossing_1e-2'] = {a: dict(point=jf(X[a][0]), status=STATUS[int(ST[a][0])], ci=[jf(np.sort(X[a][1:])[int(math.ceil(.025 * B)) - 1]), jf(np.sort(X[a][1:])[int(math.ceil(.975 * B)) - 1])],
                                    frac_censored_high=float(np.mean(ST[a][1:] == HIGH)), frac_censored_low=float(np.mean(ST[a][1:] == LOW))) for a in fers}
    verdict = {}
    for kind, names in READINGS.items():
        if not all(a in X for a in names):
            continue
        star = choose_reading(names, X, cell['fail'])
        gain = summarize(diff_gain(X[star], ST[star], X['B'], ST['B']))
        fav = summarize(diff_gain_fav(X[star], ST[star], X['B'], ST['B']))
        other = [a for a in names if a != star][0]
        verdict[kind] = dict(selected=star, selected_crossing=jf(X[star][0]), selected_status=STATUS[int(ST[star][0])], other_reading=other, other_crossing=jf(X[other][0]),
                             gain_vs_B_db=jsum(gain), gain_favourable_to_B_bound=jsum(fav),
                             B_better=bool(math.isfinite(gain['lo']) and gain['lo'] > 0), Z_better_than_B=bool(math.isfinite(fav['hi']) and fav['hi'] < 0))
    res['families'] = verdict
    present = [a for a in ALL_Z if a in X]
    if present:
        star = choose_reading(present, X, cell['fail'])
        gain = summarize(diff_gain(X[star], ST[star], X['B'], ST['B']))
        fav = summarize(diff_gain_fav(X[star], ST[star], X['B'], ST['B']))
        res['H5'] = dict(baseline=star, baseline_crossing=jf(X[star][0]), baseline_status=STATUS[int(ST[star][0])], B_crossing=jf(X['B'][0]), B_status=STATUS[int(ST['B'][0])],
                         gain_vs_B_db=jsum(gain), gain_favourable_to_B_bound=jsum(fav), B_better=bool(math.isfinite(gain['lo']) and gain['lo'] > 0),
                         Z_better_than_B=bool(math.isfinite(fav['hi']) and fav['hi'] < 0))
        res['label'] = 'B better than the best Zheng variant' if res['H5']['B_better'] else ('best Zheng variant better than B' if res['H5']['Z_better_than_B'] else 'B not better than the best Zheng variant')
    snr_list = [float(x) for x in snr]
    res['family_fer_at_6_7_8_db'] = {kind: {f'{d:g}': v['selected'] and res['fer'][v['selected']][snr_list.index(d)] for d in (6., 7., 8.) if d in snr_list} for kind, v in verdict.items()}
    res['family_fer_at_6_7_8_db']['B'] = {f'{d:g}': res['fer']['B'][snr_list.index(d)] for d in (6., 7., 8.) if d in snr_list}
    if TURBO in X:
        res['Z_turbo_report_only'] = dict(crossing=jf(X[TURBO][0]), status=STATUS[int(ST[TURBO][0])],
                                          gain_vs_B_db=jsum(summarize(diff_gain(X[TURBO], ST[TURBO], X['B'], ST['B']))),
                                          plain_difference_db=jsum(summarize(X[TURBO] - X['B'])))
    return res


def analyze(port_rows, p1_b, frames=1000, B=20000, seed=20261017):
    cells = build_cells(port_rows, p1_b, frames)
    rng = np.random.default_rng(seed)
    out = {f'{k[0]}_rho{k[1]}': analyze_cell(k, c, B, rng) for k, c in sorted(cells.items())}
    present = {(v['scenario'], int(round(v['rho'] * 1000))) for v in out.values()}
    labels = {k: v.get('label') for k, v in out.items()}
    if present != set(CELLS):
        overall = 'INCOMPLETE'
    elif all(v.get('H5', {}).get('B_better') for v in out.values()):
        overall = 'PASS'
    else:
        overall = 'NOT SUPPORTED'
    claim = {kind: bool(len(out) == 4 and all(v.get('families', {}).get(kind, {}).get('B_better') for v in out.values())) for kind in READINGS}
    return dict(cells=out, cell_labels=labels, H5_overall=overall, claim_better_than_family_in_all_cells=claim)


def render_md(res):
    L = ['# P2a part 2: H5 (B against the ported Zheng baselines)\n', f"H5 overall: **{res['H5_overall']}**; B better than the best variant of each family in all four cells: "
         f"{res['claim_better_than_family_in_all_cells']}.  Cell labels: {res['cell_labels']}\n"]
    for name, c in res['cells'].items():
        L.append(f"## {name} (n = {c['n_frames']})  label: **{c.get('label')}**\n")
        L.append('| SNR | ' + ' | '.join(c['arms']) + ' |\n|---|' + '---|' * len(c['arms']))
        for i, s in enumerate(c['snr_db']):
            L.append(f'| {s:g} | ' + ' | '.join(f"{c['fer'][a][i]:.3f}" for a in c['arms']) + ' |')
        L.append('\n(FER)\n')
        if 'crossing_1e-2' in c:
            L.append('| arm | crossing @1e-2 (dB) | status |\n|---|---|---|')
            for a, v in c['crossing_1e-2'].items():
                L.append(f"| {a} | {v['point']} | {v['status']} |")
        h = c.get('H5')
        if h:
            L.append(f"\n- **H5 baseline {h['baseline']}** (crossing {h['baseline_crossing']}, {h['baseline_status']}); B crossing {h['B_crossing']} ({h['B_status']}); "
                     f"gain x(Z*) - x(B) = {h['gain_vs_B_db']['point']} dB [{h['gain_vs_B_db']['lo']}, {h['gain_vs_B_db']['hi']}]; B better: {h['B_better']}; best Zheng variant better: {h['Z_better_than_B']}")
        for kind, v in c.get('families', {}).items():
            L.append(f"- family {kind}: {v['selected']} (other reading {v['other_reading']}); gain {v['gain_vs_B_db']['point']} dB [{v['gain_vs_B_db']['lo']}, {v['gain_vs_B_db']['hi']}]; B better: {v['B_better']}")
        if 'Z_turbo_report_only' in c:
            t = c['Z_turbo_report_only']
            L.append(f"- Z-turbo (report only): crossing {t['crossing']} ({t['status']}), gain vs B {t['gain_vs_B_db']['point']} [{t['gain_vs_B_db']['lo']}, {t['gain_vs_B_db']['hi']}]")
        e = c['extras']
        L.append(f"- family FER at 6 / 7 / 8 dB: " + '; '.join(f"{k} " + '/'.join(f'{x:.3f}' for x in v.values()) for k, v in c['family_fer_at_6_7_8_db'].items()))
        L.append(f"- band-truncation energy of the true channel (mean) {e['mean_trunc_true']}; mean true delays hit (of 8) at the lowest / highest SNR: "
                 + ', '.join(f"{a} {v[0]:.1f}/{v[-1]:.1f}" for a, v in e['mean_true_delays_hit'].items()) + '\n')
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------- self test
SNR = (450, 500, 550, 600, 650, 700, 750, 800)


def synth(rng, n, curves, scenario='U', rho_pm=300, variants=('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09', 'Zt')):
    """Port rows and P1 B rows from nested latents (arms strongly paired)."""
    u = rng.random((n, len(SNR)))
    port, p1 = [], {}
    for f in range(n):
        for i, s in enumerate(SNR):
            h = dict(channel_seed=f, noise_sha256=f'n{f}', info_sha256=f'i{f}', physical_gains_sha256=f'g{f}')
            port.append(dict(scenario=scenario, rho_permille=rho_pm, snr_centi_db=s, frame=f, trunc_true=.02, **h,
                             variants={a: dict(fer=int(u[f, i] < curves[a][i]), n_true_delays_hit=3, mp_iterations=10, trunc_est=.02, seconds=.5, zeta_star=.7) for a in variants}))
            p1[(scenario, rho_pm, s, f)] = dict(fer=int(u[f, i] < curves['B'][i]), **h)
    return port, p1


def loglin(slope, s0):
    return np.minimum(1., 10. ** (-slope * (np.array(SNR) / 100. - s0)))


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(('PASS ' if cond else 'FAIL ') + name)
        ok &= bool(cond)

    rng = np.random.default_rng(4)
    n = 1500
    names = ('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09', 'Zt')
    bad = {a: np.full(8, .5) for a in names}                                  # never reaches 1e-2: censored high
    b_good = loglin(.9, 3.0)
    port, p1 = synth(rng, n, dict(bad, B=b_good))
    res = analyze(port, p1, frames=n, B=800, seed=1)
    c = res['cells']['U_rho300']
    check('all Z censored high, B finite -> B better with a finite lower-bound gain', c['H5']['B_better'] and math.isfinite(c['H5']['gain_vs_B_db']['lo']) and c['H5']['baseline_status'].startswith('censored-high'))
    check('missing cells -> INCOMPLETE', res['H5_overall'] == 'INCOMPLETE')
    port2, p12 = synth(rng, n, dict(bad, B=np.full(8, .05)))
    r2 = analyze(port2, p12, frames=n, B=300, seed=2)['cells']['U_rho300']
    check('B censored high -> gain -inf -> B not better', not r2['H5']['B_better'] and r2['H5']['gain_vs_B_db']['lo'] == '-inf')
    # baseline = lowest crossing among all six variants (here Zo09), readings inside families
    cur = dict(Zf01=loglin(.9, 4.5), Zf09=loglin(.9, 4.0), Za01=loglin(.9, 4.2), Za09=loglin(.9, 3.9), Zo01=loglin(.9, 3.6), Zo09=loglin(.9, 3.4), Zt=loglin(.9, 3.0), B=loglin(.9, 3.0))
    port3, p13 = synth(rng, n, cur)
    c3 = analyze(port3, p13, frames=n, B=800, seed=3)['cells']['U_rho300']
    check('H5 baseline = the variant with the lowest crossing (Zo09)', c3['H5']['baseline'] == 'Zo09')
    check('per-family best readings: Zf09, Za09, Zo09', [c3['families'][k]['selected'] for k in ('faithful', 'adapted', 'omp')] == ['Zf09', 'Za09', 'Zo09'])
    exact = lambda s0: s0 + 2 / .9  # noqa: E731
    gain = exact(3.4) - exact(3.0)
    g = c3['H5']['gain_vs_B_db']
    check('gain CI covers the exact-curve difference %.2f dB and excludes 0' % gain, g['lo'] < gain < g['hi'] and g['lo'] > 0)
    check('all families beaten -> label "B better than the best Zheng variant"', c3['label'] == 'B better than the best Zheng variant' and all(v['B_better'] for v in c3['families'].values()))
    # Z-OMP equal to B: B not better than the best variant, other families still beaten
    cur4 = dict(cur, Zo01=loglin(.9, 3.0), Zo09=loglin(.9, 3.0))
    port4, p14 = synth(rng, n, cur4)
    c4 = analyze(port4, p14, frames=n, B=800, seed=4)['cells']['U_rho300']
    check('Z-OMP as good as B -> B not better; faithful and adapted families still beaten', not c4['H5']['B_better'] and c4['families']['faithful']['B_better'] and c4['families']['adapted']['B_better']
          and not c4['families']['omp']['B_better'])
    cur5 = dict(cur, Zo09=loglin(.9, 2.0), Zo01=loglin(.9, 2.5))
    port5, p15 = synth(rng, n, cur5)
    c5 = analyze(port5, p15, frames=n, B=800, seed=5)['cells']['U_rho300']
    check('Z-OMP clearly better than B -> flagged', c5['H5']['Z_better_than_B'] and c5['label'] == 'best Zheng variant better than B')
    check('Z-turbo reported and family FER summary present', 'Z_turbo_report_only' in c3 and 'omp' in c3['family_fer_at_6_7_8_db'] and 'B' in c3['family_fer_at_6_7_8_db'])
    port6, p16 = synth(rng, 50, dict(bad, B=b_good))
    k = next(iter(p16))
    p16[k] = dict(p16[k], noise_sha256='other')
    try:
        analyze(port6, p16, frames=50, B=50, seed=6)
        raised = False
    except ValueError:
        raised = True
    check('hash mismatch between port and P1 rows raises', raised)
    allp, allp1 = [], {}
    for sc, rho in CELLS:
        pp, qq = synth(rng, 600, dict(bad, B=b_good), scenario=sc, rho_pm=rho)
        allp += pp
        allp1.update(qq)
    r7 = analyze(allp, allp1, frames=600, B=300, seed=7)
    check('four cells with B better -> H5 PASS and family claims in all cells', r7['H5_overall'] == 'PASS' and all(r7['claim_better_than_family_in_all_cells'].values()))
    allp2, allp12 = [], {}
    for sc, rho in CELLS:
        curves = dict(bad, B=(np.full(8, .05) if (sc, rho) == ('G', 500) else b_good))
        pp, qq = synth(rng, 600, curves, scenario=sc, rho_pm=rho)
        allp2 += pp
        allp12.update(qq)
    r8 = analyze(allp2, allp12, frames=600, B=300, seed=8)
    check('one cell with B censored high -> H5 NOT SUPPORTED', r8['H5_overall'] == 'NOT SUPPORTED')
    json.dumps(r7, allow_nan=False)
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', nargs='+', type=Path)
    p.add_argument('--p1', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--frames', type=int, default=1000)
    p.add_argument('--boot', type=int, default=20000)
    p.add_argument('--seed', type=int, default=20261017)
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not args.rows or not args.p1 or not args.out:
        p.error('--rows, --p1 and --out are required')
    rows, files = load_rows(args.rows)
    p1_b, p1_files = load_p1_b(args.p1, args.frames)
    res = analyze(rows, p1_b, frames=args.frames, B=args.boot, seed=args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = dict(_argv=sys.argv[:], _config=dict(frames=args.frames, boot=args.boot, seed=args.seed, target_fer=TARGET, n_rows=len(rows), n_p1_b_rows=len(p1_b),
                                                    rows_md5={str(Path(f)): md5_file(f) for f in files}, p1_rows_md5={str(Path(f)): md5_file(f) for f in p1_files},
                                                    z_agg_md5=md5_file(__file__)), results=res)
    (args.out / 'z_results.json').write_text(json.dumps(payload, indent=1, allow_nan=False, default=float) + '\n')
    (args.out / 'Z_RESULTS.md').write_text(render_md(res))
    print('H5:', res['H5_overall'], res['cell_labels'])


if __name__ == '__main__':
    main()
